from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional


class ChatIntent(Enum):
    CHAT_ONLY = "chat_only"
    REUSE_ARTIFACT = "reuse_artifact"
    GUIDED_ANALYSIS = "guided_analysis"
    EXPLORATORY_ANALYSIS = "exploratory_analysis"


@dataclass
class RouterDecision:
    intent: ChatIntent
    goal: str | None = None
    artifact_preview: dict[str, Any] | None = None
    reason: str | None = None


_GUIDED_KEYWORDS = [
    "analyze",
    "trend",
    "compare",
    "correlation",
    "insight",
    "focus",
    "target",
    "evaluate",
    "detail",
]

_EXPLORATORY_KEYWORDS = [
    "explore",
    "discover",
    "suggest",
    "auto",
    "generate",
    "find",
    "open-ended",
    "survey",
]

_REUSE_KEYWORDS = [
    "show",
    "review",
    "display",
    "again",
    "replay",
    "repeat",
    "inspect",
    "open",
    "report",
    "chart",
    "visual",
]


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def _contains_keyword(text: str, keywords: List[str]) -> bool:
    for kw in keywords:
        if kw in text:
            return True
    return False


def _choose_artifact(manifest: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    if not manifest:
        return None
    reports = manifest.get("reports", [])
    if reports:
        entry = reports[0].copy()
        entry["kind"] = "report"
        entry.setdefault("name", entry.get("name") or entry.get("relative_path", "report"))
        return entry
    visuals = manifest.get("visualizations", [])
    if visuals:
        entry = visuals[0].copy()
        entry["kind"] = "visualization"
        entry.setdefault("name", entry.get("metadata", {}).get("name") or entry.get("relative_path", "visual"))
        return entry
    tables = manifest.get("tables", [])
    if tables:
        entry = tables[0].copy()
        entry["kind"] = entry.get("type", "table")
        entry.setdefault("name", entry.get("name") or entry.get("relative_path", "table"))
        return entry
    return None


def classify_intent(
    message: str, manifest: Mapping[str, Any] | None = None
) -> RouterDecision:
    text = _normalize(message)
    artifact = _choose_artifact(manifest or {})

    if artifact and _contains_keyword(text, _REUSE_KEYWORDS):
        return RouterDecision(
            intent=ChatIntent.REUSE_ARTIFACT,
            artifact_preview=artifact,
            reason="reuse_keywords",
        )

    if _contains_keyword(text, _GUIDED_KEYWORDS):
        return RouterDecision(
            intent=ChatIntent.GUIDED_ANALYSIS,
            goal=message.strip(),
            reason="guided_keywords",
        )

    if _contains_keyword(text, _EXPLORATORY_KEYWORDS):
        return RouterDecision(
            intent=ChatIntent.EXPLORATORY_ANALYSIS,
            reason="exploratory_keywords",
        )

    return RouterDecision(intent=ChatIntent.CHAT_ONLY, reason="default_chat")
