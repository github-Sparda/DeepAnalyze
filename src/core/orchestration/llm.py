from __future__ import annotations

import os
from typing import Any

from openai import OpenAI

from src.api.config import (
    API_BASE,
    DEEPANALYZE_VLLM_API_KEY,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
)


class LLMClient:
    def __init__(self) -> None:
        self._sanitize_proxy_env()
        self.client = OpenAI(base_url=API_BASE, api_key=DEEPANALYZE_VLLM_API_KEY)

    @staticmethod
    def _sanitize_proxy_env() -> None:
        # httpx/OpenAI SDK may fail on socks5h URLs. Prefer HTTP(S) proxy vars when present.
        proxy_keys = ["ALL_PROXY", "all_proxy"]
        http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
        https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        for key in proxy_keys:
            raw = str(os.environ.get(key, "")).strip()
            if not raw:
                continue
            low = raw.lower()
            if low.startswith("socks5h://") or low.startswith("socks5://"):
                if http_proxy or https_proxy:
                    os.environ.pop(key, None)
                else:
                    # Fall back to direct connection instead of startup crash.
                    os.environ.pop(key, None)

    def chat(self, messages: list[dict[str, Any]], max_tokens: int = 4096) -> str:
        response = self.client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            temperature=DEFAULT_TEMPERATURE,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
