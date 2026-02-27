from __future__ import annotations

import json
from pathlib import Path

from src.core.reporting.assembler import ReportAssembler


def test_split_readable_paragraph_limits_length() -> None:
    assembler = ReportAssembler(language="zh")
    text = "；".join([f"指标{i}=取值{i}" for i in range(20)])
    parts = assembler._split_readable_paragraph(text, max_len=60)
    assert len(parts) >= 2
    assert all(len(p) <= 60 for p in parts)


def test_method_steps_attach_io_hints() -> None:
    assembler = ReportAssembler(language="zh")
    rendered = assembler._render_method_steps(
        ["数据清洗", "统计检验"],
        {"统计检验": {"status": "ok", "output": "/tmp/stats_results.json"}},
    )
    content = "\n".join(rendered)
    assert "输出：stats_results.json" in content
    assert "状态：ok" in content


def test_global_process_summary_filters_hypothesis_list(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_process_filter"
    (session_dir / "plan").mkdir(parents=True, exist_ok=True)
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "report").mkdir(parents=True, exist_ok=True)
    (session_dir / "plan" / "analysis_plan.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {"id": "H1", "title": "差异", "hypothesis": "存在差异", "validation_plan_steps": [], "expected_artifacts": []}
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (session_dir / "plan" / "analysis_plan.md").write_text(
        "### 1. 假设列表\n- H1：存在差异\n\n### 2. 详细分析步骤\n1. 数据清洗\n2. 统计检验\n",
        encoding="utf-8",
    )
    (session_dir / "result" / "hypothesis_results.json").write_text(
        json.dumps({"hypotheses": [{"hypothesis": "H1", "steps": {}, "missing": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    assembler = ReportAssembler(language="zh")
    html = assembler.assemble(
        outline="",
        analysis_md="",
        document_manifest={
            "visualizations": [],
            "tables": [{"name": "hypothesis_results.json", "path": str(session_dir / "result" / "hypothesis_results.json"), "relative_path": "result/hypothesis_results.json"}],
        },
        report_payload={"title": "t", "summary": "", "sections": []},
        execution_warning="",
    )
    assert "本节仅保留全局流程摘要" in html
    assert "假设列表" not in html.split("## 分析方法与实施过程", 1)[1].split("## 假设验证与结果分析", 1)[0]
