from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
import trafilatura


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ArticleContent:
    text: str
    source: str


class ArticleContentExtractor:
    """Download a news page and extract its main readable text."""

    def __init__(self, timeout: float = 8.0, max_characters: int = 20_000) -> None:
        self._timeout = timeout
        self._max_characters = max_characters

    def extract(self, url: str, fallback_snippet: str = "") -> ArticleContent:
        headers = {"User-Agent": "FeishuPersonalNewsBot/0.1"}
        # A page is optional enrichment. Fall back to its RSS snippet quickly
        # when a publisher blocks scraping or the connection is unstable.
        transport = httpx.HTTPTransport(retries=0)

        try:
            with httpx.Client(
                headers=headers,
                follow_redirects=True,
                timeout=self._timeout,
                transport=transport,
            ) as client:
                response = client.get(url)
                response.raise_for_status()

            extracted = trafilatura.extract(
                response.text,
                include_comments=False,
                include_tables=False,
                include_links=False,
                include_images=False,
                favor_precision=True,
            )
            if extracted and extracted.strip():
                return ArticleContent(
                    text=extracted.strip()[: self._max_characters],
                    source="webpage",
                )
        except Exception as exc:
            logger.warning(
                "Article extraction failed for %s: %s",
                url,
                type(exc).__name__,
            )

        return ArticleContent(
            text=fallback_snippet.strip()[: self._max_characters],
            source="rss_fallback",
        )
