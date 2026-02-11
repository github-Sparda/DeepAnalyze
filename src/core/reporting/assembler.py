from __future__ import annotations

import json
import re
from typing import Any, Dict, List


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

    def _build_visual_block(self, visuals: list[Dict[str, Any]]) -> str:
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

    def _table_preview_blocks(self, tables: list[Dict[str, Any]]) -> list[str]:
        targets = {"top_features.json", "stats_summary.json", "model_eval.json"}
        blocks: list[str] = []
        for item in tables:
            name = item.get("name", "")
            if name not in targets:
                continue
            path = self._report_relative(item.get("relative_path", ""))
            title = name.replace("_", " ").replace(".json", "").title()
            blocks.append(f"<div class=\"table-preview\" data-src=\"{path}\" data-title=\"{title}\"></div>")
        return blocks

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
                block = self._build_visual_block(visuals_by_category.get("diff", []))
                if block:
                    lines.append(block)
                    used_visuals.update(
                        v.get("relative_path", "") for v in visuals_by_category.get("diff", [])
                    )
            elif "相关" in title or "Correlation" in title:
                block = self._build_visual_block(visuals_by_category.get("correlation", []))
                if block:
                    lines.append(block)
                    used_visuals.update(
                        v.get("relative_path", "") for v in visuals_by_category.get("correlation", [])
                    )
            elif "分布" in title or "描述" in title or "统计" in title or "Distribution" in title:
                block = self._build_visual_block(visuals_by_category.get("distribution", []))
                if block:
                    lines.append(block)
                    used_visuals.update(
                        v.get("relative_path", "") for v in visuals_by_category.get("distribution", [])
                    )
            elif "聚类" in title or "降维" in title or "Embedding" in title:
                block = self._build_visual_block(visuals_by_category.get("embedding", []))
                if block:
                    lines.append(block)
                    used_visuals.update(
                        v.get("relative_path", "") for v in visuals_by_category.get("embedding", [])
                    )
            elif "可视化" in title or "Visual" in title:
                block = self._build_visual_block(visuals)
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
                lines.append(self._build_visual_block(remaining))
                lines.append("")
        if document_manifest and tables:
            table_blocks = self._table_preview_blocks(tables)
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
