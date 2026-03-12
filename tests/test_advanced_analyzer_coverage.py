from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.core.analytics.advanced_analyzer import (
    AdvancedDataAnalyzer,
    AnalysisType,
    StatisticalTest,
    analyze_dataset,
    get_data_analyzer,
)


def test_advanced_analyzer_load_quality_and_report(monkeypatch, tmp_path: Path) -> None:
    updates = []
    monkeypatch.setattr("src.core.analytics.advanced_analyzer.update_session_state", lambda sid, payload: updates.append((sid, payload)) or True)
    analyzer = AdvancedDataAnalyzer()

    csv_path = tmp_path / "data.csv"
    df = pd.DataFrame(
        {
            "value": [1, 2, 3, 3, 4, 100],
            "group": ["A", "A", "B", "B", "B", "B"],
            "other": [10, None, 12, 12, 13, 13],
        }
    )
    df.to_csv(csv_path, index=False)
    loaded = analyzer.load_data(csv_path)
    assert loaded is not None and loaded.shape[0] == 6
    assert analyzer.load_data(tmp_path / "missing.csv") is None
    bad = tmp_path / "data.txt"
    bad.write_text("x", encoding="utf-8")
    assert analyzer.load_data(bad) is None

    quality = analyzer.assess_data_quality(loaded)
    assert quality.missing_values["other"] == 1
    assert quality.duplicates >= 1
    assert "value" in quality.outliers

    corr = analyzer.perform_statistical_tests(loaded, [StatisticalTest.CORRELATION])[0]
    assert corr.test_type == StatisticalTest.CORRELATION
    ttest = analyzer.perform_statistical_tests(loaded, [StatisticalTest.T_TEST], "value", "group")[0]
    assert ttest.effect_size is not None

    report = analyzer.generate_docs_analysis_report(loaded, "sess", [AnalysisType.DESCRIPTIVE, AnalysisType.INFERENTIAL])
    assert "quality_report" in report and report["statistical_results"]
    assert updates
    assert analyze_dataset(csv_path, "sess2")["data_summary"]["shape"][0] == 6
    assert isinstance(get_data_analyzer(), AdvancedDataAnalyzer)


def test_advanced_analyzer_normality_and_insights() -> None:
    analyzer = AdvancedDataAnalyzer()
    df = pd.DataFrame(
        {
            "value": [1.0, 1.2, 0.9, 1.1, 1.05, 0.95],
            "group": ["A", "A", "A", "B", "B", "B"],
        }
    )
    normality = analyzer.perform_statistical_tests(df, [StatisticalTest.NORMALITY], "value")
    assert normality and normality[0].test_type == StatisticalTest.NORMALITY

    quality = analyzer.assess_data_quality(df)
    insights = analyzer._generate_insights(df, quality)
    recs = analyzer._generate_recommendations(df, quality)
    assert isinstance(insights, list)
    assert recs
