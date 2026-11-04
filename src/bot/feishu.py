from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    P2ImMessageReceiveV1,
)

from .config import Settings
from .deepseek import DeepSeekClient
from .digest import NewsDigestService


logger = logging.getLogger(__name__)


class FeishuBot:
    """Private-chat Feishu bot backed by DeepSeek."""

    def __init__(
        self,
        settings: Settings,
        deepseek: DeepSeekClient,
        digest: NewsDigestService,
    ) -> None:
        self._settings = settings
        self._deepseek = deepseek
        self._digest = digest
        self._executor = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="bot-worker",
        )
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

        # Return from the Feishu event callback quickly. Model calls happen in a
        # worker so a slow answer does not cause Feishu to retry the event.
        self._executor.submit(
            self._answer_and_send,
            message.chat_id,
            message.message_id,
            text,
        )

    def _answer_and_send(
        self,
        chat_id: str,
        message_id: str | None,
        text: str,
    ) -> None:
        try:
            command = re.sub(r"\s+", "", text).lower()
            if command == "帮助":
                reply = (
                    "我是你的个人财经与 AI 新闻助手。\n\n"
                    "可用指令：\n"
                    "今日财经：获取财经新闻摘要\n"
                    "今日AI：获取 AI 新闻摘要\n"
                    "今日早报：同时获取财经与 AI 摘要\n"
                    "其他文字：直接向 DeepSeek 提问"
                )
            elif command == "今日财经":
                reply = self._digest.build("finance")
            elif command == "今日ai":
                reply = self._digest.build("ai")
            elif command == "今日早报":
                finance = self._digest.build("finance")
                ai = self._digest.build("ai")
                reply = f"{finance}\n\n{'=' * 20}\n\n{ai}"
            else:
                reply = self._deepseek.answer(text)
        except Exception:
            logger.exception("DeepSeek request failed.")
            reply = "DeepSeek 暂时不可用，请稍后再试。"

        self._send_text(chat_id, reply, message_id)

    def _send_text(
        self,
        chat_id: str,
        text: str,
        source_message_id: str | None = None,
    ) -> None:
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
                "Failed to send Feishu message: code=%s msg=%s log_id=%s",
                response.code,
                response.msg,
                response.get_log_id(),
            )
