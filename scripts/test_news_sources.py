from __future__ import annotations

from dataclasses import dataclass

import feedparser
import httpx


@dataclass(frozen=True)
class NewsSource:
    name: str
    url: str


SOURCES = [
    NewsSource(
        "财经新闻（Bing 搜索 RSS）",
        "https://www.bing.com/news/search?q=%E8%B4%A2%E7%BB%8F%20%E9%87%91%E8%9E%8D%20%E5%AE%8F%E8%A7%82%E7%BB%8F%E6%B5%8E&format=rss&setlang=zh-cn",
    ),
    NewsSource(
        "AI 新闻（Bing 搜索 RSS）",
        "https://www.bing.com/news/search?q=AI%20%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD%20%E5%A4%A7%E6%A8%A1%E5%9E%8B&format=rss&setlang=zh-cn",
    ),
    NewsSource("OpenAI 官方", "https://openai.com/news/rss.xml"),
    NewsSource("Google DeepMind 官方", "https://deepmind.google/blog/rss.xml"),
    NewsSource("Hugging Face 官方", "https://huggingface.co/blog/feed.xml"),
]


def check_source(client: httpx.Client, source: NewsSource) -> None:
    try:
        response = client.get(source.url)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        entries = feed.entries
        if not entries:
            print(f"[FAIL] {source.name}: HTTP {response.status_code}, 没有解析到新闻")
            return

        first_title = str(entries[0].get("title", "(无标题)"))
        print(f"[OK]   {source.name}: {len(entries)} 条；最新：{first_title}")
    except Exception as exc:
        print(f"[FAIL] {source.name}: {type(exc).__name__}: {exc}")


def main() -> None:
    headers = {"User-Agent": "FeishuPersonalNewsBot/0.1"}
    with httpx.Client(
        headers=headers,
        follow_redirects=True,
        timeout=15.0,
    ) as client:
        for source in SOURCES:
            check_source(client, source)


if __name__ == "__main__":
    main()
