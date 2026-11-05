from __future__ import annotations

from bot.database import NewsRepository
from bot.news import NewsCollector


def main() -> None:
    repository = NewsRepository()
    collector = NewsCollector()
    items = collector.collect(
        category="ai",
        limit=3,
        max_age_hours=168,
        keywords="OpenAI",
    )

    count_before = repository.count_news()
    first_ids = [repository.save_news("ai", item) for item in items]
    count_after_first_save = repository.count_news()
    second_ids = [repository.save_news("ai", item) for item in items]
    count_after_second_save = repository.count_news()

    print(f"Count before: {count_before}")
    print(f"First save ids: {first_ids}")
    print(f"Count after first save: {count_after_first_save}")
    print(f"Second save ids: {second_ids}")
    print(f"Count after second save: {count_after_second_save}")


if __name__ == "__main__":
    main()
