from __future__ import annotations

import logging
import sqlite3
from collections.abc import Sequence
from pathlib import Path
from threading import RLock
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver

from .config import Settings
from .tools import (
    collect_latest_news,
    get_news_detail,
    list_news_sources,
    make_news_digest,
)


logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AGENT_STATE_PATH = PROJECT_ROOT / "data" / "agent_state.db"


SYSTEM_PROMPT = """
你是一个个人财经与 AI 新闻助手。

规则：
1. 当用户询问当前配置了哪些新闻来源时，必须调用 list_news_sources 工具。
2. 当用户只要求最新、今天或近期的新闻列表时，调用 collect_latest_news 工具。
3. 当用户要求早报、摘要、整理或每条新闻简介时，调用 make_news_digest 工具。
4. 当用户追问之前新闻列表中的某一条时，从历史工具结果确定新闻 ID，调用 get_news_detail。
5. 不能猜测新闻 ID；如果历史中没有对应关系，应请用户说明具体新闻。
6. 新闻回答只能依据工具返回的数据，不得编造标题、时间、来源、链接或事件细节。
7. 每条新闻都要保留来源和原文链接。
8. 普通知识问题可以直接回答，不需要调用工具。
9. 使用简洁、清楚的中文回答。
""".strip()


def find_incomplete_tool_call_ids(messages: Sequence[BaseMessage]) -> list[str]:
    """Return tool-call IDs that are missing their required ToolMessage."""

    pending: list[str] = []
    for message in messages:
        if isinstance(message, AIMessage):
            if pending:
                return pending
            pending = [
                str(call["id"])
                for call in message.tool_calls
                if call.get("id")
            ]
            continue

        if isinstance(message, ToolMessage):
            if message.tool_call_id in pending:
                pending.remove(message.tool_call_id)
            continue

        if pending:
            return pending

    return pending


def is_incomplete_tool_history_error(error: BaseException) -> bool:
    """Recognize the OpenAI-compatible API error for a broken tool history."""

    current: BaseException | None = error
    while current is not None:
        message = str(current).lower()
        if (
            "tool_calls" in message
            and "tool_call_id" in message
            and "must be followed" in message
        ):
            return True
        current = current.__cause__ or current.__context__
    return False


class NewsAgent:
    """A minimal LangChain agent that can choose and call news tools."""

    def __init__(
        self,
        settings: Settings,
        state_path: str | Path | None = None,
    ) -> None:
        memory_path = Path(state_path) if state_path else DEFAULT_AGENT_STATE_PATH
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        self._memory_connection = sqlite3.connect(
            memory_path,
            check_same_thread=False,
        )
        self._checkpointer = SqliteSaver(self._memory_connection)
        # LangGraph and one SQLite connection must not be invoked concurrently.
        # Feishu callbacks may arrive on different threads, so serialize access
        # here as the final protection around both the graph and its memory.
        self._invoke_lock = RLock()

        model = ChatOpenAI(
            model=settings.deepseek_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=30.0,
            max_retries=2,
            extra_body={"thinking": {"type": "disabled"}},
        )
        self._graph = create_agent(
            model=model,
            tools=[
                list_news_sources,
                collect_latest_news,
                make_news_digest,
                get_news_detail,
            ],
            system_prompt=SYSTEM_PROMPT,
            checkpointer=self._checkpointer,
        )

    def invoke(
        self,
        user_text: str,
        thread_id: str = "terminal-default",
    ) -> dict[str, Any]:
        """Run one agent turn and return the complete execution state."""

        with self._invoke_lock:
            self._reset_thread_if_incomplete(thread_id)
            try:
                return self._invoke_once(user_text, thread_id)
            except Exception as error:
                # A process interruption or tool failure can leave an
                # AIMessage(tool_calls=...) without its ToolMessage. Remove
                # that poisoned history so later requests are not all rejected.
                reset = self._reset_thread_if_incomplete(thread_id)
                if is_incomplete_tool_history_error(error):
                    if not reset:
                        self._checkpointer.delete_thread(thread_id)
                    logger.warning(
                        "Retrying Agent request after resetting invalid tool "
                        "history: thread_id=%s",
                        thread_id,
                    )
                    return self._invoke_once(user_text, thread_id)
                raise

    def _invoke_once(self, user_text: str, thread_id: str) -> dict[str, Any]:
        return self._graph.invoke(
            {"messages": [{"role": "user", "content": user_text}]},
            config={
                "recursion_limit": 6,
                "configurable": {"thread_id": thread_id},
            },
        )

    def _reset_thread_if_incomplete(self, thread_id: str) -> bool:
        checkpoint = self._checkpointer.get_tuple(
            {"configurable": {"thread_id": thread_id}}
        )
        if checkpoint is None:
            return False

        messages = checkpoint.checkpoint["channel_values"].get("messages", [])
        incomplete_ids = find_incomplete_tool_call_ids(messages)
        if not incomplete_ids:
            return False

        logger.warning(
            "Resetting incomplete Agent history: thread_id=%s "
            "tool_call_ids=%s",
            thread_id,
            incomplete_ids,
        )
        self._checkpointer.delete_thread(thread_id)
        return True

    def reset_thread(self, thread_id: str) -> None:
        """Delete one conversation's Agent memory without touching news data."""

        with self._invoke_lock:
            self._checkpointer.delete_thread(thread_id)

    def answer(
        self,
        user_text: str,
        thread_id: str = "terminal-default",
    ) -> str:
        """Run one agent turn and return only its final text answer."""

        result = self.invoke(user_text, thread_id=thread_id)
        for message in reversed(result["messages"]):
            if isinstance(message, AIMessage) and isinstance(message.content, str):
                text = message.content.strip()
                if text:
                    return text

        raise RuntimeError("Agent returned no final text answer.")

    def close(self) -> None:
        """Close the local SQLite conversation-memory connection."""

        with self._invoke_lock:
            self._memory_connection.close()
