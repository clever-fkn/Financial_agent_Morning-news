from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .news import NewsItem


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "news.db"

NEWS_SCHEMA = """
CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('finance', 'ai')),
    published_at TEXT NOT NULL,
    snippet TEXT NOT NULL DEFAULT '',
    content TEXT,
    summary TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_news_category_published
ON news(category, published_at DESC);
"""


def initialize_database(db_path: str | Path | None = None) -> Path:
    """Create the SQLite file and news table if they do not exist."""

    path = Path(db_path) if db_path is not None else DEFAULT_DATABASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        connection.executescript(NEWS_SCHEMA)

    return path


class NewsRepository:
    """Store and retrieve news records from the local SQLite database."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._path = initialize_database(db_path)

    @property
    def path(self) -> Path:
        return self._path

    def save_news(self, category: str, item: NewsItem) -> int:
        """Insert a news item or refresh its basic fields when the URL exists."""

        if category not in {"finance", "ai"}:
            raise ValueError(f"Unsupported news category: {category}")

        with sqlite3.connect(self._path) as connection:
            connection.execute(
                """
                INSERT INTO news (
                    url,
                    title,
                    source,
                    category,
                    published_at,
                    snippet
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    title = excluded.title,
                    source = excluded.source,
                    category = excluded.category,
                    published_at = excluded.published_at,
                    snippet = excluded.snippet
                """,
                (
                    item.url,
                    item.title,
                    item.source,
                    category,
                    item.published_at.isoformat(),
                    item.snippet,
                ),
            )
            row = connection.execute(
                "SELECT id FROM news WHERE url = ?",
                (item.url,),
            ).fetchone()

        if row is None:
            raise RuntimeError("News was saved but its id could not be read back.")
        return int(row[0])

    def get_news(self, news_id: int) -> dict[str, Any] | None:
        with sqlite3.connect(self._path) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM news WHERE id = ?",
                (news_id,),
            ).fetchone()

        return dict(row) if row is not None else None

    def list_recent_news(self, limit: int = 10) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")

        with sqlite3.connect(self._path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT * FROM news ORDER BY published_at DESC LIMIT ?",
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]

    def update_content(self, news_id: int, content: str) -> None:
        """Save extracted article content for an existing news record."""

        clean_content = content.strip()
        if not clean_content:
            raise ValueError("Article content must not be empty.")

        with sqlite3.connect(self._path) as connection:
            cursor = connection.execute(
                "UPDATE news SET content = ? WHERE id = ?",
                (clean_content, news_id),
            )

        if cursor.rowcount == 0:
            raise ValueError(f"News record does not exist: {news_id}")

    def update_summary(self, news_id: int, summary: str) -> None:
        """Save an AI-generated summary for an existing news record."""

        clean_summary = summary.strip()
        if not clean_summary:
            raise ValueError("News summary must not be empty.")

        with sqlite3.connect(self._path) as connection:
            cursor = connection.execute(
                "UPDATE news SET summary = ? WHERE id = ?",
                (clean_summary, news_id),
            )

        if cursor.rowcount == 0:
            raise ValueError(f"News record does not exist: {news_id}")

    def count_news(self) -> int:
        with sqlite3.connect(self._path) as connection:
            row = connection.execute("SELECT COUNT(*) FROM news").fetchone()

        return int(row[0]) if row is not None else 0
