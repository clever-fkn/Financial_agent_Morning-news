from __future__ import annotations

from bot.content import ArticleContentExtractor
from bot.news import NewsCollector


def main() -> None:
    item = NewsCollector().collect(
        category="ai",
        limit=1,
        max_age_hours=168,
        keywords="OpenAI",
    )[0]
    content = ArticleContentExtractor().extract(
        url=item.url,
        fallback_snippet=item.snippet,
    )

    print(f"Title: {item.title}")
    print(f"URL: {item.url}")
    print(f"Content source: {content.source}")
    print(f"RSS snippet length: {len(item.snippet)}")
    print(f"Extracted content length: {len(content.text)}")
    print("\nContent preview:")
    print(content.text[:1000])


if __name__ == "__main__":
    main()
