from __future__ import annotations

import logging

from .config import Settings
from .deepseek import DeepSeekClient
from .digest import NewsDigestService
from .feishu import FeishuBot
from .news import NewsCollector


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    settings = Settings.from_env()
    deepseek = DeepSeekClient(settings)
    digest = NewsDigestService(
        collector=NewsCollector(),
        deepseek=deepseek,
    )
    bot = FeishuBot(settings, deepseek, digest)
    try:
        bot.start()
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Bot stopped by user.")
