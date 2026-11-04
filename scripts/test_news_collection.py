from __future__ import annotations

from bot.news import NewsCollector, format_news_list


def main() -> None:
    collector = NewsCollector()

    finance_items = collector.collect("finance", limit=3)
    print(format_news_list("=== 今日财经测试 ===", finance_items))

    print("\n" + "=" * 60 + "\n")

    ai_items = collector.collect("ai", limit=5)
    print(format_news_list("=== 今日 AI 测试 ===", ai_items))


if __name__ == "__main__":
    main()
