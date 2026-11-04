# Personal Finance and AI News Bot

This project is being built in small, testable stages.

## Current stage: Feishu + DeepSeek private chat

The current code connects Feishu private messages to DeepSeek:

```text
Feishu private message -> WebSocket -> background worker -> DeepSeek -> Feishu reply
```

Before starting, configure the Feishu app with:

- Bot capability enabled.
- `im:message.p2p_msg:readonly` permission.
- `im:message:send_as_bot` permission.
- Long-connection event subscription.
- `im.message.receive_v1` event.
- A published version whose availability includes your account.

Copy `.env.example` to `.env` and fill in the values locally. Never commit or
share `.env`.

Run the bot:

```powershell
uv run python main.py
```

Available private-chat commands:

- `帮助`: show the command list.
- `今日财经`: collect and summarize finance news.
- `今日AI`: collect and summarize AI news.
- `今日早报`: return both finance and AI digests.
- Other text: ask DeepSeek directly.

## News configuration

Edit `news_config.json` to change sources and item counts:

- `default_limit`: final number of items returned for that category.
- `per_source_limit`: maximum items read from each source before merging.
- `max_age_hours`: discard articles older than this many hours.
- `sources`: RSS/Atom source names and URLs.

Validate configuration changes with:

```powershell
uv run python scripts/test_news_collection.py
```
