from __future__ import annotations

from bot.config import Settings
from bot.content import ArticleContentExtractor
from bot.content_service import NewsContentService
from bot.database import NewsRepository
from bot.deepseek import DeepSeekClient
from bot.news import NewsCollector
from bot.summary_service import NewsSummaryService


def main() -> None:
    repository = NewsRepository()
    item = NewsCollector().collect(
        category="ai",
        limit=1,
        max_age_hours=168,
        keywords="OpenAI",
    )[0]
    news_id = repository.save_news("ai", item)
    content_service = NewsContentService(
        repository=repository,
        extractor=ArticleContentExtractor(),
    )
    summary_service = NewsSummaryService(
        repository=repository,
        content_service=content_service,
        deepseek=DeepSeekClient(Settings.from_env()),
    )

    summary_before = repository.get_news(news_id)["summary"]
    first_result = summary_service.get_summary(news_id)
    second_result = summary_service.get_summary(news_id)
    summary_after = repository.get_news(news_id)["summary"]

    print(f"News id: {news_id}")
    print(f"Had cached summary before test: {bool(summary_before)}")
    print(f"First result source: {first_result.source}")
    print(f"Second result source: {second_result.source}")
    print(f"Summary saved after test: {bool(summary_after)}")
    print(f"Summary: {second_result.text}")


if __name__ == "__main__":
    main()
