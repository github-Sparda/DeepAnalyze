#!/usr/bin/env python3
"""
Test Serum Orchestration Skill
功能性测试脚本 - 测试技能是否按预期执行

测试内容:
1. 环境检查功能
2. 产物全面质量评估功能
3. 问题诊断功能
4. 任务清单管理功能
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.serum_orchestration_skill import (
    SerumOrchestrationSkill,
    ArtifactQualityAnalyzer,
    QualityIssue,
    QualityScore,
)


class TestQualityIssue(unittest.TestCase):
    def test_quality_issue_creation(self):
        issue = QualityIssue(
            severity="critical",
            code="TEST-001",
            dimension="test_dimension",
            message="Test message",
        )
        self.assertEqual(issue.severity, "critical")
        self.assertEqual(issue.code, "TEST-001")

    def test_quality_issue_to_dict(self):
        issue = QualityIssue(
            severity="high",
            code="TEST-002",
            dimension="test_dimension",
            message="Test message",
            detail={"key": "value"},
        )
        result = issue.to_dict()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["severity"], "high")
        self.assertEqual(result["code"], "TEST-002")
        self.assertIn("detail", result)


class TestQualityScore(unittest.TestCase):
    def test_quality_score_creation(self):
        score = QualityScore(
            dimension="test_dimension",
            score=85,
            weight=0.25,
        )
        self.assertEqual(score.dimension, "test_dimension")
        self.assertEqual(score.score, 85)
        self.assertEqual(len(score.issues), 0)
        self.assertEqual(len(score.metrics), 0)

    def test_quality_score_with_issues(self):
        score = QualityScore(
            dimension="test_dimension",
            score=70,
            weight=0.25,
        )
        issue = QualityIssue("medium", "TEST-003", "test_dimension", "Test issue")
        score.issues.append(issue)
        self.assertEqual(len(score.issues), 1)

    def test_quality_score_to_dict(self):
        score = QualityScore(
            dimension="test_dimension",
            score=90,
            weight=0.25,
            metrics={"auc": 0.85},
        )
        result = score.to_dict()
        self.assertEqual(result["dimension"], "test_dimension")
        self.assertEqual(result["score"], 90)
        self.assertEqual(result["metrics"]["auc"], 0.85)


class TestArtifactQualityAnalyzer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_output_dir = Path(tempfile.mkdtemp(prefix="test_quality_"))
        cls.test_data_file = PROJECT_ROOT / "data" / "examples" / "serum" / "Normal_EP_serum_data.xlsx"
        if not cls.test_data_file.exists():
            raise unittest.SkipTest(f"Test data file not found: {cls.test_data_file}")

        cls.existing_session = PROJECT_ROOT / "outputs" / "serum_orchestrated" / "workspace"
        if cls.existing_session.exists():
            sessions = list(cls.existing_session.glob("serum_*"))
            if sessions:
                cls.existing_session = sessions[-1]
            else:
                cls.existing_session = None
        else:
            cls.existing_session = None

    @classmethod
    def tearDownClass(cls):
        if cls.test_output_dir.exists():
            shutil.rmtree(cls.test_output_dir, ignore_errors=True)

    def test_analyzer_initialization(self):
        session_dir = self.test_output_dir / "nonexistent"
        analyzer = ArtifactQualityAnalyzer(session_dir)
        self.assertEqual(analyzer.session_dir, session_dir)
        self.assertEqual(len(analyzer.issues), 0)
        self.assertEqual(len(analyzer.scores), 0)

    def test_dimension_weights(self):
        expected_dims = {
            "statistical_significance": 0.25,
            "model_performance": 0.25,
            "data_quality": 0.20,
            "visualization": 0.15,
            "report_completeness": 0.15,
        }
        self.assertEqual(ArtifactQualityAnalyzer.DIMENSION_WEIGHTS, expected_dims)

    def test_analyze_empty_session(self):
        session_dir = self.test_output_dir / "empty_session"
        session_dir.mkdir(parents=True, exist_ok=True)
        result_dir = session_dir / "result"
        result_dir.mkdir(parents=True, exist_ok=True)
        analyzer = ArtifactQualityAnalyzer(session_dir)
        result = analyzer.analyze()

        self.assertIn("overall_score", result)
        self.assertIn("dimensions", result)
        self.assertIn("critical_issues", result)
        self.assertGreaterEqual(result["overall_score"], 0)

    def test_analyze_existing_session(self):
        if not self.existing_session:
            self.skipTest("No existing session found")

        analyzer = ArtifactQualityAnalyzer(self.existing_session)
        result = analyzer.analyze()

        self.assertGreater(result["overall_score"], 0)
        self.assertIn("statistical_significance", result["dimensions"])
        self.assertIn("model_performance", result["dimensions"])
        self.assertIn("data_quality", result["dimensions"])
        self.assertIn("visualization", result["dimensions"])
        self.assertIn("report_completeness", result["dimensions"])

        for dim_data in result["dimensions"].values():
            self.assertIn("score", dim_data)
            self.assertIn("weight", dim_data)
            self.assertIn("issues", dim_data)
            self.assertGreaterEqual(dim_data["score"], 0)
            self.assertLessEqual(dim_data["score"], 100)

    def test_statistical_significance_analysis_no_file(self):
        session_dir = self.test_output_dir / "no_stats"
        session_dir.mkdir(parents=True, exist_ok=True)
        analyzer = ArtifactQualityAnalyzer(session_dir)
        analyzer._analyze_statistical_significance()

        stat_score = analyzer.scores["statistical_significance"]
        self.assertLess(stat_score.score, 100)
        self.assertTrue(any("stats_summary.json" in i.message for i in stat_score.issues))

    def test_model_performance_analysis_no_files(self):
        session_dir = self.test_output_dir / "no_models"
        session_dir.mkdir(parents=True, exist_ok=True)
        result_dir = session_dir / "result"
        result_dir.mkdir(parents=True, exist_ok=True)
        analyzer = ArtifactQualityAnalyzer(session_dir)
        analyzer._analyze_model_performance()

        model_score = analyzer.scores["model_performance"]
        self.assertLess(model_score.score, 100)
        self.assertTrue(any("缺少模型性能相关文件" in i.message for i in model_score.issues))

    def test_data_quality_analysis_no_file(self):
        session_dir = self.test_output_dir / "no_dq"
        session_dir.mkdir(parents=True, exist_ok=True)
        result_dir = session_dir / "result"
        result_dir.mkdir(parents=True, exist_ok=True)
        analyzer = ArtifactQualityAnalyzer(session_dir)
        analyzer._analyze_data_quality()

        dq_score = analyzer.scores["data_quality"]
        self.assertLess(dq_score.score, 100)

    def test_visualization_analysis_no_dir(self):
        session_dir = self.test_output_dir / "no_plots"
        session_dir.mkdir(parents=True, exist_ok=True)
        analyzer = ArtifactQualityAnalyzer(session_dir)
        analyzer._analyze_visualization()

        viz_score = analyzer.scores["visualization"]
        self.assertLess(viz_score.score, 100)
        self.assertTrue(any("缺少 plots 目录" in i.message for i in viz_score.issues))

    def test_report_completeness_analysis_no_dir(self):
        session_dir = self.test_output_dir / "no_report"
        session_dir.mkdir(parents=True, exist_ok=True)
        analyzer = ArtifactQualityAnalyzer(session_dir)
        analyzer._analyze_report_completeness()

        rpt_score = analyzer.scores["report_completeness"]
        self.assertLess(rpt_score.score, 100)
        self.assertTrue(any("缺少 report 目录" in i.message for i in rpt_score.issues))

    def test_calculate_std(self):
        values = [0.5, 0.6, 0.7, 0.8]
        std = ArtifactQualityAnalyzer._calculate_std(values)
        self.assertGreater(std, 0)

    def test_calculate_std_empty(self):
        std = ArtifactQualityAnalyzer._calculate_std([])
        self.assertEqual(std, 0)


class TestSerumOrchestrationSkill(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_output_dir = Path(tempfile.mkdtemp(prefix="test_serum_"))
        cls.test_data_file = PROJECT_ROOT / "data" / "examples" / "serum" / "Normal_EP_serum_data.xlsx"
        if not cls.test_data_file.exists():
            raise unittest.SkipTest(f"Test data file not found: {cls.test_data_file}")

    @classmethod
    def tearDownClass(cls):
        if cls.test_output_dir.exists():
            shutil.rmtree(cls.test_output_dir, ignore_errors=True)

    def setUp(self):
        self.skill = SerumOrchestrationSkill(
            data_file=str(self.test_data_file),
            output_dir=str(self.test_output_dir / "output1"),
            max_depth=1,
        )

    def test_check_environment_data_file_exists(self):
        result = self.skill.check_environment()
        self.assertTrue(result["data_file_exists"])
        self.assertGreater(result["data_file_size"], 0)

    def test_check_environment_output_dir_writable(self):
        result = self.skill.check_environment()
        self.assertTrue(result["output_dir_writable"])

    def test_check_environment_python_version(self):
        result = self.skill.check_environment()
        self.assertIn("python_version", result)
        self.assertTrue(result["python_version"].startswith("3."))

    def test_add_task(self):
        self.skill._add_task("TEST-001", "测试任务", "P1", "test", ["操作1", "操作2"])
        self.assertEqual(len(self.skill.optimization_tasks), 1)
        task = self.skill.optimization_tasks[0]
        self.assertEqual(task["id"], "TEST-001")
        self.assertEqual(task["title"], "测试任务")
        self.assertEqual(task["priority"], "P1")
        self.assertEqual(task["status"], "pending")
        self.assertIn("detected_at", task)

    def test_diagnose_no_session(self):
        diagnosis = self.skill.diagnose()
        self.assertIn("issues", diagnosis)
        self.assertIn("warnings", diagnosis)
        self.assertIn("recommendations", diagnosis)
        self.assertIn("timestamp", diagnosis)

    def test_diagnose_detects_missing_data_file(self):
        self.skill.data_file = Path("/nonexistent/file.xlsx")
        diagnosis = self.skill.diagnose()
        critical_issues = [i for i in diagnosis["issues"] if i["severity"] == "critical"]
        self.assertTrue(len(critical_issues) > 0)
        self.assertTrue(any("不存在" in i["message"] for i in critical_issues))

    def test_save_optimization_tasks(self):
        self.skill._add_task("TEST-001", "测试任务", "P1", "test", ["操作1"])
        output_path = self.skill.save_optimization_tasks()
        self.assertTrue(output_path.exists())

        with open(output_path, encoding="utf-8") as f:
            saved_data = json.load(f)

        self.assertEqual(saved_data["total_tasks"], 1)
        self.assertIn("generated_at", saved_data)
        self.assertIn("quality_score", saved_data)

    def test_save_optimization_tasks_by_priority(self):
        self.skill._add_task("P0-001", "P0任务", "P0", "test", [])
        self.skill._add_task("P1-001", "P1任务", "P1", "test", [])
        self.skill._add_task("P2-001", "P2任务", "P2", "test", [])

        output_path = self.skill.save_optimization_tasks()

        with open(output_path, encoding="utf-8") as f:
            saved_data = json.load(f)

        self.assertEqual(len(saved_data["by_priority"]["P0"]), 1)
        self.assertEqual(len(saved_data["by_priority"]["P1"]), 1)
        self.assertEqual(len(saved_data["by_priority"]["P2"]), 1)

    def test_get_report_no_session(self):
        report = self.skill.get_report()
        self.assertIsNone(report)

    def test_build_result_structure(self):
        result = self.skill._build_result()
        self.assertIn("execution_time", result)
        self.assertIn("session_id", result)
        self.assertIn("session_dir", result)
        self.assertIn("quality_report", result)
        self.assertIn("optimization_tasks", result)
        self.assertIn("execution_log", result)


class TestSerumOrchestrationSkillIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_output_dir = Path(tempfile.mkdtemp(prefix="test_serum_integration_"))
        cls.test_data_file = PROJECT_ROOT / "data" / "examples" / "serum" / "Normal_EP_serum_data.xlsx"
        if not cls.test_data_file.exists():
            raise unittest.SkipTest(f"Test data file not found: {cls.test_data_file}")

        cls.existing_session = PROJECT_ROOT / "outputs" / "serum_orchestrated" / "workspace"
        if cls.existing_session.exists():
            sessions = list(cls.existing_session.glob("serum_*"))
            if sessions:
                cls.existing_session = sessions[-1]
            else:
                cls.existing_session = None
        else:
            cls.existing_session = None

    @classmethod
    def tearDownClass(cls):
        if cls.test_output_dir.exists():
            shutil.rmtree(cls.test_output_dir, ignore_errors=True)

    def setUp(self):
        self.skill = SerumOrchestrationSkill(
            data_file=str(self.test_data_file),
            output_dir=str(self.test_output_dir),
        )

    def test_analyze_quality_existing_session(self):
        if not self.existing_session:
            self.skipTest("No existing session found")

        self.skill.session_dir = self.existing_session
        quality_report = self.skill.analyze_artifacts_quality()

        self.assertIn("overall_score", quality_report)
        self.assertIn("dimensions", quality_report)
        self.assertGreater(quality_report["overall_score"], 0)

    def test_diagnose_existing_session_with_quality(self):
        if not self.existing_session:
            self.skipTest("No existing session found")

        self.skill.session_dir = self.existing_session
        self.skill.quality_report = self.skill.analyze_artifacts_quality()
        diagnosis = self.skill.diagnose()

        self.assertIn("timestamp", diagnosis)
        self.assertIn("quality_report", diagnosis)
        self.assertIsInstance(diagnosis["issues"], list)
        self.assertIsInstance(diagnosis["warnings"], list)


class TestSerumOrchestrationSkillEdgeCases(unittest.TestCase):
    def setUp(self):
        self.test_output_dir = Path(tempfile.mkdtemp(prefix="test_serum_edge_"))
        self.test_data_file = PROJECT_ROOT / "data" / "examples" / "serum" / "Normal_EP_serum_data.xlsx"

    def tearDown(self):
        if self.test_output_dir.exists():
            shutil.rmtree(self.test_output_dir, ignore_errors=True)

    def test_invalid_data_file_path(self):
        skill = SerumOrchestrationSkill(
            data_file="/invalid/path/to/file.xlsx",
            output_dir=str(self.test_output_dir),
        )
        result = skill.check_environment()
        self.assertFalse(result["data_file_exists"])

    def test_empty_analysis_goal(self):
        skill = SerumOrchestrationSkill(
            data_file=str(self.test_data_file),
            output_dir=str(self.test_output_dir),
            analysis_goal="",
        )
        self.assertEqual(skill.analysis_goal, "")

    def test_max_depth_zero(self):
        skill = SerumOrchestrationSkill(
            data_file=str(self.test_data_file),
            output_dir=str(self.test_output_dir),
            max_depth=0,
        )
        self.assertEqual(skill.max_depth, 0)

    def test_multiple_tasks_same_id(self):
        skill = SerumOrchestrationSkill(
            data_file=str(self.test_data_file),
            output_dir=str(self.test_output_dir),
        )
        skill._add_task("DUP-001", "Task 1", "P1", "test", [])
        skill._add_task("DUP-001", "Task 2", "P1", "test", [])
        self.assertEqual(len(skill.optimization_tasks), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
