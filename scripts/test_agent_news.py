from __future__ import annotations

from bot.agent import NewsAgent
from bot.config import Settings


def main() -> None:
    agent = NewsAgent(Settings.from_env())
    result = agent.invoke(
        "请获取过去 168 小时内与 OpenAI 相关的 3 条 AI 新闻，并用中文简要介绍。",
        thread_id="test-agent-news",
    )

    print("\n===== 新闻 Agent 执行轨迹 =====")
    for message in result["messages"]:
        message_type = type(message).__name__
        tool_calls = getattr(message, "tool_calls", None)

        if tool_calls:
            print(f"\n{message_type} 发起工具调用：{tool_calls}")
        else:
            print(f"\n{message_type}：\n{message.content}")


if __name__ == "__main__":
    main()
