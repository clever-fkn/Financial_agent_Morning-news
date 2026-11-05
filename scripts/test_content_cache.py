from __future__ import annotations

from bot.content import ArticleContentExtractor
from bot.content_service import NewsContentService
from bot.database import NewsRepository
from bot.news import NewsCollector


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

    content_before = repository.get_news(news_id)["content"]
    first_result = content_service.get_content(news_id)
    second_result = content_service.get_content(news_id)
    content_after = repository.get_news(news_id)["content"]

    print(f"News id: {news_id}")
    print(f"Had cached content before test: {bool(content_before)}")
    print(f"First result source: {first_result.source}")
    print(f"Second result source: {second_result.source}")
    print(f"Content saved after test: {bool(content_after)}")
    print(f"Content length: {len(second_result.text)}")


if __name__ == "__main__":
    main()
