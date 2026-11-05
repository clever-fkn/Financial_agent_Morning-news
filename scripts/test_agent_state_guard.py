from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from bot.agent import find_incomplete_tool_call_ids


def main() -> None:
    tool_call = {
        "name": "list_news_sources",
        "args": {"category": "ai"},
        "id": "call-test-1",
        "type": "tool_call",
    }

    valid_messages = [
        HumanMessage(content="有哪些 AI 新闻来源？"),
        AIMessage(content="", tool_calls=[tool_call]),
        ToolMessage(content="OpenAI", tool_call_id="call-test-1"),
        AIMessage(content="当前配置了 OpenAI。"),
    ]
    broken_messages = [
        HumanMessage(content="今日财经"),
        AIMessage(content="", tool_calls=[tool_call]),
        HumanMessage(content="为什么没有回复？"),
    ]

    assert find_incomplete_tool_call_ids(valid_messages) == []
    assert find_incomplete_tool_call_ids(broken_messages) == ["call-test-1"]
    print("Agent state guard: PASS")


if __name__ == "__main__":
    main()
