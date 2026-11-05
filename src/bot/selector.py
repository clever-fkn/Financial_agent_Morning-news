from __future__ import annotations

import json
from typing import Any

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_openai import ChatOpenAI

from .config import Settings
from .models import SelectedNews


SELECTION_SYSTEM_PROMPT = """
你是面向投资者的谨慎新闻编辑。
请根据政策影响、市场影响、覆盖范围、事件新颖性和信息可信度选择最重要的新闻。
只能选择候选列表中真实存在的 ID，不能虚构新闻或 ID。
返回的 ID 按重要性从高到低排列，并严格遵守用户要求的数量。
""".strip()


class NewsSelector:
    """Select important news IDs using validated structured model output."""

    def __init__(self, settings: Settings) -> None:
        model = ChatOpenAI(
            model=settings.deepseek_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=30.0,
            max_retries=2,
            extra_body={"thinking": {"type": "disabled"}},
        )
        self._agent = create_agent(
            model=model,
            tools=[],
            system_prompt=SELECTION_SYSTEM_PROMPT,
            response_format=ToolStrategy(SelectedNews),
        )

    def select(
        self,
        candidates: list[dict[str, Any]],
        limit: int,
    ) -> SelectedNews:
        if not candidates:
            raise ValueError("At least one news candidate is required.")
        if not 1 <= limit <= 10:
            raise ValueError("limit must be between 1 and 10")

        candidate_ids: list[int] = []
        for candidate in candidates:
            news_id = candidate.get("id")
            if not isinstance(news_id, int) or news_id < 1:
                raise ValueError("Every candidate must have a positive integer id.")
            if news_id in candidate_ids:
                raise ValueError("Candidate ids must be unique.")
            candidate_ids.append(news_id)

        target_count = min(limit, len(candidate_ids))
        user_message = json.dumps(
            {
                "required_count": target_count,
                "candidates": candidates,
            },
            ensure_ascii=False,
        )
        result = self._agent.invoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config={"recursion_limit": 4},
        )
        structured = result.get("structured_response")
        if not isinstance(structured, SelectedNews):
            structured = SelectedNews.model_validate(structured)

        # Provider output is validated again against the actual candidate IDs.
        final_ids: list[int] = []
        for news_id in structured.ids:
            if news_id in candidate_ids and news_id not in final_ids:
                final_ids.append(news_id)
            if len(final_ids) == target_count:
                break

        # If the model returned too few valid IDs, keep the workflow available
        # by filling from the original (newest-first) candidate order.
        for news_id in candidate_ids:
            if len(final_ids) == target_count:
                break
            if news_id not in final_ids:
                final_ids.append(news_id)

        return SelectedNews(ids=final_ids)
