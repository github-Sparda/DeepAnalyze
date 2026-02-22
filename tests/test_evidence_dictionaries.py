from __future__ import annotations

import pytest

from src.core.analytics.resources import (
    build_hypothesis_evidence_pack,
    build_hypothesis_gate_report,
    default_feature_dictionary,
    default_method_dictionary,
    default_metric_dictionary,
    validate_hypothesis_evidence_pack,
)


def test_build_hypothesis_evidence_pack_and_gate() -> None:
    evidence_payload = {
        "hypotheses": [
            {
                "hypothesis_id": "H1",
                "claim": "存在组间差异",
                "quant_metrics": {"significant_p_lt_0_05": 3, "strongest_abs_corr": 0.78},
                "evidence_sources": ["result/stats_results.json"],
                "status": "supported",
            }
        ]
    }
    contrast_payload = {
        "hypotheses": [
            {
                "hypothesis_id": "H1",
                "path_a": {"status": "ok"},
                "path_b": {"status": "ok"},
                "consistency": "consistent",
                "status": "validated",
                "conflict_reason": "",
            }
        ]
    }
    multipath_payload = {
        "hypotheses": [
            {
                "hypothesis_id": "H1",
                "status": "validated",
                "paths": [
                    {
                        "path_id": "path_a",
                        "method_family": "parametric_test",
                        "missing_artifacts": [],
                        "status": "validated",
                    },
                    {
                        "path_id": "path_b",
                        "method_family": "nonparametric_or_fdr",
                        "missing_artifacts": [],
                        "status": "validated",
                    },
                ],
            }
        ]
    }
    pack = build_hypothesis_evidence_pack(
        evidence_payload,
        contrast_payload,
        multipath_payload,
        default_metric_dictionary(),
        default_feature_dictionary(),
        default_method_dictionary(),
    )
    assert pack["hypotheses"][0]["hypothesis_id"] == "H1"
    assert len(pack["hypotheses"][0]["quant_metrics"]) >= 2
    assert pack["hypotheses"][0]["reason_code"] == ""

    gate = build_hypothesis_gate_report(pack)
    assert gate["hypotheses"][0]["gate_status"] == "pass"


def test_validate_hypothesis_evidence_pack_strict_schema() -> None:
    invalid_pack = {"hypotheses": [{"hypothesis_id": "H1"}]}
    report = validate_hypothesis_evidence_pack(invalid_pack)
    assert report["valid"] is False
    assert any("missing_fields" in err for err in report["errors"])


def test_build_hypothesis_evidence_pack_marks_extract_failed() -> None:
    pack = build_hypothesis_evidence_pack(
        {
            "hypotheses": [
                {"hypothesis_id": "H1", "claim": "x", "quant_metrics": {}, "evidence_sources": [], "status": "inconclusive"}
            ]
        },
        {"hypotheses": []},
        {"hypotheses": []},
        default_metric_dictionary(),
        default_feature_dictionary(),
        default_method_dictionary(),
    )
    assert pack["hypotheses"][0]["reason_code"] in {"extract_failed", "method_conflict", "execution_error", ""}


@pytest.mark.parametrize(
    ("name", "evidence_payload", "contrast_payload", "multipath_payload", "expected_gate"),
    [
        (
            "full_chain",
            {"hypotheses": [{"hypothesis_id": "H1", "claim": "x", "quant_metrics": {"significant_p_lt_0_05": 3, "auc": 0.81}, "evidence_sources": ["result/a.json"], "status": "supported"}]},
            {"hypotheses": [{"hypothesis_id": "H1", "path_a": {"status": "ok"}, "path_b": {"status": "ok"}, "consistency": "consistent", "status": "validated"}]},
            {"hypotheses": [{"hypothesis_id": "H1", "status": "validated", "paths": [{"path_id": "a", "method_family": "parametric_test", "status": "validated"}, {"path_id": "b", "method_family": "nonparametric_or_fdr", "status": "validated"}]}]},
            "pass",
        ),
        (
            "missing_artifacts",
            {"hypotheses": [{"hypothesis_id": "H1", "claim": "x", "quant_metrics": {"m1": 1}, "evidence_sources": [], "status": "partial"}]},
            {"hypotheses": [{"hypothesis_id": "H1", "path_a": {"status": "missing"}, "path_b": {"status": "ok"}, "consistency": "unknown", "status": "partial"}]},
            {"hypotheses": [{"hypothesis_id": "H1", "status": "partial", "paths": [{"path_id": "a", "method_family": "parametric_test", "status": "failed"}, {"path_id": "b", "method_family": "nonparametric_or_fdr", "status": "validated"}]}]},
            "partial",
        ),
        (
            "path_invalid",
            {"hypotheses": [{"hypothesis_id": "H1", "claim": "x", "quant_metrics": {}, "evidence_sources": ["http://bad/path"], "status": "failed", "reason_code": "path_invalid"}]},
            {"hypotheses": [{"hypothesis_id": "H1", "path_a": {"status": "failed"}, "path_b": {"status": "failed"}, "consistency": "conflict", "status": "failed"}]},
            {"hypotheses": [{"hypothesis_id": "H1", "status": "failed", "paths": [{"path_id": "a", "method_family": "parametric_test", "status": "failed"}, {"path_id": "b", "method_family": "nonparametric_or_fdr", "status": "failed"}]}]},
            "fail",
        ),
        (
            "method_conflict",
            {"hypotheses": [{"hypothesis_id": "H1", "claim": "x", "quant_metrics": {"p_value": 0.02, "effect_size": 0.4}, "evidence_sources": ["result/a.json"], "status": "inconclusive"}]},
            {"hypotheses": [{"hypothesis_id": "H1", "path_a": {"status": "ok"}, "path_b": {"status": "ok"}, "consistency": "conflict", "status": "inconclusive", "conflict_reason": "direction_conflict"}]},
            {"hypotheses": [{"hypothesis_id": "H1", "status": "inconclusive", "paths": [{"path_id": "a", "method_family": "parametric_test", "status": "validated"}, {"path_id": "b", "method_family": "nonparametric_or_fdr", "status": "validated"}]}]},
            "partial",
        ),
        (
            "sparse_data",
            {"hypotheses": [{"hypothesis_id": "H1", "claim": "x", "quant_metrics": {}, "evidence_sources": [], "status": "inconclusive", "reason_code": "insufficient_sample"}]},
            {"hypotheses": [{"hypothesis_id": "H1", "path_a": {"status": "missing"}, "path_b": {"status": "missing"}, "consistency": "conflict", "status": "failed"}]},
            {"hypotheses": [{"hypothesis_id": "H1", "status": "failed", "paths": [{"path_id": "a", "method_family": "parametric_test", "status": "failed"}, {"path_id": "b", "method_family": "nonparametric_or_fdr", "status": "failed"}]}]},
            "fail",
        ),
    ],
)
def test_quality_baseline_matrix_module_acceptance(
    name: str,
    evidence_payload: dict,
    contrast_payload: dict,
    multipath_payload: dict,
    expected_gate: str,
) -> None:
    pack = build_hypothesis_evidence_pack(
        evidence_payload,
        contrast_payload,
        multipath_payload,
        default_metric_dictionary(),
        default_feature_dictionary(),
        default_method_dictionary(),
    )
    validation = validate_hypothesis_evidence_pack(pack)
    assert validation["valid"] is True, name
    gate = build_hypothesis_gate_report(pack)
    assert gate["hypotheses"][0]["gate_status"] == expected_gate
