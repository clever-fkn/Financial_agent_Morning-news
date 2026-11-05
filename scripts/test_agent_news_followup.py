from __future__ import annotations

from uuid import uuid4

from bot.agent import NewsAgent
from bot.config import Settings
from bot.database import NewsRepository


def main() -> None:
    repository = NewsRepository()
    recent_news = [
        news
        for news in repository.list_recent_news(limit=20)
        if not str(news["url"]).startswith("https://example.com/")
    ]
    if len(recent_news) < 2:
        raise RuntimeError("At least two real news records are required for this test.")

    first_news, second_news = recent_news[:2]
    thread_id = f"news-followup-{uuid4()}"
    settings = Settings.from_env()

    first_agent = NewsAgent(settings)
    first_agent.answer(
        "请记住下面这份早报顺序，只需要确认：\n"
        f"第1条：ID={first_news['id']}，标题={first_news['title']}\n"
        f"第2条：ID={second_news['id']}，标题={second_news['title']}",
        thread_id=thread_id,
    )
    first_agent.close()

    second_agent = NewsAgent(settings)
    result = second_agent.invoke(
        "请详细解释刚才的第2条新闻。",
        thread_id=thread_id,
    )
    second_agent.close()

    print(f"Expected second news id: {second_news['id']}")
    print("Follow-up execution trace:")
    for message in result["messages"]:
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            print(f"- Tool calls: {tool_calls}")
    print(f"Final answer: {result['messages'][-1].content}")


if __name__ == "__main__":
    main()
