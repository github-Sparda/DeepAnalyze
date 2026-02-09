from __future__ import annotations

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
        self.client = OpenAI(base_url=API_BASE, api_key=DEEPANALYZE_VLLM_API_KEY)

    def chat(self, messages: list[dict[str, Any]], max_tokens: int = 4096) -> str:
        response = self.client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            temperature=DEFAULT_TEMPERATURE,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
