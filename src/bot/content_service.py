from __future__ import annotations

from .content import ArticleContent, ArticleContentExtractor
from .database import NewsRepository


class NewsContentService:
    """Load article content from SQLite or extract and cache it."""

    def __init__(
        self,
        repository: NewsRepository,
        extractor: ArticleContentExtractor,
    ) -> None:
        self._repository = repository
        self._extractor = extractor

    def get_content(self, news_id: int) -> ArticleContent:
        news = self._repository.get_news(news_id)
        if news is None:
            raise ValueError(f"News record does not exist: {news_id}")

        cached_content = news.get("content")
        if isinstance(cached_content, str) and cached_content.strip():
            return ArticleContent(
                text=cached_content.strip(),
                source="database_cache",
            )

        extracted = self._extractor.extract(
            url=str(news["url"]),
            fallback_snippet=str(news["snippet"] or ""),
        )
        if extracted.text:
            self._repository.update_content(news_id, extracted.text)

        return extracted
