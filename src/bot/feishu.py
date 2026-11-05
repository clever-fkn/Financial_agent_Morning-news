from __future__ import annotations

import json
import logging
import re
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import perf_counter

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    P2ImMessageReceiveV1,
)

from .agent import NewsAgent
from .config import Settings


logger = logging.getLogger(__name__)


HELP_TEXT = (
    "我是你的个人财经与 AI 新闻 Agent。\n\n"
    "快捷指令：\n"
    "今日财经：生成财经早报\n"
    "今日AI：生成 AI 早报\n"
    "今日早报：同时生成财经与 AI 早报\n\n"
    "也可以直接用自然语言，例如：\n"
    "给我过去24小时最重要的3条财经新闻\n"
    "整理最近一周与OpenAI相关的AI新闻\n"
    "详细解释刚才第2条"
)

SHORTCUT_PROMPTS = {
    "今日财经": "请生成过去72小时内最重要的5条财经早报，包含中文摘要、来源和链接。",
    "今日ai": "请生成过去168小时内最重要的5条AI早报，包含中文摘要、来源和链接。",
    "今日早报": (
        "请分别生成过去72小时内最重要的5条财经早报，以及过去168小时内最重要的"
        "5条AI早报；每条包含中文摘要、来源和链接。"
    ),
}


def resolve_agent_prompt(text: str) -> str:
    """Expand legacy shortcut commands into explicit Agent requests."""

    command = re.sub(r"\s+", "", text).lower()
    return SHORTCUT_PROMPTS.get(command, text.strip())


class FeishuBot:
    """Private-chat Feishu bot backed by the news Agent."""

    def __init__(
        self,
        settings: Settings,
        agent: NewsAgent,
    ) -> None:
        self._settings = settings
        self._agent = agent
        # A personal bot handles Agent turns in order. This prevents two
        # messages from writing interleaved checkpoints to the same chat.
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="bot-worker",
        )
        self._seen_message_ids: set[str] = set()
        self._seen_message_order: deque[str] = deque()
        self._seen_message_lock = Lock()
        self._seen_message_limit = 1000
        self._api_client = (
            lark.Client.builder()
            .app_id(settings.feishu_app_id)
            .app_secret(settings.feishu_app_secret)
            .log_level(lark.LogLevel.WARNING)
            .build()
        )
        self._event_handler = (
            lark.EventDispatcherHandler.builder("", "")
            .register_p2_im_message_receive_v1(self._on_message)
            .build()
        )
        self._ws_client = lark.ws.Client(
            settings.feishu_app_id,
            settings.feishu_app_secret,
            event_handler=self._event_handler,
            log_level=lark.LogLevel.WARNING,
        )

    def start(self) -> None:
        logger.info("Starting Feishu WebSocket client. Press Ctrl+C to stop.")
        self._ws_client.start()

    def close(self) -> None:
        """Wait for queued replies before the Agent database is closed."""

        self._executor.shutdown(wait=True, cancel_futures=False)

    def _on_message(self, data: P2ImMessageReceiveV1) -> None:
        event = data.event
        message = event.message if event else None
        sender = event.sender if event else None

        if message is None:
            logger.warning("Ignored an event without a message body.")
            return
        if sender is not None and sender.sender_type not in (None, "user"):
            logger.info("Ignored a non-user message event.")
            return
        if message.chat_type != "p2p":
            logger.info("Ignored a non-private message: chat_type=%s", message.chat_type)
            return
        if not message.chat_id:
            logger.warning("Ignored a message without chat_id.")
            return
        if self._is_duplicate_message(message.message_id):
            logger.info("Ignored a duplicate message: message_id=%s", message.message_id)
            return

        if message.message_type != "text":
            self._send_text(
                message.chat_id,
                "当前测试版本只支持文字消息。",
                message.message_id,
            )
            return

        try:
            payload = json.loads(message.content or "{}")
        except json.JSONDecodeError:
            logger.warning("Ignored a text message with invalid JSON content.")
            return

        text = str(payload.get("text", "")).strip()
        if not text:
            return

        logger.info(
            "Received Feishu message: chat_id=%s message_id=%s text_chars=%s",
            message.chat_id,
            message.message_id,
            len(text),
        )

        # Return from the Feishu event callback quickly. Model calls happen in a
        # worker so a slow answer does not cause Feishu to retry the event.
        self._executor.submit(
            self._answer_and_send,
            message.chat_id,
            message.message_id,
            text,
        )

    def _is_duplicate_message(self, message_id: str | None) -> bool:
        if not message_id:
            return False

        with self._seen_message_lock:
            if message_id in self._seen_message_ids:
                return True
            if len(self._seen_message_order) >= self._seen_message_limit:
                oldest = self._seen_message_order.popleft()
                self._seen_message_ids.discard(oldest)
            self._seen_message_order.append(message_id)
            self._seen_message_ids.add(message_id)
        return False

    def _answer_and_send(
        self,
        chat_id: str,
        message_id: str | None,
        text: str,
    ) -> None:
        started_at = perf_counter()
        logger.info(
            "Agent request started: chat_id=%s message_id=%s",
            chat_id,
            message_id,
        )
        try:
            command = re.sub(r"\s+", "", text).lower()
            if command == "帮助":
                reply = HELP_TEXT
            else:
                prompt = resolve_agent_prompt(text)
                reply = self._agent.answer(prompt, thread_id=chat_id)
            logger.info(
                "Agent request completed: chat_id=%s message_id=%s "
                "duration_seconds=%.3f reply_chars=%s",
                chat_id,
                message_id,
                perf_counter() - started_at,
                len(reply),
            )
        except Exception:
            logger.exception(
                "Agent request failed: chat_id=%s message_id=%s "
                "duration_seconds=%.3f",
                chat_id,
                message_id,
                perf_counter() - started_at,
            )
            reply = "新闻 Agent 暂时不可用，请稍后再试。"

        self._send_text(chat_id, reply, message_id)

    def _send_text(
        self,
        chat_id: str,
        text: str,
        source_message_id: str | None = None,
    ) -> None:
        started_at = perf_counter()
        logger.info(
            "Feishu send started: chat_id=%s source_message_id=%s text_chars=%s",
            chat_id,
            source_message_id,
            len(text),
        )
        body_builder = (
            CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type("text")
            .content(json.dumps({"text": text}, ensure_ascii=False))
        )
        if source_message_id:
            body_builder = body_builder.uuid(source_message_id)

        request = (
            CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(body_builder.build())
            .build()
        )
        response = self._api_client.im.v1.message.create(request)
        if not response.success():
            logger.error(
                "Failed to send Feishu message: code=%s msg=%s log_id=%s "
                "duration_seconds=%.3f",
                response.code,
                response.msg,
                response.get_log_id(),
                perf_counter() - started_at,
            )
            return

        logger.info(
            "Feishu send completed: chat_id=%s duration_seconds=%.3f",
            chat_id,
            perf_counter() - started_at,
        )
