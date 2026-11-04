from __future__ import annotations

from bot.config import Settings
from bot.deepseek import DeepSeekClient


def main() -> None:
    settings = Settings.from_env()
    client = DeepSeekClient(settings)
    answer = client.answer("请只回复：DeepSeek 连接成功")
    print(answer)


if __name__ == "__main__":
    main()
