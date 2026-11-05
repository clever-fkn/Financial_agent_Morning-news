from __future__ import annotations

import logging

from .agent import NewsAgent
from .config import Settings
from .feishu import FeishuBot


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    settings = Settings.from_env()
    agent = NewsAgent(settings)
    bot = FeishuBot(settings, agent)
    try:
        bot.start()
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Bot stopped by user.")
    finally:
        bot.close()
        agent.close()
