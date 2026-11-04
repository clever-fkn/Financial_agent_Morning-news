from __future__ import annotations

from bot.config import Settings
from bot.deepseek import DeepSeekClient
from bot.digest import NewsDigestService
from bot.news import NewsCollector


def main() -> None:
    settings = Settings.from_env()
    service = NewsDigestService(
        collector=NewsCollector(),
        deepseek=DeepSeekClient(settings),
    )

    print(service.build("finance", limit=3))
    print("\n" + "=" * 60 + "\n")
    print(service.build("ai", limit=3))


if __name__ == "__main__":
    main()
