from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


def _extract_json_candidates(raw: str) -> list[str]:
    if not raw:
        return []
    candidates: list[str] = []
    fence = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
    for match in fence.findall(raw):
        candidates.append(match.strip())
    obj_match = re.search(r"(\{[\s\S]*\})", raw)
    if obj_match:
        candidates.append(obj_match.group(1))
    arr_match = re.search(r"(\[[\s\S]*\])", raw)
    if arr_match:
        candidates.append(arr_match.group(1))
    return candidates


def parse_structured_payload(raw: str) -> Any:
    try:
        return json.loads(raw)
    except Exception:
        pass
    for candidate in _extract_json_candidates(raw):
        try:
            return json.loads(candidate)
        except Exception:
            continue
    return {}


def normalize_analysis_payload(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        payload = {}
    evidence = payload.get("evidence", [])
    if isinstance(evidence, str):
        evidence = [evidence]
    key_findings = payload.get("key_findings", [])
    if isinstance(key_findings, str):
        key_findings = [key_findings]
    limitations = payload.get("limitations", [])
    if isinstance(limitations, str):
        limitations = [limitations]
    next_steps = payload.get("next_steps", [])
    if isinstance(next_steps, str):
        next_steps = [next_steps]
    return {
        "summary": str(payload.get("summary", "")),
        "key_findings": list(key_findings or []),
        "evidence": list(evidence or []),
        "limitations": list(limitations or []),
        "next_steps": list(next_steps or []),
    }


def analysis_payload_to_markdown(payload: Dict[str, Any], execution_warning: str = "") -> str:
    lines: list[str] = []
    if execution_warning:
        lines.append(execution_warning)
        lines.append("")
    summary = payload.get("summary")
    if summary:
        lines.append("## 执行摘要")
        lines.append(summary)
        lines.append("")
    key_findings = payload.get("key_findings") or []
    if key_findings:
        lines.append("## 关键发现")
        for item in key_findings:
            lines.append(f"- {item}")
        lines.append("")
    evidence = payload.get("evidence") or []
    if evidence:
        lines.append("## 证据与依据")
        for item in evidence:
            lines.append(f"- {item}")
        lines.append("")
    limitations = payload.get("limitations") or []
    if limitations:
        lines.append("## 局限性")
        for item in limitations:
            lines.append(f"- {item}")
        lines.append("")
    next_steps = payload.get("next_steps") or []
    if next_steps:
        lines.append("## 后续建议")
        for item in next_steps:
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines).strip()


