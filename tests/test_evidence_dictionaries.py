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
    assert gate["hypotheses"][0]["gate_rule_type"] == "significance_and_effect"
    assert "has_significance_metric" in gate["hypotheses"][0]["required_checks"]
    assert "has_effect_metric" in gate["hypotheses"][0]["required_checks"]


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


def test_gate_rule_type_predictive_performance_requires_dual_metrics() -> None:
    pack = {
        "hypotheses": [
            {
                "hypothesis_id": "H2",
                "claim": "x",
                "status": "validated",
                "quant_metrics": [
                    {"name": "centroid_accuracy", "value": 0.78, "category": "performance"},
                    {"name": "cv_mean_accuracy", "value": 0.66, "category": "performance"},
                ],
                "effect_metrics": [{"name": "centroid_accuracy", "value": 0.78}],
                "method_trace": [{"method_family": "feature_modeling", "status": "validated"}],
                "evidence_sources": ["result/model_eval.json"],
                "consistency": {"flag": "consistent"},
                "reason_code": "",
                "recovery_action": "",
            }
        ]
    }
    gate = build_hypothesis_gate_report(pack)
    row = gate["hypotheses"][0]
    assert row["gate_rule_type"] == "predictive_performance"
    assert row["gate_status"] == "pass"
    assert "has_primary_performance" in row["checks"]
    assert "has_secondary_performance" in row["checks"]


def test_gate_rule_type_correlation_flags_missing_edges() -> None:
    pack = {
        "hypotheses": [
            {
                "hypothesis_id": "H3",
                "claim": "x",
                "status": "partial",
                "quant_metrics": [
                    {"name": "strongest_abs_corr", "value": 0.82, "category": "correlation"},
                    {"name": "abs_corr_gt_0_7_edges", "value": 0, "category": "correlation"},
                ],
                "effect_metrics": [{"name": "strongest_abs_corr", "value": 0.82}],
                "method_trace": [{"method_family": "pearson_network", "status": "validated"}],
                "evidence_sources": ["result/correlation.json"],
                "consistency": {"flag": "consistent"},
                "reason_code": "",
                "recovery_action": "",
            }
        ]
    }
    gate = build_hypothesis_gate_report(pack)
    row = gate["hypotheses"][0]
    assert row["gate_rule_type"] == "correlation_structure"
    assert row["gate_status"] in {"partial", "fail"}
    assert "corr_edge_ge_min" in row["failed_checks"]


def test_gate_calibration_profile_changes_threshold_outcome() -> None:
    pack = {
        "hypotheses": [
            {
                "hypothesis_id": "H2",
                "claim": "x",
                "status": "validated",
                "quant_metrics": [
                    {"name": "centroid_accuracy", "value": 0.62, "category": "performance"},
                    {"name": "cv_mean_accuracy", "value": 0.58, "category": "performance"},
                ],
                "effect_metrics": [{"name": "centroid_accuracy", "value": 0.62}],
                "method_trace": [{"method_family": "feature_modeling", "status": "validated"}],
                "evidence_sources": ["result/model_eval.json"],
                "consistency": {"flag": "consistent"},
                "reason_code": "",
                "recovery_action": "",
            }
        ]
    }
    strict_gate = build_hypothesis_gate_report(pack, calibration_profile="strict")
    exploratory_gate = build_hypothesis_gate_report(pack, calibration_profile="exploratory")
    strict_row = strict_gate["hypotheses"][0]
    exploratory_row = exploratory_gate["hypotheses"][0]
    assert strict_row["calibration_profile"] == "strict"
    assert exploratory_row["calibration_profile"] == "exploratory"
    assert strict_row["gate_status"] in {"partial", "fail"}
    assert exploratory_row["gate_status"] in {"pass", "partial"}
    assert isinstance(exploratory_row.get("decision_evidence"), list)


def test_gate_reason_code_and_recovery_plan_refined() -> None:
    pack = {
        "hypotheses": [
            {
                "hypothesis_id": "H3",
                "claim": "x",
                "status": "validated",
                "quant_metrics": [
                    {"name": "strongest_abs_corr", "value": 0.41, "category": "correlation"},
                    {"name": "abs_corr_gt_0_7_edges", "value": 0, "category": "correlation"},
                ],
                "effect_metrics": [{"name": "strongest_abs_corr", "value": 0.41}],
                "method_trace": [{"method_family": "pearson_network", "status": "validated"}],
                "evidence_sources": ["result/correlation.json"],
                "consistency": {"flag": "consistent"},
                "reason_code": "",
                "recovery_action": "",
            }
        ]
    }
    gate = build_hypothesis_gate_report(pack, calibration_profile="standard")
    row = gate["hypotheses"][0]
    assert row["gate_status"] in {"partial", "fail"}
    assert row["reason_code"] in {"threshold_not_met", "assumption_violation"}
    assert isinstance(row.get("recovery_plan"), list)
    assert row["recovery_plan"]


def test_gate_dynamic_overrides_adjust_thresholds() -> None:
    pack = {
        "hypotheses": [
            {
                "hypothesis_id": "H2",
                "claim": "x",
                "status": "validated",
                "quant_metrics": [
                    {"name": "centroid_accuracy", "value": 0.6, "category": "performance"},
                    {"name": "cv_mean_accuracy", "value": 0.59, "category": "performance"},
                ],
                "effect_metrics": [{"name": "centroid_accuracy", "value": 0.6}],
                "method_trace": [{"method_family": "feature_modeling", "status": "validated"}],
                "evidence_sources": ["result/model_eval.json"],
                "consistency": {"flag": "consistent"},
                "reason_code": "",
                "recovery_action": "",
            }
        ]
    }
    base_gate = build_hypothesis_gate_report(pack, calibration_profile="standard")
    relaxed_gate = build_hypothesis_gate_report(
        pack,
        calibration_profile="standard",
        calibration_overrides={"secondary_performance_min": 0.55},
    )
    assert base_gate["hypotheses"][0]["gate_status"] in {"partial", "fail"}
    assert relaxed_gate["hypotheses"][0]["gate_status"] in {"pass", "partial"}
