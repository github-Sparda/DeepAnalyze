from __future__ import annotations

from orchestration.intent_router import ChatIntent, classify_intent


def _manifest_with_report() -> dict[str, object]:
    return {
        "reports": [
            {
                "name": "report_v1.html",
                "relative_path": "report/report_v1.html",
            }
        ],
        "visualizations": [],
        "tables": [],
    }


def test_reuse_artifact_when_requested():
    manifest = _manifest_with_report()
    decision = classify_intent("Can you show me the latest report?", manifest)
    assert decision.intent is ChatIntent.REUSE_ARTIFACT
    assert decision.artifact_preview


def test_guided_analysis_keyword():
    decision = classify_intent("Analyze trends for revenue growth.", None)
    assert decision.intent is ChatIntent.GUIDED_ANALYSIS
    assert "revenue" in (decision.goal or "")


def test_exploratory_keyword():
    decision = classify_intent("Explore the data and suggest interesting charts.", None)
    assert decision.intent is ChatIntent.EXPLORATORY_ANALYSIS


def test_default_chat():
    decision = classify_intent("Hi there, how are you today?", None)
    assert decision.intent is ChatIntent.CHAT_ONLY