def normalize_report_payload(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        payload = {}
    sections = payload.get("sections")
    normalized_sections: List[Dict[str, str]] = []
    if isinstance(sections, list):
        for item in sections:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            body = str(item.get("body", "")).strip()
            if title or body:
                normalized_sections.append({"title": title or "Section", "body": body})
    highlights = payload.get("highlights", [])
    if isinstance(highlights, str):
        highlights = [highlights]
    limitations = payload.get("limitations", [])
    if isinstance(limitations, str):
        limitations = [limitations]
    return {
        "title": str(payload.get("title", "DeepAnalyze 报告")),
        "summary": str(payload.get("summary", "")),
        "sections": normalized_sections,
        "highlights": list(highlights or []),
        "limitations": list(limitations or []),
    }


class ReportAssembler:
    def __init__(self, language: str = "zh") -> None:
        self.language = language

    def _infer_session_root(
        self,
        visuals: list[Dict[str, Any]],
        tables: list[Dict[str, Any]],
    ) -> Path | None:
        for item in visuals:
            raw = item.get("path") or ""
            if not raw:
                continue
            p = Path(raw)
            if not p.exists():
                continue
            if "plots" in p.parts:
                return p.parent.parent
        for item in tables:
            raw = item.get("path") or ""
            if not raw:
                continue
            p = Path(raw)
            if not p.exists():
                continue
            if "result" in p.parts:
                return p.parent.parent
        return None

    def _load_json(self, path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _report_relative(self, path: str) -> str:
        if not path:
            return path
        lower = path.lower()
        if lower.startswith(("http://", "https://", "data:")):
            return path
        if path.startswith("../"):
            return path
        return f"../{path}"

    def _classify_visual(self, path: str) -> str:
        lower = path.lower()
        if "volcano" in lower:
            return "diff"
        if "top_features" in lower or "feature" in lower:
            return "diff"
        if "correlation" in lower or "heatmap" in lower:
            return "correlation"
        if "network" in lower:
            return "correlation"
        if "embedding" in lower or "scatter" in lower or "pca" in lower or "tsne" in lower:
            return "embedding"
        if "distribution" in lower or "comparison" in lower:
            return "distribution"
        return "other"

    def _visual_explanation(
        self,
        item: Dict[str, Any],
        session_root: Path | None,
        binding_map: dict[str, str],
    ) -> str:
        relative = item.get("relative_path", "") or ""
        filename = Path(relative).name.lower()
        if not session_root:
            return ""
        bound_hypothesis = binding_map.get(relative, "")

        result_dir = session_root / "result"
        if filename.startswith("volcano"):
            stats_path = result_dir / "stats_results.json"
            if not stats_path.exists():
                return ""
            df = pd.read_json(stats_path)
            group_a = df["group_a"].iloc[0] if "group_a" in df.columns else "Group A"
            group_b = df["group_b"].iloc[0] if "group_b" in df.columns else "Group B"
            sig_count = int((df["p_value"] < 0.05).sum()) if "p_value" in df.columns else 0
            top = df.sort_values("p_value").head(3)
            top_items = []
            for _, row in top.iterrows():
                feat = row.get("feature")
                diff = row.get("mean_diff")
                pval = row.get("p_value")
                if feat is not None:
                    top_items.append(f"{feat} (mean_diff={diff:.3g}, p={pval:.3g})")
            top_text = "、".join(top_items) if top_items else "无"
            return (
                "<div class=\"chart-explain\">"
                f"<p><strong>假设</strong>：{bound_hypothesis or (group_a + ' 与 ' + group_b + ' 在各峰值上存在差异')}。</p>"
                "<p><strong>验证</strong>：对每个峰值进行组间检验，绘制火山图。</p>"
                "<p><strong>坐标/颜色</strong>：X=mean_diff(组均值差)，Y=-log10(p)。"
                "红色表示 p<0.05，灰色为不显著。</p>"
                f"<p><strong>结论</strong>：显著特征数量约 {sig_count} 个；"
                f"代表性特征：{top_text}。</p>"
                "<p><strong>后续</strong>：建议对 Top 特征进行效应量复核与独立验证，"
                "并结合生物学/业务背景解释方向性。</p>"
                "</div>"
            )

        if filename.startswith("heatmap"):
            corr_path = result_dir / "correlation.json"
            if not corr_path.exists():
                return ""
            corr = pd.read_json(corr_path)
            arr = corr.to_numpy().copy()
            import numpy as np

            np.fill_diagonal(arr, 0)
            max_idx = divmod(np.abs(arr).argmax(), arr.shape[1])
            pair = (corr.index[max_idx[0]], corr.columns[max_idx[1]])
            max_corr = arr[max_idx]
            return (
                "<div class=\"chart-explain\">"
                f"<p><strong>假设</strong>：{bound_hypothesis or '峰值之间存在相关性结构'}。</p>"
                "<p><strong>验证</strong>：计算相关矩阵并绘制热力图。</p>"
                "<p><strong>坐标/颜色</strong>：X/Y 为峰值变量，颜色表示相关系数（-1~1）。</p>"
                f"<p><strong>结论</strong>：最大绝对相关约 {max_corr:.3g}，"
                f"对应 {pair[0]} 与 {pair[1]}。</p>"
                "<p><strong>后续</strong>：可对高相关变量做模块划分或共变验证。</p>"
                "</div>"
            )

        if filename.startswith("network"):
            corr_path = result_dir / "correlation.json"
            if not corr_path.exists():
                return ""
            corr = pd.read_json(corr_path)
            arr = corr.to_numpy().copy()
            import numpy as np

            np.fill_diagonal(arr, 0)
            max_idx = divmod(np.abs(arr).argmax(), arr.shape[1])
            pair = (corr.index[max_idx[0]], corr.columns[max_idx[1]])
            max_corr = arr[max_idx]
            return (
                "<div class=\"chart-explain\">"
                f"<p><strong>假设</strong>：{bound_hypothesis or '存在强相关的峰值网络结构'}。</p>"
                "<p><strong>验证</strong>：对相关矩阵阈值筛边（|corr|>0.5）构建网络。</p>"
                "<p><strong>颜色/图例</strong>：蓝线为正相关，红线为负相关，"
                "仅显示 |corr|>0.5 的边。</p>"
                f"<p><strong>结论</strong>：最强相关对为 {pair[0]} 与 {pair[1]}（|corr|≈{abs(max_corr):.3g}）。</p>"
                "<p><strong>后续</strong>：可对网络中高度连接的变量进行共同变化分析。</p>"
                "</div>"
            )

        if filename.startswith("embedding_pca") or filename.startswith("embedding_tsne"):
            method = "PCA" if "pca" in filename else "t-SNE"
            return (
                "<div class=\"chart-explain\">"
                f"<p><strong>假设</strong>：{bound_hypothesis or '样本在低维空间存在分离结构'}。</p>"
                f"<p><strong>验证</strong>：使用 {method} 将样本投影到 2D 并绘制散点图。</p>"
                "<p><strong>坐标</strong>：X/Y 为降维后的第 1/2 维坐标。</p>"
                "<p><strong>结论</strong>：用于观察聚类或离群样本趋势。</p>"
                "<p><strong>后续</strong>：建议结合聚类标签或分组上色进一步验证。</p>"
                "</div>"
            )

        if filename.startswith("scatter"):
            meta_path = (session_root / "plots" / "scatter.png.json")
            meta = self._load_json(meta_path) if meta_path.exists() else {}
            x_col = meta.get("x")
            y_col = meta.get("y")
            corr_val = meta.get("abs_correlation")
            if not x_col or not y_col:
                corr_path = result_dir / "correlation.json"
                if corr_path.exists():
                    corr = pd.read_json(corr_path)
                    arr = corr.to_numpy().copy()
                    import numpy as np

                    np.fill_diagonal(arr, 0)
                    max_idx = divmod(np.abs(arr).argmax(), arr.shape[1])
                    x_col = corr.index[max_idx[0]]
                    y_col = corr.columns[max_idx[1]]
                    corr_val = float(abs(arr[max_idx]))
            x_col = x_col or "变量1"
            y_col = y_col or "变量2"
            corr_text = f"{corr_val:.3g}" if isinstance(corr_val, (int, float)) else "未知"
            return (
                "<div class=\"chart-explain\">"
                f"<p><strong>假设</strong>：{bound_hypothesis or (x_col + ' 与 ' + y_col + ' 之间存在相关关系')}。</p>"
                "<p><strong>验证</strong>：选取绝对相关最高的两个变量绘制散点图。</p>"
                f"<p><strong>坐标</strong>：X={x_col}, Y={y_col}。</p>"
                f"<p><strong>结论</strong>：|corr|≈{corr_text}，可用于判断线性关系与异常点。</p>"
                "<p><strong>后续</strong>：建议对其他高相关变量对做补充验证。</p>"
                "</div>"
            )

        if filename.startswith("top_features"):
            top_path = result_dir / "top_features.json"
            if not top_path.exists():
                return ""
            top = self._load_json(top_path)
            names = []
            if isinstance(top, list):
                for item in top[:5]:
                    if isinstance(item, dict) and item.get("feature"):
                        names.append(item["feature"])
            names_text = "、".join(names) if names else "无"
            return (
                "<div class=\"chart-explain\">"
                f"<p><strong>假设</strong>：{bound_hypothesis or '存在显著差异的关键峰值'}。</p>"
                "<p><strong>验证</strong>：按 p/q 值排序，展示 Top 特征。</p>"
                "<p><strong>坐标</strong>：Y 为特征名，X 为排名。</p>"
                f"<p><strong>结论</strong>：Top 特征包括：{names_text}。</p>"
                "<p><strong>后续</strong>：建议对 Top 特征做效应量与外部验证。</p>"
                "</div>"
            )

        return ""

    def _build_visual_block(
        self,
        visuals: list[Dict[str, Any]],
        session_root: Path | None,
        binding_map: dict[str, str],
    ) -> str:
        lines: list[str] = []
        for item in visuals:
            name = item.get("name", "visual")
            path = self._report_relative(item.get("relative_path", ""))
            note = item.get("relative_path", "")
            if path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
                lines.append(f"<figure><img src=\"{path}\" alt=\"{name}\"/>")
                lines.append(f"<figcaption>来源: {note}</figcaption></figure>")
            elif path.lower().endswith((".html", ".htm")):
                lines.append(
                    "<figure>"
                    f"<iframe src=\"{path}\" title=\"{name}\" loading=\"lazy\" "
                    "style=\"width:100%;height:480px;border:1px solid #ddd;\"></iframe>"
                )
                lines.append(f"<figcaption>交互图表来源: {note}</figcaption></figure>")
            else:
                lines.append(f"- 图表链接: {name} ({path})")
            explanation = self._visual_explanation(item, session_root, binding_map)
            if explanation:
                lines.append(explanation)
        return "\n".join(lines)

    def _visual_names(self, visuals: list[Dict[str, Any]]) -> str:
        names: list[str] = []
        for item in visuals:
            name = item.get("name")
            if not name:
                rel = item.get("relative_path") or ""
                name = rel.split("/")[-1] if rel else "visual"
            names.append(str(name))
        return "、".join(names[:6])

    def _auto_sections(self, visuals_by_category: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, str]]:
        order = [
            ("diff", "差异与关键特征", "基于差异检验与显著性统计，重点关注变化幅度与显著特征。"),
            ("correlation", "相关性与结构", "基于相关矩阵/网络结构，观察变量间协同关系与潜在模块。"),
            ("distribution", "分布与统计概览", "展示主要变量分布、中心趋势与离散程度。"),
            ("embedding", "聚类与降维", "基于降维/聚类结果查看样本分群与潜在结构。"),
            ("other", "补充可视化", "其他产物统一汇总，便于查验。"),
        ]
        sections: list[Dict[str, str]] = []
        for key, title, default_body in order:
            visuals = visuals_by_category.get(key, [])
            if not visuals:
                continue
            names = self._visual_names(visuals)
            body = f"{default_body} 当前可用图表：{names}。"
            sections.append({"title": title, "body": body})
        return sections

    def _table_preview_blocks(self, tables: list[Dict[str, Any]], session_root: Path | None) -> list[str]:
        targets = {"top_features.json", "stats_summary.json", "model_eval.json"}
        blocks: list[str] = []
        for item in tables:
            name = item.get("name", "")
            if name not in targets:
                continue
            path = self._report_relative(item.get("relative_path", ""))
            title = name.replace("_", " ").replace(".json", "").title()
            blocks.append(f"<div class=\"table-preview\" data-src=\"{path}\" data-title=\"{title}\"></div>")
            if name == "top_features.json":
                blocks.append(
                    "<div class=\"table-explain\">"
                    "<p><strong>输入</strong>：统计检验结果。</p>"
                    "<p><strong>输出</strong>：按 p/q 值排序的 Top 特征列表。</p>"
                    "<p><strong>结论</strong>：用于定位差异最显著的峰值。</p>"
                    "</div>"
                )
            elif name == "stats_summary.json":
                blocks.append(
                    "<div class=\"table-explain\">"
                    "<p><strong>输入</strong>：组间检验结果。</p>"
                    "<p><strong>输出</strong>：均值差、效应量、p/q 值等汇总。</p>"
                    "<p><strong>结论</strong>：用于快速查看整体显著性与方向。</p>"
                    "</div>"
                )
            elif name == "model_eval.json":
                blocks.append(
                    "<div class=\"table-explain\">"
                    "<p><strong>输入</strong>：基础模型/基线方法。</p>"
                    "<p><strong>输出</strong>：majority/centroid 等基线指标。</p>"
                    "<p><strong>结论</strong>：衡量模型是否优于简单基线。</p>"
                    "</div>"
                )
        return blocks

    def _render_hypothesis_matrix(self, session_root: Path | None) -> str:
        if not session_root:
            return ""
        matrix_path = session_root / "result" / "hypothesis_matrix.json"
        if not matrix_path.exists():
            return ""
        payload = self._load_json(matrix_path)
        rows = payload.get("hypotheses", []) if isinstance(payload, dict) else []
        if not rows:
            return ""
        lines = ["## 假设闭环矩阵", "<table border=1 cellpadding=4 cellspacing=0>"]
        lines.append("<thead><tr><th>假设</th><th>状态</th><th>缺失产物</th><th>原因</th></tr></thead><tbody>")
        for row in rows:
            missing = ", ".join(row.get("missing_artifacts", []) or [])
            reason = row.get("reason", "")
            lines.append(
                f"<tr><td>{row.get('hypothesis','')}</td>"
                f"<td>{row.get('status','')}</td>"
                f"<td>{missing}</td>"
                f"<td>{reason}</td></tr>"
            )
        lines.append("</tbody></table>")
        return "\n".join(lines)

    def _render_coverage_report(self, session_root: Path | None) -> str:
        if not session_root:
            return ""
        path = session_root / "result" / "coverage_report.json"
        if not path.exists():
            return ""
        payload = self._load_json(path)
        missing = payload.get("missing_features", []) or []
        mode = payload.get("mode", "")
        filter_info = payload.get("filter_info", {}) or {}
        lines = ["## 覆盖策略与遗漏项"]
        lines.append(f"- 覆盖模式: {mode}")
        if filter_info:
            method = filter_info.get("method")
            top_k = filter_info.get("top_k")
            if method:
                lines.append(f"- 筛选方法: {method}")
            if top_k:
                lines.append(f"- Top K: {top_k}")
        if missing:
            lines.append(f"- 未覆盖特征数量: {len(missing)}")
            lines.append(f"- 未覆盖示例: {', '.join(missing[:10])}")
        else:
            lines.append("- 已覆盖全部数值特征")
        return "\n".join(lines)

    def _render_quality_warnings(self, session_root: Path | None) -> str:
        if not session_root:
            return ""
        audit_path = session_root / "meta" / "run_audit.json"
        if not audit_path.exists():
            return ""
        audit = self._load_json(audit_path)
        missing_required = audit.get("missing_required", []) or []
        gate_missing = audit.get("quality_gate_missing", []) or []
        if not missing_required and not gate_missing:
            return ""
        lines = ["## 质量门槛未达标"]
        if missing_required:
            lines.append(f"- 缺失核心产物: {', '.join(missing_required)}")
        if gate_missing:
            lines.append(f"- 缺失质量门槛: {', '.join(gate_missing)}")
        return "\n".join(lines)

    def _render_validation_failures(self, session_root: Path | None) -> str:
        if not session_root:
            return ""
        failure_path = session_root / "result" / "validation_failures.json"
        if not failure_path.exists():
            return ""
        payload = self._load_json(failure_path)
        if not payload:
            return ""
        stage = payload.get("stage", "validation")
        error = payload.get("error", "unknown")
        return (
            "## 验证失败记录\n"
            f"- 阶段: {stage}\n"
            f"- 错误: {error}"
        )

    def assemble(
        self,
        outline: str,
        analysis_md: str,
        document_manifest: Dict[str, Any],
        report_payload: Dict[str, Any],
        execution_warning: str = "",
    ) -> str:
        outline = outline.strip()
        analysis_md = analysis_md.strip()
        outline_block = ""
        if outline:
            outline_block = "\n".join([f"> {line}" if line.strip() else ">" for line in outline.splitlines()])
        visuals = document_manifest.get("visualizations", []) or []
        tables = document_manifest.get("tables", []) or []
        session_root = self._infer_session_root(visuals, tables)
        binding_map: dict[str, str] = {}
        if session_root:
            binding_path = session_root / "result" / "visual_binding.json"
            if binding_path.exists():
                binding_payload = self._load_json(binding_path)
                for item in binding_payload.get("bindings", []) if isinstance(binding_payload, dict) else []:
                    artifact = item.get("artifact")
                    hypothesis = item.get("hypothesis")
                    if artifact and hypothesis:
                        binding_map[artifact] = hypothesis
        artifact_names = " ".join(
            [str(item.get("name", "")).lower() for item in visuals + tables]
        )
        has_advanced = any(
            key in artifact_names
            for key in ("roc", "auc", "volcano", "pca", "tsne", "umap", "model", "lasso")
        )
        lines: list[str] = []
        title = report_payload.get("title") or "DeepAnalyze 报告"
        lines.append(f"# {title}")
        lines.append("")
        if execution_warning:
            lines.append(execution_warning)
            lines.append("")
        summary = report_payload.get("summary")
        if not has_advanced:
            summary = "当前仅完成描述性统计与相关性分析，推断性统计与建模尚未执行。"
        if not summary:
            summary = "报告基于当前已生成产物自动装配，未启用 LLM 生成段落。"
        if summary:
            lines.append("## 摘要")
            lines.append(summary)
            lines.append("")
        if outline_block:
            lines.append("## 报告大纲")
            lines.append(outline_block)
            lines.append("")
        if analysis_md:
            lines.append("## 分析结果")
            lines.append(analysis_md)
            lines.append("")
        failure_block = self._render_validation_failures(session_root)
        if failure_block:
            lines.append(failure_block)
            lines.append("")
        quality_block = self._render_quality_warnings(session_root)
        if quality_block:
            lines.append(quality_block)
            lines.append("")
        matrix_block = self._render_hypothesis_matrix(session_root)
        if matrix_block:
            lines.append(matrix_block)
            lines.append("")
        coverage_block = self._render_coverage_report(session_root)
        if coverage_block:
            lines.append(coverage_block)
            lines.append("")
        if document_manifest:
            lines.append("## 自动校验摘要")
            lines.append(f"- 可视化产物数量: {len(visuals)}")
            lines.append(f"- 表格/结果文件数量: {len(tables)}")
            if visuals:
                lines.append("- 可视化状态: 已生成")
            else:
                lines.append("- 可视化状态: 未生成")
            lines.append("")
        sections = report_payload.get("sections") or []
        visuals_by_category: Dict[str, List[Dict[str, Any]]] = {}
        for item in visuals:
            category = self._classify_visual(item.get("relative_path", ""))
            visuals_by_category.setdefault(category, []).append(item)
        if not sections:
            sections = self._auto_sections(visuals_by_category)
        used_visuals: set[str] = set()
        for section in sections:
            title = section.get("title", "Section")
            body = section.get("body", "")
            lowered = f"{title} {body}".lower()
            if not has_advanced:
                if any(
                    key in lowered
                    for key in ("roc", "auc", "volcano", "pca", "tsne", "umap", "lasso", "random forest")
                    ):
                    continue
            lines.append(f"## {title}")
            lines.append(body)
            if "差异" in title or "Differential" in title:
                block = self._build_visual_block(visuals_by_category.get("diff", []), session_root, binding_map)
                if block:
                    lines.append(block)
                    used_visuals.update(
                        v.get("relative_path", "") for v in visuals_by_category.get("diff", [])
                    )
            elif "相关" in title or "Correlation" in title:
                block = self._build_visual_block(visuals_by_category.get("correlation", []), session_root, binding_map)
                if block:
                    lines.append(block)
                    used_visuals.update(
                        v.get("relative_path", "") for v in visuals_by_category.get("correlation", [])
                    )
            elif "分布" in title or "描述" in title or "统计" in title or "Distribution" in title:
                block = self._build_visual_block(visuals_by_category.get("distribution", []), session_root, binding_map)
                if block:
                    lines.append(block)
                    used_visuals.update(
                        v.get("relative_path", "") for v in visuals_by_category.get("distribution", [])
                    )
            elif "聚类" in title or "降维" in title or "Embedding" in title:
                block = self._build_visual_block(visuals_by_category.get("embedding", []), session_root, binding_map)
                if block:
                    lines.append(block)
                    used_visuals.update(
                        v.get("relative_path", "") for v in visuals_by_category.get("embedding", [])
                    )
            elif "可视化" in title or "Visual" in title:
                block = self._build_visual_block(visuals, session_root, binding_map)
                if block:
                    lines.append(block)
                    used_visuals.update(v.get("relative_path", "") for v in visuals)
            lines.append("")
        highlights = report_payload.get("highlights") or []
        if not has_advanced:
            highlights = []
        if highlights:
            lines.append("## 关键结论")
            for item in highlights:
                lines.append(f"- {item}")
            lines.append("")
        limitations = report_payload.get("limitations") or []
        if not has_advanced:
            limitations = []
        if limitations:
            lines.append("## 局限性")
            for item in limitations:
                lines.append(f"- {item}")
            lines.append("")
        if document_manifest:
            if visuals or tables:
                lines.append("## 产物清单")
                for item in visuals:
                    name = item.get("name", "visual")
                    path = self._report_relative(item.get("relative_path", ""))
                    lines.append(f"- 图表: {name} ({path})")
                for item in tables:
                    name = item.get("name", "table")
                    path = self._report_relative(item.get("relative_path", ""))
                    lines.append(f"- 表格: {name} ({path})")
                lines.append("")
        if document_manifest and visuals:
            remaining = [
                v
                for v in visuals
                if v.get("relative_path", "") not in used_visuals
            ]
            if remaining:
                lines.append("## 图表预览")
                lines.append(self._build_visual_block(remaining, session_root, binding_map))
                lines.append("")
        if document_manifest and tables:
            table_blocks = self._table_preview_blocks(tables, session_root)
            if table_blocks:
                lines.append("## 表格预览")
                lines.extend(table_blocks)
                lines.append(
                    "<script>\n"
                    "async function renderTable(block){\n"
                    "  const src = block.dataset.src;\n"
                    "  const title = block.dataset.title || src;\n"
                    "  const res = await fetch(src);\n"
                    "  const text = await res.text();\n"
                    "  let rows = [];\n"
                    "  if (src.endsWith('.json')) {\n"
                    "    const data = JSON.parse(text);\n"
                    "    rows = Array.isArray(data) ? data : (data.rows || []);\n"
                    "  } else {\n"
                    "    rows = text.trim().split('\\n').map(line => line.split(','));\n"
                    "    rows = rows.slice(1).map(cols => Object.fromEntries(cols.map((c,i)=>[i,c])));\n"
                    "  }\n"
                    "  if (!rows.length){ block.innerHTML = `<h4>${title}</h4><div>无可展示数据</div>`; return; }\n"
                    "  const cols = Object.keys(rows[0]);\n"
                    "  let html = `<h4>${title}</h4><table border=1 cellpadding=4 cellspacing=0><thead><tr>`;\n"
                    "  html += cols.map(c=>`<th>${c}</th>`).join('');\n"
                    "  html += '</tr></thead><tbody>';\n"
                    "  rows.slice(0,20).forEach(r=>{ html+='<tr>'+cols.map(c=>`<td>${r[c]}</td>`).join('')+'</tr>'; });\n"
                    "  html += '</tbody></table>';\n"
                    "  block.innerHTML = html;\n"
                    "}\n"
                    "document.querySelectorAll('.table-preview').forEach(renderTable);\n"
                    "</script>"
                )
                lines.append("")
        return "\n".join(lines).strip()
