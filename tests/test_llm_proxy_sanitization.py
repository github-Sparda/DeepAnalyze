from __future__ import annotations

from src.core.orchestration.llm import LLMClient


def test_sanitize_proxy_env_removes_socks_proxy(monkeypatch) -> None:
    monkeypatch.setenv("ALL_PROXY", "socks5h://127.0.0.1:7895")
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:7895")
    LLMClient._sanitize_proxy_env()
    assert "ALL_PROXY" not in __import__("os").environ


def test_sanitize_proxy_env_keeps_http_proxy(monkeypatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:7895")
    LLMClient._sanitize_proxy_env()
    assert __import__("os").environ.get("HTTP_PROXY") == "http://127.0.0.1:7895"
