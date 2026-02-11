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
        if not has_advanced:
            sections = []
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
            lines.append("## 图表预览")
            for item in visuals:
                path = self._report_relative(item.get("relative_path", ""))
                name = item.get("name", "visual")
                if path.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                    lines.append(f"![{name}]({path})")
                else:
                    lines.append(f"- 图表链接: {name} ({path})")
            lines.append("")
        return "\n".join(lines).strip()
