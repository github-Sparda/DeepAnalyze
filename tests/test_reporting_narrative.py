from src.core.reporting.narrative import (
    detect_metric_conflicts_detailed,
    failed_check_review_steps,
    recovery_action_sentence,
    metric_narrative,
)


def test_metric_narrative_contains_implication_for_cv_std() -> None:
    text = metric_narrative(
        {
            "name": "cv_std_accuracy",
            "display_name": "交叉验证准确率标准差",
            "value": 0.0138,
            "unit": "ratio",
        }
    )
    assert "交叉验证准确率标准差" in text
    assert "波动较小" in text


def test_detect_metric_conflicts_detailed_returns_structured_items() -> None:
    findings = detect_metric_conflicts_detailed(
        [
            {"name": "centroid_accuracy", "value": 0.0},
            {"name": "cv_mean_accuracy", "value": 0.71},
        ]
    )
    assert findings
    first = findings[0]
    assert first.get("title") == "分类性能指标冲突"
    assert "centroid_accuracy=0" in str(first.get("evidence"))
    assert isinstance(first.get("next_steps"), list)


def test_failed_check_review_steps_contains_path_consistency_steps() -> None:
    steps = failed_check_review_steps("path_consistency")
    assert steps
    assert "路径 A/B" in steps[0]


def test_recovery_action_sentence_translates_known_action() -> None:
    text = recovery_action_sentence("run_third_path_and_compare_stability")
    assert "第三验证路径" in text
    assert "run_third_path_and_compare_stability" in text
