from __future__ import annotations

import json

from openai import OpenAI

from .config import Settings


class DeepSeekClient:
    def __init__(self, settings: Settings) -> None:
        self._model = settings.deepseek_model
        self._client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=30.0,
            max_retries=2,
        )

    def answer(self, user_text: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个简洁、可靠的个人财经与 AI 新闻助手。",
                },
                {"role": "user", "content": user_text},
            ],
            stream=False,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("DeepSeek returned an empty response.")
        return content.strip()

    def answer_json(self, system_prompt: str, user_text: str) -> dict:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            response_format={"type": "json_object"},
            stream=False,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("DeepSeek returned an empty JSON response.")

        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise RuntimeError("DeepSeek JSON response is not an object.")
        return parsed
