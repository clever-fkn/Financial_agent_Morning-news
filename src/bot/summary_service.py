from __future__ import annotations

from dataclasses import dataclass

from .content_service import NewsContentService
from .database import NewsRepository
from .deepseek import DeepSeekClient


SUMMARY_SYSTEM_PROMPT = """
你是谨慎的中文新闻编辑。
只能依据用户提供的新闻标题和正文总结，不得补充正文中没有的数字、人物或结论。
请生成一段 50 到 100 字的中文摘要。
必须返回 JSON 对象，格式为：{"summary": "摘要内容"}。
""".strip()


@dataclass(frozen=True)
class NewsSummary:
    text: str
    source: str


class NewsSummaryService:
    """Generate a summary once and reuse it from SQLite afterwards."""

    def __init__(
        self,
        repository: NewsRepository,
        content_service: NewsContentService,
        deepseek: DeepSeekClient,
    ) -> None:
        self._repository = repository
        self._content_service = content_service
        self._deepseek = deepseek

    def get_summary(self, news_id: int) -> NewsSummary:
        news = self._repository.get_news(news_id)
        if news is None:
            raise ValueError(f"News record does not exist: {news_id}")

        cached_summary = news.get("summary")
        if isinstance(cached_summary, str) and cached_summary.strip():
            return NewsSummary(
                text=cached_summary.strip(),
                source="database_cache",
            )

        content = self._content_service.get_content(news_id)
        if not content.text:
            raise RuntimeError(f"News content is empty: {news_id}")

        user_content = (
            f"标题：{news['title']}\n\n"
            f"正文：\n{content.text[:12_000]}"
        )
        result = self._deepseek.answer_json(
            SUMMARY_SYSTEM_PROMPT,
            user_content,
        )
        summary = result.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise RuntimeError("DeepSeek returned an invalid news summary.")

        clean_summary = summary.strip()
        self._repository.update_summary(news_id, clean_summary)
        return NewsSummary(text=clean_summary, source="deepseek")
