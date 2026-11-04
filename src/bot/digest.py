from __future__ import annotations

import json

from .deepseek import DeepSeekClient
from .news import NewsCollector, NewsItem


class NewsDigestService:
    def __init__(
        self,
        collector: NewsCollector,
        deepseek: DeepSeekClient,
    ) -> None:
        self._collector = collector
        self._deepseek = deepseek

    def build(self, category: str, limit: int | None = None) -> str:
        items = self._collector.collect(category, limit=limit)
        summaries = self._summarize(items)
        heading = "今日财经摘要" if category == "finance" else "今日 AI 摘要"

        blocks = [heading]
        for index, item in enumerate(items, start=1):
            summary = summaries.get(index, "暂时无法生成摘要，请查看原文。")
            published = item.published_at.astimezone().strftime("%Y-%m-%d %H:%M")
            blocks.append(
                f"{index}. {item.title}\n"
                f"摘要：{summary}\n"
                f"时间：{published}\n"
                f"来源：{item.source}\n"
                f"{item.url}"
            )
        return "\n\n".join(blocks)

    def _summarize(self, items: list[NewsItem]) -> dict[int, str]:
        payload = [
            {
                "index": index,
                "title": item.title,
                "source": item.source,
                "published_at": item.published_at.isoformat(),
                "snippet": item.snippet[:1500],
            }
            for index, item in enumerate(items, start=1)
        ]
        system_prompt = (
            "你是谨慎的中文新闻编辑。只能根据给出的标题、来源和 RSS 摘要片段进行总结，"
            "不能补充片段中不存在的数字、事件或结论。每条用一到两句话概括。"
            "必须返回 JSON 对象，格式为 "
            '{"summaries":[{"index":1,"summary":"..."}]}。'
        )
        result = self._deepseek.answer_json(
            system_prompt,
            json.dumps(payload, ensure_ascii=False),
        )

        parsed: dict[int, str] = {}
        raw_summaries = result.get("summaries", [])
        if not isinstance(raw_summaries, list):
            return parsed

        for row in raw_summaries:
            if not isinstance(row, dict):
                continue
            index = row.get("index")
            summary = row.get("summary")
            if isinstance(index, int) and isinstance(summary, str) and summary.strip():
                parsed[index] = summary.strip()
        return parsed
