from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from langchain_core.tools import tool

from .config import Settings
from .content import ArticleContentExtractor
from .content_service import NewsContentService
from .database import NewsRepository
from .deepseek import DeepSeekClient
from .news import NewsCollector
from .selector import NewsSelector
from .summary_service import NewsSummaryService


CONFIG_PATH = Path(__file__).resolve().parents[2] / "news_config.json"

CATEGORY_NAMES = {
    "finance": "财经新闻",
    "ai": "AI 新闻",
}


@tool
def list_news_sources(
    category: Literal["finance", "ai", "all"] = "all",
) -> str:
    """列出当前配置的新闻来源。当用户询问新闻来源时使用这个工具。"""

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    categories = ["finance", "ai"] if category == "all" else [category]

    result: list[str] = []
    for current_category in categories:
        result.append(f"{CATEGORY_NAMES[current_category]}来源：")
        for source in config[current_category]["sources"]:
            result.append(f"- {source['name']}：{source['url']}")

    return "\n".join(result)


@tool
def collect_latest_news(
    category: Literal["finance", "ai"],
    limit: int = 5,
    max_age_hours: int | None = None,
    keywords: str | None = None,
) -> str:
    """获取最新的财经或 AI 新闻。

    当用户询问最新、今天或近期新闻时使用这个工具。
    category 只能是 finance 或 ai，limit 是需要返回的新闻数量。
    max_age_hours 是新闻的最大时间范围，例如过去 24 小时应传入 24。
    keywords 是用户指定的公司、人物或主题关键词；没有指定时传入 null。
    """

    if not 1 <= limit <= 10:
        raise ValueError("limit must be between 1 and 10")
    if max_age_hours is not None and not 1 <= max_age_hours <= 24 * 30:
        raise ValueError("max_age_hours must be between 1 and 720")
    if keywords is not None and len(keywords.strip()) > 100:
        raise ValueError("keywords must not exceed 100 characters")

    items = NewsCollector().collect(
        category=category,
        limit=limit,
        max_age_hours=max_age_hours,
        keywords=keywords,
    )
    repository = NewsRepository()
    payload = [
        {
            "id": repository.save_news(category, item),
            "title": item.title,
            "source": item.source,
            "published_at": item.published_at.isoformat(),
            "snippet": item.snippet[:1000],
            "url": item.url,
        }
        for item in items
    ]
    return json.dumps(payload, ensure_ascii=False)


@tool
def get_news_detail(news_id: int) -> str:
    """根据数据库新闻 ID 获取详细正文。

    当用户追问早报中的某一条、要求详细解释或询问更多信息时使用。
    news_id 必须来自之前的新闻工具结果，不能猜测或编造。
    """

    if news_id < 1:
        raise ValueError("news_id must be a positive integer")

    repository = NewsRepository()
    news = repository.get_news(news_id)
    if news is None:
        raise ValueError(f"News record does not exist: {news_id}")

    content = NewsContentService(
        repository=repository,
        extractor=ArticleContentExtractor(),
    ).get_content(news_id)
    payload = {
        "id": news_id,
        "title": news["title"],
        "source": news["source"],
        "published_at": news["published_at"],
        "url": news["url"],
        "summary": news["summary"],
        "content_source": content.source,
        "content": content.text[:12_000],
    }
    return json.dumps(payload, ensure_ascii=False)


@tool
def make_news_digest(
    category: Literal["finance", "ai"],
    limit: int = 5,
    max_age_hours: int | None = None,
    keywords: str | None = None,
) -> str:
    """生成带中文摘要的财经或 AI 新闻早报。

    当用户要求早报、新闻摘要、新闻整理或每条新闻简介时使用这个工具。
    category 只能是 finance 或 ai，limit 是早报条数。
    max_age_hours 是新闻时间范围，keywords 是可选主题关键词。
    """

    if not 1 <= limit <= 10:
        raise ValueError("limit must be between 1 and 10")
    if max_age_hours is not None and not 1 <= max_age_hours <= 24 * 30:
        raise ValueError("max_age_hours must be between 1 and 720")
    if keywords is not None and len(keywords.strip()) > 100:
        raise ValueError("keywords must not exceed 100 characters")

    settings = Settings.from_env()
    repository = NewsRepository()
    content_service = NewsContentService(
        repository=repository,
        extractor=ArticleContentExtractor(),
    )
    summary_service = NewsSummaryService(
        repository=repository,
        content_service=content_service,
        deepseek=DeepSeekClient(settings),
    )
    candidate_limit = min(max(limit * 2, limit + 2), 20)
    items = NewsCollector().collect(
        category=category,
        limit=candidate_limit,
        max_age_hours=max_age_hours,
        keywords=keywords,
    )

    candidates = []
    for item in items:
        news_id = repository.save_news(category, item)
        summary = summary_service.get_summary(news_id)
        candidates.append(
            {
                "id": news_id,
                "title": item.title,
                "summary": summary.text,
                "summary_source": summary.source,
                "source": item.source,
                "published_at": item.published_at.isoformat(),
                "url": item.url,
            }
        )

    selected = NewsSelector(settings).select(candidates, limit=limit)
    candidates_by_id = {item["id"]: item for item in candidates}
    selected_items = [candidates_by_id[news_id] for news_id in selected.ids]

    result = {
        "candidate_count": len(candidates),
        "selected_count": len(selected_items),
        "selected_ids": selected.ids,
        "items": selected_items,
    }
    return json.dumps(result, ensure_ascii=False)
