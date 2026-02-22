from __future__ import annotations

import json
from pathlib import Path

from src.core.analytics.resources import build_hypothesis_gate_report
from src.core.reporting.assembler import ReportAssembler


def test_light_integration_evidence_gate_and_assemble(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_light"
    (session_dir / "plan").mkdir(parents=True, exist_ok=True)
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "plots").mkdir(parents=True, exist_ok=True)

    (session_dir / "plan" / "analysis_plan.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "id": "H1",
                        "title": "差异假设",
                        "hypothesis": "Normal 与 EP 存在差异",
                        "validation_plan_steps": ["差异检验", "多重检验校正"],
                        "expected_artifacts": ["result/stats_results.json"],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_results.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis": "H1", "steps": {"差异检验": {"status": "ok", "output": "done"}}, "missing": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    evidence_pack = {
        "hypotheses": [
            {
                "hypothesis_id": "H1",
                "claim": "supported",
                "status": "validated",
                "quant_metrics": [
                    {"name": "significant_p_lt_0_05", "display_name": "显著特征数", "value": 3, "unit": "count", "threshold": ">=1", "direction": "higher_is_stronger", "category": "significance"},
                    {"name": "strongest_abs_corr", "display_name": "最强绝对相关系数", "value": 0.68, "unit": "corr", "threshold": ">=0.5", "direction": "higher_is_stronger", "category": "correlation"},
                ],
                "effect_metrics": [{"name": "strongest_abs_corr", "value": 0.68}],
                "method_trace": [{"path_id": "path_a", "method_family": "parametric_test", "status": "validated"}],
                "evidence_sources": ["result/stats_results.json"],
                "consistency": {"path_a": "ok", "path_b": "ok", "flag": "consistent"},
                "reason_code": "",
                "recovery_action": "",
            }
        ]
    }
    (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
        json.dumps(evidence_pack, ensure_ascii=False),
        encoding="utf-8",
    )
    gate = build_hypothesis_gate_report(evidence_pack)
    (session_dir / "result" / "hypothesis_gate_report.json").write_text(
        json.dumps(gate, ensure_ascii=False),
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_contrast.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "path_a": {"status": "ok", "metrics": {"significant_p_lt_0_05": 3}},
                        "path_b": {"status": "ok", "metrics": {"q_lt_0_05": 2}},
                        "consistency": "consistent",
                        "status": "validated",
                        "conflict_reason": "",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "result" / "stats_results.json").write_text("[]", encoding="utf-8")
    (session_dir / "plots" / "volcano_plot.png").write_bytes(b"fake")

    manifest = {
        "visualizations": [
            {
                "name": "volcano",
                "path": str(session_dir / "plots" / "volcano_plot.png"),
                "relative_path": "plots/volcano_plot.png",
                "metadata": {"type": "volcano"},
            }
        ],
        "tables": [
            {"name": "hypothesis_gate_report.json", "relative_path": "result/hypothesis_gate_report.json"}
        ],
    }
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest=manifest,
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "假设验证与结果分析" in html
    assert "门槛类型" in html
    assert "关键数值与阈值判定如下" in html
    assert "../plots/volcano_plot.png" in html
    audit_path = session_dir / "meta" / "report_substance_audit.json"
    assert audit_path.exists()
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert "numeric_sentence_coverage" in audit
    assert "evidence_binding_coverage" in audit
    assert audit.get("basis_coverage", 0) >= 1.0
    assert audit.get("conflict_coverage", 0) >= 1.0
    assert audit.get("boundary_coverage", 0) >= 1.0
    assert audit.get("next_step_coverage", 0) >= 1.0
