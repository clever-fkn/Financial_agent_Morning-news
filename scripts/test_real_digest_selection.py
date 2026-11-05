from __future__ import annotations

import json

from bot.tools import make_news_digest


def main() -> None:
    raw_result = make_news_digest.invoke(
        {
            "category": "ai",
            "limit": 1,
            "max_age_hours": 168,
            "keywords": "OpenAI",
        }
    )
    result = json.loads(raw_result)

    print(f"Candidate count: {result['candidate_count']}")
    print(f"Selected count: {result['selected_count']}")
    print(f"Selected ids: {result['selected_ids']}")
    print("Selected news:")
    for item in result["items"]:
        print(f"- id: {item['id']}")
        print(f"  title: {item['title']}")
        print(f"  summary source: {item['summary_source']}")
        print(f"  summary: {item['summary']}")


if __name__ == "__main__":
    main()
