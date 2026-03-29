#!/usr/bin/env python3
"""
Serum Orchestrated Analysis Skill - Deep Analyzer
深度产物分析与优化方案生成

功能:
1. 环境检查与配置验证
2. 脚本执行与输出捕获
3. 产物深度分析与问题发掘
4. 可执行优化方案生成
5. 任务清单管理与持续改进
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class Problem:
    severity: str
    code: str
    dimension: str
    problem: str
    location: str
    evidence: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "dimension": self.dimension,
            "problem": self.problem,
            "location": self.location,
            "evidence": self.evidence,
        }


@dataclass
class OptimizationTask:
    id: str
    title: str
    priority: str
    dimension: str
    target: str
    problem_summary: str
    steps: List[str]
    expected_improvement: str
    estimated_effort: str
    status: str = "pending"
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "priority": self.priority,
            "dimension": self.dimension,
            "target": self.target,
            "problem_summary": self.problem_summary,
            "steps": self.steps,
            "expected_improvement": self.expected_improvement,
            "estimated_effort": self.estimated_effort,
            "status": self.status,
            "created_at": self.created_at,
        }


class ArtifactDeepAnalyzer:
    """产物深度分析器 - 发现问题并生成优化方案"""

    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.problems: List[Problem] = []
        self.tasks: List[OptimizationTask] = []
        self.task_counter = 0

    def _new_task_id(self) -> str:
        self.task_counter += 1
        return f"OPT-{self.task_counter:03d}"

    def _add_problem(self, severity: str, code: str, dimension: str, problem: str, location: str, evidence: Dict = None) -> None:
        self.problems.append(Problem(severity, code, dimension, problem, location, evidence))

    def _add_task(self, title: str, priority: str, dimension: str, target: str, problem_summary: str, steps: List[str], expected: str, effort: str) -> None:
        self.tasks.append(OptimizationTask(
            id=self._new_task_id(),
            title=title,
            priority=priority,
            dimension=dimension,
            target=target,
            problem_summary=problem_summary,
            steps=steps,
            expected_improvement=expected,
            estimated_effort=effort,
            created_at=datetime.now().isoformat(),
        ))

    def analyze(self) -> Dict[str, Any]:
        """执行深度分析"""
        print(f"开始深度分析: {self.session_dir.name}")
        self._analyze_statistical_module()
        self._analyze_model_module()
        self._analyze_visualization_module()
        self._analyze_code_quality()
        self._analyze_report_quality()
        self._analyze_data_processing()
        self._analyze_orchestration_flow()
        self._generate_optimization_tasks()
        return self._build_report()

    def _analyze_statistical_module(self) -> None:
        stats_file = self.session_dir / "result" / "stats_summary.json"
        if not stats_file.exists():
            self._add_problem("critical", "STAT-001", "statistical", "统计结果文件不存在", "result/stats_summary.json")
            self._add_task("修复统计模块执行", "P0", "statistical", "result/stats_summary.json", "统计结果文件未生成", ["检查统计模块代码", "验证数据输入", "查看执行日志"], "生成完整的统计结果", "medium")
            return
        try:
            with open(stats_file, encoding="utf-8") as f:
                stats_data = json.load(f)
        except Exception as e:
            self._add_problem("critical", "STAT-002", "statistical", f"统计结果解析失败: {e}", str(stats_file))
            return
        if not stats_data or len(stats_data) == 0:
            self._add_problem("critical", "STAT-003", "statistical", "统计结果为空", str(stats_file))
            return
        valid_tests = 0
        significant_features = 0
        p_values = []
        for item in stats_data:
            if not isinstance(item, dict):
                continue
            p_val = item.get("p_value") or item.get("pvalue")
            if p_val and isinstance(p_val, (int, float)):
                p_values.append(p_val)
                valid_tests += 1
                if p_val < 0.05:
                    significant_features += 1
        if valid_tests == 0:
            self._add_problem("critical", "STAT-004", "statistical", "没有有效的统计检验结果", "stats_summary.json", {"total_items": len(stats_data)})
            self._add_task("修复统计检验流程", "P0", "statistical", "stats_summary.json", "没有有效的统计检验结果，可能是数据预处理或统计方法问题", ["检查数据预处理步骤", "验证组别划分", "检查统计方法调用"], "生成有效的p值和fold change", "medium")
        else:
            sig_p005 = len([p for p in p_values if p < 0.05])
            sig_p001 = len([p for p in p_values if p < 0.01])
            very_significant = len([p for p in p_values if p < 1e-10])

            if sig_p005 == 0:
                self._add_problem("high", "STAT-005", "statistical", f"没有发现显著差异的特征 (共{valid_tests}个检验)", "stats_summary.json", {"valid_tests": valid_tests, "significant": 0})
                self._add_task("调查差异缺失原因", "P1", "statistical", "stats_summary.json", f"{valid_tests}个检验中无显著结果，可能数据噪声过大或分组不合理", ["检查组间差异可视化", "验证样本分组", "考虑降噪处理"], "发现具有统计显著性的特征", "medium")
            else:
                self._add_problem("low", "STAT-SIG-001", "statistical", f"显著特征数量: {sig_p005}/{valid_tests} (p<0.05), {sig_p001} (p<0.01)", "stats_summary.json", {"sig_p005": sig_p005, "sig_p001": sig_p001, "total": valid_tests})

            if p_values:
                min_p = min(p_values)
                if min_p > 0.01:
                    self._add_problem("medium", "STAT-006", "statistical", f"最小p值({min_p:.2e})较大，缺乏强效应特征", "stats_summary.json", {"min_p": min_p})

                if very_significant > len(p_values) * 0.5:
                    self._add_problem("medium", "STAT-007", "statistical", f"{very_significant}/{len(p_values)}({very_significant/len(p_values)*100:.1f}%)特征p值极小(<1e-10)，可能存在多重比较问题", "stats_summary.json", {"extreme_p_count": very_significant})
                    self._add_task("添加多重比较校正", "P1", "statistical", "stats_summary.json", "未进行多重比较校正，可能导致假阳性率过高", ["添加Bonferroni或FDR校正", "更新结果报告", "重新定义显著性阈值"], "校正后仍有显著结果", "low")

            self._add_problem("low", "STAT-INFO-001", "statistical", f"统计检验完成，共{valid_tests}个特征，其中{sig_p005}个显著(p<0.05)", "stats_summary.json", {"total": valid_tests, "significant": sig_p005})
        mt_file = self.session_dir / "result" / "multiple_testing.json"
        if not mt_file.exists():
            self._add_problem("low", "STAT-008", "statistical", "缺少多重比较校正结果", "result/")

    def _analyze_model_module(self) -> None:
        model_file = self.session_dir / "result" / "model_results.json"
        cv_file = self.session_dir / "result" / "cv_results.json"
        if not model_file.exists():
            self._add_problem("critical", "MODEL-001", "model", "模型结果文件不存在", "result/model_results.json")
            self._add_task("修复模型训练流程", "P0", "model", "result/model_results.json", "模型结果文件未生成", ["检查模型训练代码", "验证数据格式", "查看执行日志"], "生成完整的模型结果", "medium")
            return
        try:
            with open(model_file, encoding="utf-8") as f:
                model_data = json.load(f)
        except Exception as e:
            self._add_problem("critical", "MODEL-002", "model", f"模型结果解析失败: {e}", str(model_file))
            return

        test_acc = model_data.get("test_accuracy")
        train_acc = model_data.get("train_accuracy")
        has_auc = "auc" in str(model_data).lower()
        cv_data = {}
        if cv_file.exists():
            try:
                with open(cv_file, encoding="utf-8") as f:
                    cv_data = json.load(f)
            except:
                pass

        if not test_acc:
            self._add_problem("critical", "MODEL-003", "model", "缺少测试集准确率", str(model_file))
            return

        if isinstance(test_acc, (int, float)) and test_acc < 0.7:
            self._add_problem("high", "MODEL-004", "model", f"测试集准确率({test_acc:.3f})过低，模型预测能力不足", str(model_file), {"test_accuracy": test_acc})
            self._add_task("提升模型性能", "P1", "model", str(model_file), f"测试准确率仅{test_acc:.3f}，低于0.7阈值，模型泛化能力不足", ["检查特征选择", "尝试其他模型", "增加样本量", "检查过拟合"], "测试准确率提升至0.8以上", "medium")

        if not has_auc:
            self._add_problem("medium", "MODEL-AUC-001", "model", "模型缺少AUC/AUC-ROC指标，仅使用准确率无法全面评估二分类性能", str(model_file), {"has_auc": False})
            self._add_task("添加模型性能评估指标(AUC)", "P1", "model", str(model_file), "模型结果中缺少AUC/AUC-ROC指标，仅使用准确率无法全面评估二分类性能", ["在train_and_evaluate.py中添加roc_auc_score计算", "获取预测概率而非仅预测类别", "调用sklearn.metrics.roc_auc_score计算AUC", "同时计算precision、recall、f1分数", "将AUC等指标添加到model_results.json输出中"], "模型性能评估更全面，可验证模型在不同阈值下的表现", "low")

        if train_acc and test_acc:
            overfitting_gap = train_acc - test_acc
            if overfitting_gap > 0.15:
                self._add_problem("high", "MODEL-005", "model", f"训练-测试准确率差距过大({overfitting_gap:.3f})，可能存在过拟合", str(model_file), {"train": train_acc, "test": test_acc, "gap": overfitting_gap})
                self._add_task("解决过拟合问题", "P1", "model", str(model_file), f"训练准确率{train_acc:.3f}与测试准确率{test_acc:.3f}差距{overfitting_gap:.3f}，明显过拟合", ["添加正则化", "减少模型复杂度", "增加训练数据", "使用交叉验证"], "过拟合差距控制在0.1以内", "medium")
            elif overfitting_gap > 0.05:
                self._add_problem("low", "MODEL-006", "model", f"训练-测试准确率存在一定差距({overfitting_gap:.3f})", str(model_file), {"train": train_acc, "test": test_acc, "gap": overfitting_gap})

        n_features = len(model_data.get("numeric_features", []))
        if n_features > 100:
            self._add_problem("medium", "MODEL-007", "model", f"使用了{n_features}个特征，可能存在维度灾难或过拟合风险", str(model_file), {"n_features": n_features})
            self._add_task("进行特征选择优化", "P2", "model", str(model_file), f"特征数量({n_features})过多，可能导致过拟合和计算效率低", ["使用特征重要性排序选择Top特征", "尝试LASSO降维", "基于统计显著性选择"], "减少特征数量同时保持或提升模型性能", "medium")

    def _analyze_visualization_module(self) -> None:
        plots_dir = self.session_dir / "plots"
        if not plots_dir.exists():
            self._add_problem("critical", "VIZ-001", "visualization", "图表目录不存在", "plots/")
            self._add_task("修复可视化流程", "P0", "visualization", "plots/", "图表目录未生成", ["检查可视化代码", "验证图表生成逻辑", "查看错误日志"], "生成所有计划的图表", "medium")
            return
        png_files = list(plots_dir.glob("*.png"))
        if len(png_files) == 0:
            self._add_problem("critical", "VIZ-002", "visualization", "没有生成任何图表", "plots/")
            self._add_task("修复图表生成", "P0", "visualization", "plots/", "所有图表生成失败", ["检查matplotlib配置", "验证数据格式", "查看异常日志"], "生成完整的可视化图表", "medium")
            return
        essential_plots = ["volcano_plot.png", "heatmap.png", "clustermap.png"]
        missing = [p for p in essential_plots if not (plots_dir / p).exists()]
        if missing:
            self._add_problem("medium", "VIZ-003", "visualization", f"缺少关键图表: {', '.join(missing)}", "plots/", {"missing": missing})
            self._add_task("补充缺失图表", "P2", "visualization", f"plots/{missing[0]}" if missing else "plots/", f"缺少关键图表: {missing}，影响结果解读", ["检查图表生成逻辑", "补充缺失的可视化"], "所有关键图表都已生成", "low")

    def _analyze_code_quality(self) -> None:
        code_dir = self.session_dir / "code"
        if not code_dir.exists():
            self._add_problem("low", "CODE-001", "code", "代码目录不存在", "code/")
            return
        py_files = list(code_dir.glob("*.py"))
        if len(py_files) == 0:
            self._add_problem("low", "CODE-002", "code", "没有生成任何代码文件", "code/")
        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8")
                if len(content) < 500:
                    self._add_problem("medium", "CODE-003", "code", f"代码文件过小({len(content)}字节)，可能生成不完整", str(py_file), {"size": len(content)})
                if "except:" in content and "except Exception:" not in content:
                    self._add_problem("low", "CODE-004", "code", "代码使用了过于宽泛的异常捕获", str(py_file))
            except Exception as e:
                self._add_problem("low", "CODE-006", "code", f"代码文件读取失败: {e}", str(py_file))

    def _analyze_report_quality(self) -> None:
        report_dir = self.session_dir / "report"
        if not report_dir.exists():
            self._add_problem("critical", "RPT-001", "report", "报告目录不存在", "report/")
            self._add_task("修复报告生成流程", "P0", "report", "report/", "报告目录未生成", ["检查报告生成代码", "验证模板文件", "查看错误日志"], "生成完整的分析报告", "medium")
            return
        report_files = sorted(report_dir.glob("report_v*.*"))
        if not report_files:
            self._add_problem("critical", "RPT-002", "report", "没有生成报告文件", "report/")
            return
        latest_report = report_files[-1]
        size_kb = latest_report.stat().st_size / 1024
        if size_kb < 20:
            self._add_problem("high", "RPT-003", "report", f"报告文件过小({size_kb:.1f}KB)，内容可能不完整", str(latest_report), {"Size_kb": size_kb})
            self._add_task("补充报告内容", "P1", "report", str(latest_report), f"报告仅{size_kb:.1f}KB，内容严重不足", ["检查报告模板", "验证章节生成", "补充缺失内容"], "报告内容完整充实", "medium")
        outline_file = report_dir / "report_outline.md"
        if outline_file.exists():
            outline = outline_file.read_text(encoding="utf-8")
            if len(outline) < 1500:
                self._add_problem("medium", "RPT-004", "report", f"报告大纲过短({len(outline)}字符)，内容不够详细", str(outline_file), {"outline_length": len(outline)})
                self._add_task("完善分析报告内容", "P2", "report", str(outline_file), f"报告大纲仅{len(outline)}字符，内容不够详细", ["检查当前报告各章节字数", "补充方法学详细描述", "添加结果的安全边际分析", "完善讨论章节的生物学意义", "添加Limitations章节"], "报告内容充实，符合学术规范", "medium")

    def _analyze_data_processing(self) -> None:
        dq_file = self.session_dir / "result" / "data_quality.json"
        if not dq_file.exists():
            self._add_problem("medium", "DP-001", "data_processing", "数据质量报告不存在", "result/data_quality.json")
            return
        try:
            with open(dq_file, encoding="utf-8") as f:
                dq_data = json.load(f)
            datasets = dq_data.get("datasets", [])
            if datasets and len(datasets) > 0:
                ds = datasets[0]
                rows = ds.get("rows", 0)
                if rows < 100:
                    self._add_problem("high", "DP-003", "data_processing", f"样本量过小({rows})，统计效力不足", str(dq_file), {"rows": rows})
        except Exception as e:
            self._add_problem("medium", "DP-002", "data_processing", f"数据质量报告解析失败: {e}", str(dq_file))

    def _analyze_orchestration_flow(self) -> None:
        logs_dir = self.session_dir / "outputs_logs" / "execution"
        if not logs_dir.exists():
            self._add_problem("low", "ORCH-001", "orchestration", "执行日志目录不存在", "outputs_logs/execution/")
            return
        log_files = list(logs_dir.glob("*.json"))
        if len(log_files) < 3:
            self._add_problem("medium", "ORCH-002", "orchestration", f"执行日志文件较少({len(log_files)})，可能部分节点未执行", "outputs_logs/execution/", {"log_count": len(log_files)})
            self._add_task("检查编排流程完整性", "P2", "orchestration", "outputs_logs/execution/", f"仅{len(log_files)}个执行日志，预期应有更多节点", ["检查各节点执行状态", "验证节点依赖关系", "查看跳过原因"], "所有关键节点都已执行", "low")

    def _generate_optimization_tasks(self) -> None:
        critical = [p for p in self.problems if p.severity == "critical"]
        high = [p for p in self.problems if p.severity == "high"]
        if critical:
            self._add_task("解决关键阻塞问题", "P0", "multiple", "多个模块", f"存在{len(critical)}个关键问题，阻塞正常流程", [f"修复: {p.problem[:50]}" for p in critical[:3]], "消除所有critical问题", "high")
        if high and len(high) >= 3:
            self._add_task("解决主要质量问题", "P1", "multiple", "多个模块", f"存在{len(high)}个高级问题，影响结果质量", [f"优化: {p.problem[:50]}" for p in high[:3]], "提升整体质量评分", "medium")

    def _build_report(self) -> Dict[str, Any]:
        by_dim = {}
        for p in self.problems:
            by_dim[p.dimension] = by_dim.get(p.dimension, 0) + 1
        return {
            "session_id": self.session_dir.name,
            "analyzed_at": datetime.now().isoformat(),
            "problems_summary": {"total": len(self.problems), "by_severity": {"critical": len([p for p in self.problems if p.severity == "critical"]), "high": len([p for p in self.problems if p.severity == "high"]), "medium": len([p for p in self.problems if p.severity == "medium"]), "low": len([p for p in self.problems if p.severity == "low"])}, "by_dimension": by_dim},
            "problems": [p.to_dict() for p in self.problems],
            "optimization_tasks": [t.to_dict() for t in self.tasks],
            "execution_recommendations": self._get_recommendations(),
        }

    def _get_recommendations(self) -> List[str]:
        recs = []
        critical_dims = set(p.dimension for p in self.problems if p.severity == "critical")
        if critical_dims:
            recs.append(f"优先检查并修复: {', '.join(critical_dims)} 模块")
        high_dims = set(p.dimension for p in self.problems if p.severity == "high")
        if high_dims:
            recs.append(f"下一步应优化: {', '.join(high_dims)} 模块")
        return recs


class SerumOrchestrationSkill:
    def __init__(self, data_file: str = "data/examples/serum/Normal_EP_serum_data.xlsx", output_dir: str = "outputs/serum_orchestrated", max_depth: Optional[int] = None, force_rounds: Optional[int] = None, report_format: str = "html", analysis_goal: Optional[str] = None, strict_llm_check: bool = False):
        self.data_file = Path(data_file)
        self.output_dir = Path(output_dir)
        self.max_depth = max_depth
        self.force_rounds = force_rounds
        self.report_format = report_format
        self.analysis_goal = analysis_goal
        self.strict_llm_check = strict_llm_check
        self.session_id: str = ""
        self.session_dir: Optional[Path] = None
        self.execution_time: float = 0
        self.analysis_result: Optional[Dict[str, Any]] = None

    def check_environment(self) -> Dict[str, Any]:
        return {"python_version": sys.version, "data_file_exists": self.data_file.exists(), "data_file_size": self.data_file.stat().st_size if self.data_file.exists() else 0, "output_dir_writable": self._check_writable(self.output_dir), "llm_service_available": self._check_llm_service()}

    def _check_writable(self, path: Path) -> bool:
        try:
            path.mkdir(parents=True, exist_ok=True)
            test_file = path / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            return True
        except Exception:
            return False

    def _check_llm_service(self) -> bool:
        try:
            result = subprocess.run(["curl", "-s", "http://localhost:48000/v1/models"], capture_output=True, timeout=5)
            return result.returncode == 0 and result.stdout
        except Exception:
            return False

    def execute(self) -> Dict[str, Any]:
        start_time = time.time()
        cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "run_serum_orchestrated_analysis.py")]
        if self.data_file != Path("data/examples/serum/Normal_EP_serum_data.xlsx"):
            cmd.extend(["--data-file", str(self.data_file)])
        if self.output_dir != Path("outputs/serum_orchestrated"):
            cmd.extend(["--output-dir", str(self.output_dir)])
        if self.max_depth is not None:
            cmd.extend(["--max-depth", str(self.max_depth)])
        if self.force_rounds is not None:
            cmd.extend(["--force-rounds", str(self.force_rounds)])
        if self.report_format != "html":
            cmd.extend(["--report-format", self.report_format])
        if self.analysis_goal:
            cmd.extend(["--analysis-goal", self.analysis_goal])
        if self.strict_llm_check:
            cmd.append("--strict-llm-check")
        cmd.append("--no-print-steps")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=str(PROJECT_ROOT))
        except subprocess.TimeoutExpired:
            self.execution_time = time.time() - start_time
            return {"status": "timeout", "execution_time": self.execution_time}
        except Exception as exc:
            self.execution_time = time.time() - start_time
            return {"status": "error", "error": str(exc), "execution_time": self.execution_time}
        self.execution_time = time.time() - start_time
        summary_file = self.output_dir / "run_summary.json"
        if summary_file.exists():
            try:
                with open(summary_file, encoding="utf-8") as f:
                    summary_data = json.load(f)
                    self.session_id = summary_data.get("session_id", "")
                    self.session_dir = Path(summary_data.get("workspace", ""))
            except Exception:
                pass
        if self.session_dir and self.session_dir.exists():
            self.analysis_result = self.analyze_deep()
        return self._build_result()

    def analyze_deep(self) -> Dict[str, Any]:
        if not self.session_dir:
            return {}
        analyzer = ArtifactDeepAnalyzer(self.session_dir)
        return analyzer.analyze()

    def save_analysis_report(self, output_path: Optional[Path] = None) -> Path:
        if output_path is None:
            output_path = self.output_dir / "deep_analysis_report.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report = {"generated_at": datetime.now().isoformat(), "session_id": self.session_id, "execution_time": self.execution_time, "analysis_result": self.analysis_result}
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return output_path

    def _build_result(self) -> Dict[str, Any]:
        return {"status": "success", "execution_time": self.execution_time, "session_id": self.session_id, "session_dir": str(self.session_dir) if self.session_dir else None, "analysis_result": self.analysis_result}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Serum Orchestrated Analysis Skill - Deep Analyzer")
    parser.add_argument("--data-file", default="data/examples/serum/Normal_EP_serum_data.xlsx")
    parser.add_argument("--output-dir", default="outputs/serum_orchestrated")
    parser.add_argument("--max-depth", type=int, default=None)
    parser.add_argument("--force-rounds", type=int, default=None)
    parser.add_argument("--analysis-goal", default=None)
    parser.add_argument("--strict-llm-check", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.check_only:
        skill = SerumOrchestrationSkill(data_file=args.data_file, output_dir=args.output_dir)
        print("=== 环境检查 ===")
        print(json.dumps(skill.check_environment(), indent=2, ensure_ascii=False))
        return
    print("=== 执行血清orchestrated分析与深度产物分析 ===")
    skill = SerumOrchestrationSkill(data_file=args.data_file, output_dir=args.output_dir, max_depth=args.max_depth, force_rounds=args.force_rounds, analysis_goal=args.analysis_goal, strict_llm_check=args.strict_llm_check)
    result = skill.execute()
    print(f"\n执行耗时: {result['execution_time']:.2f}秒")
    if result.get("session_id"):
        print(f"Session ID: {result['session_id']}")
    if result.get("analysis_result"):
        ar = result["analysis_result"]
        print(f"\n=== 问题分析结果 ===")
        ps = ar.get("problems_summary", {})
        print(f"发现问题总数: {ps.get('total', 0)}")
        print(f"  - Critical: {ps.get('by_severity', {}).get('critical', 0)}")
        print(f"  - High: {ps.get('by_severity', {}).get('high', 0)}")
        print(f"  - Medium: {ps.get('by_severity', {}).get('medium', 0)}")
        print(f"  - Low: {ps.get('by_severity', {}).get('low', 0)}")
        tasks = ar.get("optimization_tasks", [])
        if tasks:
            print(f"\n=== 可执行优化方案 ({len(tasks)}项) ===")
            for task in tasks:
                print(f"\n[{task['priority']}] {task['id']}: {task['title']}")
                print(f"  问题: {task['problem_summary']}")
                print(f"  步骤: {', '.join(task['steps'])}")
                print(f"  预期: {task['expected_improvement']}")
        recs = ar.get("execution_recommendations", [])
        if recs:
            print(f"\n=== 执行建议 ===")
            for rec in recs:
                print(f"  - {rec}")
    report_file = skill.save_analysis_report()
    print(f"\n深度分析报告已保存: {report_file}")


if __name__ == "__main__":
    main()
