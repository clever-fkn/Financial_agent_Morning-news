from __future__ import annotations

from datetime import datetime, timezone

from bot.database import NewsRepository
from bot.news import NewsItem


def main() -> None:
    repository = NewsRepository()
    test_item = NewsItem(
        title="SQLite 入门测试新闻",
        url="https://example.com/agent-course/sqlite-test",
        source="课程测试来源",
        snippet="这是一条用于学习数据库插入和查询的测试数据。",
        published_at=datetime.now(timezone.utc),
    )

    news_id = repository.save_news("ai", test_item)
    saved_news = repository.get_news(news_id)

    print(f"Saved news id: {news_id}")
    print(f"Total news count: {repository.count_news()}")
    print("Saved row:")
    for key, value in (saved_news or {}).items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
