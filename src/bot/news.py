from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser
import httpx


@dataclass(frozen=True)
class NewsSource:
    name: str
    url: str


@dataclass(frozen=True)
class NewsItem:
    title: str
    url: str
    source: str
    snippet: str
    published_at: datetime


@dataclass(frozen=True)
class NewsCategoryConfig:
    default_limit: int
    per_source_limit: int
    max_age_hours: int
    sources: list[NewsSource]


def _title_key(title: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", title.casefold())


class NewsCollector:
    def __init__(
        self,
        timeout: float = 15.0,
        config_path: str | Path | None = None,
    ) -> None:
        self._timeout = timeout
        path = (
            Path(config_path)
            if config_path is not None
            else Path(__file__).resolve().parents[2] / "news_config.json"
        )
        self._categories = _load_config(path)

    def collect(self, category: str, limit: int | None = None) -> list[NewsItem]:
        config = self._categories.get(category)
        if config is None:
            raise ValueError(f"Unsupported news category: {category}")

        final_limit = config.default_limit if limit is None else limit
        if final_limit < 1:
            raise ValueError("News limit must be at least 1.")
        cutoff = datetime.now(timezone.utc) - timedelta(hours=config.max_age_hours)

        items: list[NewsItem] = []
        seen_titles: set[str] = set()
        errors: list[str] = []

        headers = {"User-Agent": "FeishuPersonalNewsBot/0.1"}
        transport = httpx.HTTPTransport(retries=2)
        with httpx.Client(
            headers=headers,
            follow_redirects=True,
            timeout=self._timeout,
            transport=transport,
        ) as client:
            for source in config.sources:
                try:
                    response = client.get(source.url)
                    response.raise_for_status()
                    feed = feedparser.parse(response.content)
                except Exception as exc:
                    errors.append(f"{source.name}: {type(exc).__name__}")
                    continue

                # Limit each feed so one large source does not dominate the list.
                for entry in feed.entries[: config.per_source_limit]:
                    title = str(entry.get("title", "")).strip()
                    url = str(entry.get("link", "")).strip()
                    raw_snippet = str(
                        entry.get("summary", entry.get("description", ""))
                    )
                    snippet = _clean_html(raw_snippet)
                    published_at = _entry_published_at(entry)
                    key = _title_key(title)
                    if (
                        not title
                        or not url
                        or not key
                        or key in seen_titles
                        or published_at is None
                        or published_at < cutoff
                    ):
                        continue

                    seen_titles.add(key)
                    items.append(
                        NewsItem(
                            title=title,
                            url=url,
                            source=source.name,
                            snippet=snippet,
                            published_at=published_at,
                        )
                    )

        if not items:
            detail = "; ".join(errors) if errors else "no entries returned"
            raise RuntimeError(f"No news could be collected: {detail}")

        items.sort(key=lambda item: item.published_at, reverse=True)
        return items[:final_limit]


def format_news_list(title: str, items: list[NewsItem]) -> str:
    lines = [title]
    for index, item in enumerate(items, start=1):
        published = item.published_at.astimezone().strftime("%Y-%m-%d %H:%M")
        lines.append(
            f"{index}. {item.title}\n"
            f"时间：{published}\n"
            f"来源：{item.source}\n"
            f"{item.url}"
        )
    return "\n\n".join(lines)


def _clean_html(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    unescaped = html.unescape(without_tags)
    return re.sub(r"\s+", " ", unescaped).strip()


def _entry_published_at(entry: object) -> datetime | None:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        value = entry.get(key) if hasattr(entry, "get") else None
        if value:
            return datetime(*value[:6], tzinfo=timezone.utc)

    for key in ("published", "updated", "created"):
        value = entry.get(key) if hasattr(entry, "get") else None
        if not value:
            continue
        try:
            parsed = parsedate_to_datetime(str(value))
        except (TypeError, ValueError):
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    return None


def _load_config(path: Path) -> dict[str, NewsCategoryConfig]:
    if not path.exists():
        raise RuntimeError(f"News configuration file not found: {path}")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid news configuration: {path}") from exc

    categories: dict[str, NewsCategoryConfig] = {}
    for category in ("finance", "ai"):
        value = raw.get(category)
        if not isinstance(value, dict):
            raise RuntimeError(f"Missing news category in config: {category}")

        default_limit = value.get("default_limit")
        per_source_limit = value.get("per_source_limit")
        max_age_hours = value.get("max_age_hours")
        raw_sources = value.get("sources")
        if not isinstance(default_limit, int) or default_limit < 1:
            raise RuntimeError(f"Invalid default_limit for {category}")
        if not isinstance(per_source_limit, int) or per_source_limit < 1:
            raise RuntimeError(f"Invalid per_source_limit for {category}")
        if not isinstance(max_age_hours, int) or max_age_hours < 1:
            raise RuntimeError(f"Invalid max_age_hours for {category}")
        if not isinstance(raw_sources, list) or not raw_sources:
            raise RuntimeError(f"No news sources configured for {category}")

        sources: list[NewsSource] = []
        for row in raw_sources:
            if not isinstance(row, dict):
                raise RuntimeError(f"Invalid news source entry for {category}")
            name = row.get("name")
            url = row.get("url")
            if not isinstance(name, str) or not name.strip():
                raise RuntimeError(f"Invalid source name for {category}")
            if not isinstance(url, str) or not url.startswith("https://"):
                raise RuntimeError(f"Invalid source URL for {category}: {name}")
            sources.append(NewsSource(name=name.strip(), url=url.strip()))

        categories[category] = NewsCategoryConfig(
            default_limit=default_limit,
            per_source_limit=per_source_limit,
            max_age_hours=max_age_hours,
            sources=sources,
        )

    return categories
