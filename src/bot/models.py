from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class SelectedNews(BaseModel):
    """The validated IDs selected by the news importance model."""

    ids: list[int] = Field(
        min_length=1,
        max_length=10,
        description="按重要性从高到低排列的新闻 ID，最多 10 条",
    )

    @field_validator("ids")
    @classmethod
    def validate_ids(cls, ids: list[int]) -> list[int]:
        if any(news_id < 1 for news_id in ids):
            raise ValueError("news ids must be positive integers")
        if len(ids) != len(set(ids)):
            raise ValueError("news ids must not contain duplicates")
        return ids
