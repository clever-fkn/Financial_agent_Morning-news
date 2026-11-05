from __future__ import annotations

from bot.feishu import resolve_agent_prompt


def main() -> None:
    examples = [
        "今日财经",
        "今日AI",
        "今日早报",
        "给我过去24小时最重要的3条财经新闻",
        "详细解释刚才第2条",
    ]

    for text in examples:
        print(f"User: {text}")
        print(f"Agent prompt: {resolve_agent_prompt(text)}")
        print()


if __name__ == "__main__":
    main()
