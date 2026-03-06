from __future__ import annotations

import os
import json
import time
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
        timeout_sec = float(os.getenv("DEEPANALYZE_LLM_TIMEOUT_SEC", "120"))
        self.max_retries = max(0, int(os.getenv("DEEPANALYZE_LLM_RETRIES", "2")))
        self.client = OpenAI(
            base_url=API_BASE,
            api_key=DEEPANALYZE_VLLM_API_KEY,
            timeout=timeout_sec,
        )

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

    @staticmethod
    def _normalize_text_response(raw: str) -> str:
        text = str(raw or "")
        if not text.lstrip().startswith("data:"):
            return text
        chunks: list[str] = []
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                obj = json.loads(payload)
            except Exception:
                continue
            for choice in obj.get("choices", []) if isinstance(obj, dict) else []:
                if not isinstance(choice, dict):
                    continue
                delta = choice.get("delta", {})
                if isinstance(delta, dict):
                    content = delta.get("content")
                    if isinstance(content, str) and content:
                        chunks.append(content)
        return "".join(chunks).strip()

    def chat(self, messages: list[dict[str, Any]], max_tokens: int = 4096) -> str:
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=DEFAULT_MODEL,
                    messages=messages,
                    temperature=DEFAULT_TEMPERATURE,
                    max_tokens=max_tokens,
                )
                # Some OpenAI-compatible providers may occasionally return plain text.
                if isinstance(response, str):
                    text = self._normalize_text_response(response)
                    if text:
                        return text
                    raise ValueError("empty_text_response")
                # SDK object path
                if hasattr(response, "choices"):
                    return response.choices[0].message.content or ""
                # dict-like fallback
                if isinstance(response, dict):
                    choices = response.get("choices", [])
                    if choices and isinstance(choices[0], dict):
                        msg = choices[0].get("message", {})
                        if isinstance(msg, dict):
                            return str(msg.get("content", "") or "")
                raise TypeError(f"unexpected_response_type:{type(response).__name__}")
            except Exception as exc:
                last_exc = exc
                if attempt >= self.max_retries:
                    break
                low = str(exc).lower()
                transient = any(
                    token in low
                    for token in [
                        "timed out",
                        "timeout",
                        "connection",
                        "rate limit",
                        "429",
                        "service unavailable",
                        "unexpected_response_type",
                        "empty_text_response",
                        "'str' object has no attribute 'choices'",
                    ]
                )
                if not transient:
                    break
                time.sleep(min(2.0 * (attempt + 1), 5.0))
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("llm_chat_failed_without_exception")
