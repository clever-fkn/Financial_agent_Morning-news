from __future__ import annotations

import json
from datetime import datetime
from time import perf_counter
from zoneinfo import ZoneInfo

from bot.tools import collect_latest_news


BEIJING_TIME = ZoneInfo("Asia/Shanghai")

CASES = [
    {
        "name": "近24小时财经快讯",
        "args": {
            "category": "finance",
            "limit": 3,
            "max_age_hours": 24,
            "keywords": None,
        },
    },
    {
        "name": "近72小时财经早报",
        "args": {
            "category": "finance",
            "limit": 5,
            "max_age_hours": 72,
            "keywords": None,
        },
    },
    {
        "name": "近7天财经周览",
        "args": {
            "category": "finance",
            "limit": 8,
            "max_age_hours": 168,
            "keywords": None,
        },
    },
]


def main() -> None:
    for index, case in enumerate(CASES, start=1):
        started_at = datetime.now(BEIJING_TIME)
        timer_started = perf_counter()

        try:
            raw_result = collect_latest_news.invoke(case["args"])
            items = json.loads(raw_result)
            error = None
        except Exception as exc:
            items = []
            error = f"{type(exc).__name__}: {exc}"

        elapsed_seconds = perf_counter() - timer_started
        finished_at = datetime.now(BEIJING_TIME)

        print(f"\n===== 工具调用 {index}: {case['name']} =====")
        print(f"开始时间: {started_at.isoformat(timespec='seconds')}")
        print(f"结束时间: {finished_at.isoformat(timespec='seconds')}")
        print(f"工具参数: {json.dumps(case['args'], ensure_ascii=False)}")
        print(f"耗时秒数: {elapsed_seconds:.3f}")
        print(f"返回条数: {len(items)}")

        if error:
            print(f"调用错误: {error}")
            continue

        for item_index, item in enumerate(items, start=1):
            print(
                f"{item_index}. {item['title']} | "
                f"{item['source']} | {item['published_at']}"
            )


if __name__ == "__main__":
    main()
