from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    feishu_app_id: str
    feishu_app_secret: str
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()

        values = {
            "FEISHU_APP_ID": os.getenv("FEISHU_APP_ID", "").strip(),
            "FEISHU_APP_SECRET": os.getenv("FEISHU_APP_SECRET", "").strip(),
            "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY", "").strip(),
            "DEEPSEEK_BASE_URL": os.getenv("DEEPSEEK_BASE_URL", "").strip(),
            "DEEPSEEK_MODEL": os.getenv("DEEPSEEK_MODEL", "").strip(),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            missing_text = ", ".join(missing)
            raise RuntimeError(f"Missing required environment variables: {missing_text}")

        return cls(
            feishu_app_id=values["FEISHU_APP_ID"],
            feishu_app_secret=values["FEISHU_APP_SECRET"],
            deepseek_api_key=values["DEEPSEEK_API_KEY"],
            deepseek_base_url=values["DEEPSEEK_BASE_URL"],
            deepseek_model=values["DEEPSEEK_MODEL"],
        )
