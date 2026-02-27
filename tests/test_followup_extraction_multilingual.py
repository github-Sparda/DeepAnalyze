from __future__ import annotations

from src.core.orchestration import graph as orchestration_graph


def test_followup_extraction_supports_multilingual_text() -> None:
    payload = """
    1. 假设 1：Normal 与 EP 的分组差异需要在批次校正后复验
    2. H2: predictive signal should be stress-tested with nested CV
    3. 建议补充图表
    """
    hypotheses = orchestration_graph._extract_hypotheses(payload)
    assert any(item.startswith("假设 1") for item in hypotheses)
    assert any(item.lower().startswith("h2") for item in hypotheses)


def test_followup_extraction_supports_json_payload() -> None:
    payload = """
    {
      "followup_hypotheses": [
        "假设 3：冲突结论需第三路径裁决",
        {"title": "Hypothesis 4: perform sensitivity analysis"}
      ]
    }
    """
    hypotheses = orchestration_graph._extract_hypotheses(payload)
    assert "假设 3：冲突结论需第三路径裁决" in hypotheses
    assert "Hypothesis 4: perform sensitivity analysis" in hypotheses
