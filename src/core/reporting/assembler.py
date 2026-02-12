from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

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
        "key_findings": [str(x) for x in (key_findings or [])],
        "evidence": [str(x) for x in (evidence or [])],
        "limitations": [str(x) for x in (limitations or [])],
        "next_steps": [str(x) for x in (next_steps or [])],
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
        "outline_mode": str(payload.get("outline_mode", "structure_only")),
    }


class ReportAssembler:
    def __init__(self, language: str = "zh") -> None:
        self.language = language

    def _infer_session_root(
        self,
        visuals: list[Dict[str, Any]],
        tables: list[Dict[str, Any]],
        document_manifest: Dict[str, Any] | None = None,
    ) -> Path | None:
        def _candidate_root(path: Path) -> Path | None:
            if not path.exists():
                return None
            for parent in [path] + list(path.parents):
                # Session root should at least contain result + report directories.
                if (parent / "result").exists() and (parent / "report").exists():
                    return parent
            return None

        for item in visuals:
            raw = item.get("path") or ""
            if not raw:
                continue
            p = Path(raw)
            root = _candidate_root(p)
            if root:
                return root
        for item in tables:
            raw = item.get("path") or ""
            if not raw:
                continue
            p = Path(raw)
            root = _candidate_root(p)
            if root:
                return root
        plans = (document_manifest or {}).get("plans", []) if isinstance(document_manifest, dict) else []
        for plan in plans:
            for entry in plan.get("entries", []):
                raw = entry.get("path") or ""
                if not raw:
                    continue
                root = _candidate_root(Path(raw))
                if root:
                    return root
        return None

    def _load_json(self, path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _preview_script(self) -> str:
        return (
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
            "async function renderAttachment(block){\n"
            "  const src = block.dataset.src;\n"
            "  try {\n"
            "    const res = await fetch(src);\n"
            "    const text = await res.text();\n"
            "    block.textContent = text.slice(0, 4000);\n"
            "  } catch (e) {\n"
            "    block.textContent = '预览失败: ' + e;\n"
            "  }\n"
            "}\n"
            "document.querySelectorAll('.table-preview').forEach(renderTable);\n"
            "document.querySelectorAll('.attachment-preview').forEach(renderAttachment);\n"
            "const hypFilter = document.getElementById('appendix-hypothesis-filter');\n"
            "if (hypFilter) {\n"
            "  hypFilter.addEventListener('change', (ev) => {\n"
            "    const selected = ev.target.value;\n"
            "    document.querySelectorAll('.appendix-item').forEach((el) => {\n"
            "      const hyp = el.dataset.hypothesis || 'ALL';\n"
            "      el.style.display = (selected === 'ALL' || hyp === selected) ? '' : 'none';\n"
            "    });\n"
            "  });\n"
            "}\n"
            "</script>"
        )

    def _report_relative(self, path: str) -> str:
        if not path:
            return path
        lower = path.lower()
        if lower.startswith(("http://", "https://", "data:")):
            return path
        if path.startswith("../"):
            return path
        return f"../{path}"

    def _resource_health(self, session_root: Path | None, relative_path: str) -> tuple[bool, str]:
        if not relative_path:
            return False, "empty_path"
        lower = relative_path.lower()
        if lower.startswith(("http://", "https://", "data:")):
            return True, "ok_remote"
        if "://" in relative_path:
            return False, "illegal_scheme"
        if relative_path.startswith("/"):
            return False, "absolute_path_forbidden"
        if ".." in Path(relative_path).parts:
            return False, "path_traversal_forbidden"
        if not session_root:
            return True, "unknown_without_session_root"
        target = session_root / relative_path
        if target.exists():
            return True, "ok"
        return False, "missing_file"

    def _classify_visual(self, item: Dict[str, Any]) -> str:
        metadata = item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {}
        visual_type = str(metadata.get("type", "")).lower()
        if visual_type in {"correlation", "correlation_heatmap", "heatmap"}:
            return "correlation"
        if visual_type in {"correlation_network", "network"}:
            return "correlation"
        if visual_type in {"embedding", "scatter", "pca", "tsne", "umap"}:
            return "embedding"
        if visual_type in {"distribution", "comparison"}:
            return "distribution"
        if visual_type in {"volcano", "manhattan", "diff"}:
            return "diff"
        path = str(item.get("relative_path", ""))
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

    def _visual_priority(self, relative_path: str) -> int:
        lower = relative_path.lower()
        if lower.endswith((".html", ".htm")):
            return 0
        if lower.endswith((".png", ".jpg", ".jpeg", ".svg", ".gif")):
            return 1
        return 2

    def _visual_group_key(self, relative_path: str) -> str:
        stem = Path(relative_path).stem.lower()
        for suffix in ("_interactive", "_plotly", "_echarts", "_html"):
            if stem.endswith(suffix):
                return stem[: -len(suffix)]
        return stem

    def _prioritize_visuals(self, visuals: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        grouped: dict[str, list[Dict[str, Any]]] = {}
        for item in visuals:
            rel = str(item.get("relative_path", ""))
            if not rel:
                continue
            key = self._visual_group_key(rel)
            grouped.setdefault(key, []).append(item)
        selected: list[Dict[str, Any]] = []
        for _, candidates in grouped.items():
            candidates_sorted = sorted(
                candidates,
                key=lambda x: (
                    self._visual_priority(str(x.get("relative_path", ""))),
                    str(x.get("relative_path", "")),
                ),
            )
            selected.append(candidates_sorted[0])
        selected.sort(key=lambda x: str(x.get("relative_path", "")))
        return selected

    def _extract_outline_hypothesis_ids(self, outline: str) -> set[str]:
        ids: set[str] = set()
        for line in outline.splitlines():
            text = line.strip().upper()
            m = re.findall(r"\bH\d+\b", text)
            for item in m:
                ids.add(item)
        return ids

    def _outline_conflict_note(self, outline: str, plan_json: Dict[str, Any]) -> str:
        if not outline:
            return ""
        outline_ids = self._extract_outline_hypothesis_ids(outline)
        plan_ids = {
            str(h.get("id", "")).strip().upper()
            for h in plan_json.get("hypotheses", [])
            if isinstance(h, dict) and str(h.get("id", "")).strip()
        }
        if not outline_ids or not plan_ids:
            return ""
        if outline_ids == plan_ids:
            return ""
        missing_in_outline = sorted(plan_ids - outline_ids)
        extra_in_outline = sorted(outline_ids - plan_ids)
        notes: list[str] = []
        if missing_in_outline:
            notes.append(f"大纲缺失假设: {', '.join(missing_in_outline)}")
        if extra_in_outline:
            notes.append(f"大纲包含未执行假设: {', '.join(extra_in_outline)}")
        return "；".join(notes)

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
            pos_count = 0
            neg_count = 0
            if "mean_diff" in df.columns:
                pos_count = int(((df["p_value"] < 0.05) & (df["mean_diff"] > 0)).sum()) if "p_value" in df.columns else int((df["mean_diff"] > 0).sum())
                neg_count = int(((df["p_value"] < 0.05) & (df["mean_diff"] < 0)).sum()) if "p_value" in df.columns else int((df["mean_diff"] < 0).sum())
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
                f"<p><strong>结论</strong>：显著特征数量约 {sig_count} 个（上调 {pos_count}，下调 {neg_count}）；"
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
            edge_count = int((np.abs(arr) > 0.5).sum() / 2)
            return (
                "<div class=\"chart-explain\">"
                f"<p><strong>假设</strong>：{bound_hypothesis or '存在强相关的峰值网络结构'}。</p>"
                "<p><strong>验证</strong>：对相关矩阵阈值筛边（|corr|>0.5）构建网络。</p>"
                "<p><strong>颜色/图例</strong>：蓝线为正相关，红线为负相关，"
                "仅显示 |corr|>0.5 的边。</p>"
                f"<p><strong>结论</strong>：最强相关对为 {pair[0]} 与 {pair[1]}（|corr|≈{abs(max_corr):.3g}），"
                f"网络边数约 {edge_count} 条。</p>"
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
                "<p><strong>坐标</strong>：Y 为特征名；X 轴取决于绘图实现（通常为显著性或效应相关指标）。"
                "请结合 top_features.json 中的 p/q 值核对。</p>"
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
        render_manifest: list[dict[str, Any]] | None = None,
    ) -> str:
        lines: list[str] = []
        for item in visuals:
            name = item.get("name", "visual")
            note = item.get("relative_path", "")
            path = self._report_relative(note)
            ok, reason = self._resource_health(session_root, note)
            if render_manifest is not None:
                render_manifest.append(
                    {
                        "resource": note,
                        "kind": "visualization",
                        "ok": ok,
                        "reason": reason,
                    }
                )
            if not ok:
                lines.append(
                    f"<div class=\"render-warning\">图表资源不可渲染：{name}（{note}，原因：{reason}）</div>"
                )
                continue
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

    def _extract_plan_sections(self, session_root: Path | None) -> Tuple[str, str]:
        if not session_root:
            return "", ""
        candidates = [
            session_root / "plan" / "analysis_plan.md",
        ]
        artifact_root = session_root / "artifacts"
        if artifact_root.exists():
            for candidate in artifact_root.glob("*/plan/analysis_plan.md"):
                candidates.append(candidate)
        plan_text = ""
        for path in candidates:
            if path.exists():
                try:
                    plan_text = path.read_text(encoding="utf-8")
                    break
                except Exception:
                    continue
        if not plan_text:
            return "", ""
        hypotheses = ""
        process = ""
        if "### 1. 假设列表" in plan_text:
            part = plan_text.split("### 1. 假设列表", 1)[1]
            stop_idx = part.find("### 2.")
            hypotheses = part[:stop_idx].strip() if stop_idx >= 0 else part.strip()
            hypotheses = f"### 假设列表\n\n{hypotheses}".strip()
        if "### 2. 详细分析步骤" in plan_text:
            part = plan_text.split("### 2. 详细分析步骤", 1)[1]
            stop_idx = part.find("### 3.")
            process = part[:stop_idx].strip() if stop_idx >= 0 else part.strip()
            process = f"### 详细分析步骤\n\n{process}".strip()
        if not hypotheses:
            hypotheses = plan_text.strip()
        if not process:
            process = plan_text.strip()
        return hypotheses, process

    def _render_appendix(
        self,
        document_manifest: Dict[str, Any],
        used_visuals: set[str],
        used_tables: set[str],
        binding_map: dict[str, str] | None = None,
    ) -> str:
        lines: list[str] = ["## 附件（正文未展示）", "<details><summary>点击展开附件预览</summary>"]
        visuals = self._prioritize_visuals(document_manifest.get("visualizations", []) or [])
        tables = document_manifest.get("tables", []) or []
        remaining_visuals = [v for v in visuals if v.get("relative_path", "") not in used_visuals]
        remaining_tables = [t for t in tables if t.get("relative_path", "") not in used_tables]
        binding_map = binding_map or {}
        hypothesis_values = sorted({v for v in binding_map.values() if v})
        if hypothesis_values:
            lines.append(
                "<label>按假设过滤附件：</label>"
                "<select id=\"appendix-hypothesis-filter\">"
                "<option value=\"ALL\">全部</option>"
                + "".join([f"<option value=\"{h}\">{h}</option>" for h in hypothesis_values])
                + "</select>"
            )
        plans = document_manifest.get("plans", []) or []
        extra_groups: dict[str, list[str]] = {
            "Plan": [],
            "Code": [],
            "Result": [],
            "Meta": [],
        }
        for plan in plans:
            for entry in plan.get("entries", []):
                kind = str(entry.get("kind", "")).lower()
                rel = entry.get("relative_path", "")
                if not rel:
                    continue
                if kind == "visualization" and rel in used_visuals:
                    continue
                if kind in {"plan", "visualization_plan"}:
                    extra_groups["Plan"].append(rel)
                elif kind == "code":
                    extra_groups["Code"].append(rel)
                elif kind == "result":
                    extra_groups["Result"].append(rel)
                elif kind in {"meta", "audit"}:
                    extra_groups["Meta"].append(rel)
        if remaining_visuals:
            lines.append("- Visualization (remaining):")
            for item in remaining_visuals:
                rel = item.get("relative_path", "")
                hyp = binding_map.get(rel, "ALL")
                lines.append(f"  - <div class=\"appendix-item\" data-hypothesis=\"{hyp}\">{self._report_relative(rel)} (fallback path: {rel})</div>")
                lower = rel.lower()
                if lower.endswith((".html", ".htm")):
                    lines.append(
                        f"    <iframe src=\"{self._report_relative(rel)}\" loading=\"lazy\" "
                        "style=\"width:100%;height:360px;border:1px solid #ddd;\"></iframe>"
                    )
                elif lower.endswith((".png", ".jpg", ".jpeg", ".svg", ".gif")):
                    lines.append(f"    <img src=\"{self._report_relative(rel)}\" style=\"max-width:100%;border:1px solid #ddd;\"/>")
        if remaining_tables:
            lines.append("- Tables (remaining):")
            for item in remaining_tables:
                rel = item.get("relative_path", "")
                lines.append(f"  - <div class=\"appendix-item\" data-hypothesis=\"ALL\">{self._report_relative(rel)} (fallback path: {rel})</div>")
                lines.append(f"    <div class=\"table-preview\" data-src=\"{self._report_relative(rel)}\" data-title=\"{item.get('name','table')}\"></div>")
        for group, paths in extra_groups.items():
            uniq = sorted(set(paths))
            if not uniq:
                continue
            lines.append(f"- {group}:")
            for rel in uniq:
                lines.append(f"  - <div class=\"appendix-item\" data-hypothesis=\"ALL\">{self._report_relative(rel)} (fallback path: {rel})</div>")
                lower = rel.lower()
                if lower.endswith((".txt", ".md", ".log")):
                    lines.append(f"    <pre class=\"attachment-preview\" data-src=\"{self._report_relative(rel)}\"></pre>")
                elif lower.endswith(".json"):
                    lines.append(f"    <pre class=\"attachment-preview\" data-src=\"{self._report_relative(rel)}\"></pre>")
                elif lower.endswith(".csv"):
                    lines.append(f"    <div class=\"table-preview\" data-src=\"{self._report_relative(rel)}\" data-title=\"{Path(rel).name}\"></div>")
                elif lower.endswith(".pdf"):
                    lines.append(
                        f"    <object data=\"{self._report_relative(rel)}\" type=\"application/pdf\" "
                        "style=\"width:100%;height:420px;border:1px solid #ddd;\">"
                        f"<a href=\"{self._report_relative(rel)}\" target=\"_blank\">PDF 预览失败，点击打开原文件</a>"
                        "</object>"
                    )
        if len(lines) == 2:
            lines.append("- 无剩余附件。")
        lines.append("</details>")
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

    def _load_plan_json(self, session_root: Path | None) -> dict[str, Any]:
        if not session_root:
            return {}
        candidates = [
            session_root / "plan" / "analysis_plan.json",
        ]
        artifact_root = session_root / "artifacts"
        if artifact_root.exists():
            candidates.extend(sorted(artifact_root.glob("*/plan/analysis_plan.json")))
        for path in candidates:
            if path.exists():
                payload = self._load_json(path)
                if isinstance(payload, dict) and payload.get("hypotheses"):
                    return payload
        return {}

    def _load_hypothesis_results(self, session_root: Path | None) -> dict[str, Any]:
        if not session_root:
            return {}
        path = session_root / "result" / "hypothesis_results.json"
        if not path.exists():
            return {}
        payload = self._load_json(path)
        return payload if isinstance(payload, dict) else {}

    def _load_hypothesis_evidence(self, session_root: Path | None) -> dict[str, Any]:
        if not session_root:
            return {}
        path = session_root / "result" / "hypothesis_evidence.json"
        if not path.exists():
            return {}
        payload = self._load_json(path)
        return payload if isinstance(payload, dict) else {}

    def _load_hypothesis_contrast(self, session_root: Path | None) -> dict[str, Any]:
        if not session_root:
            return {}
        path = session_root / "result" / "hypothesis_contrast.json"
        if not path.exists():
            return {}
        payload = self._load_json(path)
        return payload if isinstance(payload, dict) else {}

    def _hypothesis_result_entry(self, hyp_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        for item in payload.get("hypotheses", []) if isinstance(payload, dict) else []:
            name = str(item.get("hypothesis", ""))
            if name.upper().startswith(hyp_id):
                return item
        return {}

    def _hypothesis_evidence_entry(self, hyp_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        for item in payload.get("hypotheses", []) if isinstance(payload, dict) else []:
            if str(item.get("hypothesis_id", "")).upper() == hyp_id.upper():
                return item
        return {}

    def _hypothesis_contrast_entry(self, hyp_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        for item in payload.get("hypotheses", []) if isinstance(payload, dict) else []:
            if str(item.get("hypothesis_id", "")).upper() == hyp_id.upper():
                return item
        return {}

    def _extract_evidence_snippet(self, session_root: Path | None, rel_path: str, max_lines: int = 6) -> str:
        if not session_root or not rel_path:
            return ""
        path = session_root / rel_path
        if not path.exists():
            return ""
        suffix = path.suffix.lower()
        try:
            if suffix in {".txt", ".md"}:
                text = path.read_text(encoding="utf-8", errors="ignore")
                lines = [ln for ln in text.splitlines() if ln.strip()][:max_lines]
                return "\n".join(lines)
            if suffix in {".json"}:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return json.dumps(payload, ensure_ascii=False, indent=2)[:1200]
                if isinstance(payload, list):
                    return json.dumps(payload[:3], ensure_ascii=False, indent=2)
            if suffix in {".csv"}:
                df = pd.read_csv(path)
                return df.head(5).to_markdown(index=False)
        except Exception:
            return ""
        return ""

    def _hypothesis_data_analysis(self, hyp_id: str, session_root: Path | None) -> list[str]:
        if not session_root:
            return []
        lines: list[str] = []
        if hyp_id == "H1":
            stats_path = session_root / "result" / "stats_results.json"
            top_path = session_root / "result" / "top_features.json"
            if stats_path.exists():
                try:
                    df = pd.read_json(stats_path)
                    total = len(df)
                    sig = int((df["p_value"] < 0.05).sum()) if "p_value" in df.columns else 0
                    lines.append(f"统计检验覆盖 {total} 个特征，其中 p<0.05 为 {sig} 个。")
                except Exception:
                    pass
            if top_path.exists():
                try:
                    top = pd.read_json(top_path).head(5)
                    names = [str(x) for x in top["feature"].tolist()] if "feature" in top.columns else []
                    if names:
                        lines.append(f"Top 特征（前5）: {'、'.join(names)}。")
                except Exception:
                    pass
        elif hyp_id == "H2":
            eval_path = session_root / "result" / "model_eval.json"
            cv_path = session_root / "result" / "cv_results.json"
            if eval_path.exists():
                model_eval = self._load_json(eval_path)
                metrics = model_eval.get("metrics", {}) if isinstance(model_eval, dict) else {}
                majority = metrics.get("majority_accuracy")
                centroid = metrics.get("centroid_accuracy")
                if majority is not None or centroid is not None:
                    lines.append(
                        f"模型评估：majority_accuracy={majority}, centroid_accuracy={centroid}。"
                    )
            if cv_path.exists():
                cv = self._load_json(cv_path)
                folds = cv.get("folds") if isinstance(cv, dict) else None
                if isinstance(folds, list):
                    lines.append(f"已执行交叉验证，折数={len(folds)}。")
        elif hyp_id == "H3":
            corr_path = session_root / "result" / "correlation.json"
            if corr_path.exists():
                try:
                    corr = pd.read_json(corr_path)
                    import numpy as np

                    arr = corr.to_numpy().copy()
                    np.fill_diagonal(arr, 0)
                    max_idx = divmod(np.abs(arr).argmax(), arr.shape[1])
                    pair = (corr.index[max_idx[0]], corr.columns[max_idx[1]])
                    lines.append(
                        f"最强相关变量对：{pair[0]} 与 {pair[1]}（|corr|≈{abs(arr[max_idx]):.3g}）。"
                    )
                except Exception:
                    pass
        elif hyp_id == "H4":
            cluster_path = session_root / "result" / "clustering.json"
            dim_path = session_root / "result" / "dimensionality.json"
            if dim_path.exists():
                lines.append("已生成降维结果（PCA/t-SNE）用于观察样本分离。")
            if cluster_path.exists():
                cluster = self._load_json(cluster_path)
                if isinstance(cluster, dict):
                    labels = cluster.get("labels")
                    if isinstance(labels, list):
                        lines.append(f"聚类标签已生成，样本标签数={len(labels)}。")
        return lines

    def _hypothesis_bound_visuals(
        self,
        hyp_id: str,
        visuals: list[Dict[str, Any]],
        binding_map: dict[str, str],
    ) -> list[Dict[str, Any]]:
        selected: list[Dict[str, Any]] = []
        for item in visuals:
            rel = item.get("relative_path", "")
            bound = binding_map.get(rel, "")
            if bound.upper().startswith(hyp_id):
                selected.append(item)
        return self._prioritize_visuals(selected)

    def _render_result_analysis_paragraph(
        self,
        hyp_id: str,
        hyp_text: str,
        details: list[str],
        missing: list[str],
        quant_metrics: dict[str, Any] | None = None,
        conclusion_status: str = "inconclusive",
    ) -> str:
        premise = hyp_text.strip() or f"{hyp_id} 假设"
        quant_metrics = quant_metrics or {}
        quant_parts = []
        for key, value in quant_metrics.items():
            quant_parts.append(f"{key}={value}")
        quant_text = f"定量指标包括：{'; '.join(quant_parts)}。" if quant_parts else ""
        if details:
            body = "；".join(details)
            if conclusion_status in {"inconclusive", "failed"}:
                return (
                    f"围绕“{premise}”的验证已收集到以下观察：{body}。{quant_text}"
                    "但多路径证据尚未形成一致支持，当前结论应标记为待定，"
                    "仅可作为后续实验和补充分析的参考线索。"
                )
            if missing:
                return (
                    f"围绕“{premise}”的验证已产生核心证据：{body}。{quant_text}"
                    f"但仍存在未完成产物（{', '.join(missing)}），因此当前结论应视为阶段性结论。"
                )
            return (
                f"围绕“{premise}”的验证结果显示：{body}。{quant_text}"
                "从现有证据看，该假设获得了可解释的经验支持，但仍建议在独立数据或替代方法下复核稳健性。"
            )
        if missing:
            return (
                f"针对“{premise}”的分析尚未形成足够证据，关键缺失产物为 {', '.join(missing)}。"
                "当前无法给出可靠判断，建议优先补齐执行链路后再评估。"
            )
        return (
            f"针对“{premise}”未提取到可自动解释的定量结果，"
            "请结合 result 目录中的原始产物进行人工复核。"
        )

    def _render_cross_hypothesis_discussion(self, outcomes: list[dict[str, Any]]) -> str:
        if not outcomes:
            return "当前运行未形成可汇总的假设级结果。"
        total = len(outcomes)
        complete = sum(1 for x in outcomes if not x.get("missing"))
        partial = total - complete
        lines: list[str] = []
        lines.append(
            f"本次共评估 {total} 条核心假设，其中 {complete} 条在当前产物范围内形成了相对完整的证据链，"
            f"{partial} 条仍存在不同程度的证据缺口。"
        )
        highlights = [x for x in outcomes if x.get("details")]
        if highlights:
            top = highlights[:3]
            summary = "；".join(
                [f"{x['id']} 关注“{x['title']}”并观察到 {x['details'][0]}" for x in top]
            )
            lines.append(f"从跨假设视角看，主要信息集中在：{summary}。")
        missing = [x for x in outcomes if x.get("missing")]
        if missing:
            miss_text = "；".join([f"{x['id']} 缺失 {', '.join(x['missing'])}" for x in missing[:3]])
            lines.append(
                f"需要注意的是，仍有假设存在未闭环环节（{miss_text}），"
                "这会降低跨模块结论的可比性与稳定性。"
            )
        return "\n\n".join(lines)

    def _render_conclusion_recommendations(self, outcomes: list[dict[str, Any]]) -> str:
        if not outcomes:
            return "当前无可汇总结论。建议先补齐数据处理、统计分析和模型评估链路。"
        supported = [x for x in outcomes if x.get("details") and not x.get("missing")]
        uncertain = [x for x in outcomes if x.get("missing")]
        lines: list[str] = []
        if supported:
            ids = "、".join([x["id"] for x in supported])
            lines.append(f"结论上，{ids} 在当前数据与流程下形成了较完整证据，可作为后续解释与验证工作的优先基础。")
        if uncertain:
            ids = "、".join([x["id"] for x in uncertain])
            lines.append(f"同时，{ids} 仍处于证据不充分状态，暂不建议输出强结论。")
        lines.append("建议后续工作按“补齐缺失产物 → 交叉验证/对照验证 → 复现实验”顺序推进，并将失败路径与修复过程持续记录到报告附件。")
        return "\n\n".join(lines)

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
        visuals = self._prioritize_visuals(document_manifest.get("visualizations", []) or [])
        tables = document_manifest.get("tables", []) or []
        session_root = self._infer_session_root(visuals, tables, document_manifest)
        binding_map: dict[str, str] = {}
        render_manifest: list[dict[str, Any]] = []
        if session_root:
            binding_path = session_root / "result" / "visual_binding.json"
            if binding_path.exists():
                binding_payload = self._load_json(binding_path)
                for item in binding_payload.get("bindings", []) if isinstance(binding_payload, dict) else []:
                    artifact = item.get("artifact")
                    hypothesis = item.get("hypothesis")
                    if artifact and hypothesis:
                        binding_map[artifact] = hypothesis
        lines: list[str] = []
        title = report_payload.get("title") or "DeepAnalyze 报告"
        lines.append(f"# {title}")
        lines.append("")
        if execution_warning:
            lines.append(execution_warning)
            lines.append("")
        summary = report_payload.get("summary") or "本报告基于自动化分析流程产物生成，重点按假设-验证-结果-分析进行组织。"
        outline_mode = str(report_payload.get("outline_mode", "structure_only")).strip().lower()
        lines.append("## 摘要")
        lines.append(summary)
        lines.append("")

        # Section 1: hypotheses and objectives
        plan_json = self._load_plan_json(session_root)
        hypotheses_md, process_md = self._extract_plan_sections(session_root)
        lines.append("## 研究目标与原始假设")
        if hypotheses_md:
            lines.append(hypotheses_md)
        elif outline:
            if outline_mode == "full_quote":
                lines.append("未读取到结构化假设，以下为报告大纲摘录：")
                lines.append("\n".join([f"> {line}" if line.strip() else ">" for line in outline.splitlines()]))
            else:
                lines.append("未读取到结构化假设，已启用 `structure_only` 模式：大纲仅作为章节结构参考，不直接并入正文。")
        else:
            lines.append("未找到原始假设文件。")
        outline_conflict_note = self._outline_conflict_note(outline, plan_json)
        if outline_conflict_note:
            lines.append(f"冲突注记：{outline_conflict_note}。正文已以真实执行结果与证据为准。")
        lines.append("")

        # Section 2: implementation process
        lines.append("## 分析方法与实施过程")
        if process_md:
            lines.append(process_md)
        else:
            lines.append("未解析到详细过程，建议检查 plan/analysis_plan.md。")
        lines.append("")

        # Section 3: per-hypothesis validation sections
        lines.append("## 假设验证与结果分析")
        hypothesis_results = self._load_hypothesis_results(session_root)
        hypothesis_evidence = self._load_hypothesis_evidence(session_root)
        hypothesis_contrast = self._load_hypothesis_contrast(session_root)
        used_visuals: set[str] = set()
        used_tables: set[str] = set()
        hypothesis_outcomes: list[dict[str, Any]] = []
        hypotheses = plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []
        if not hypotheses and hypothesis_results.get("hypotheses"):
            hypotheses = [{"id": f"H{i+1}", "title": item.get("hypothesis", ""), "hypothesis": ""} for i, item in enumerate(hypothesis_results.get("hypotheses", []))]
        if hypotheses:
            for idx, hyp in enumerate(hypotheses):
                hyp_id = str(hyp.get("id") or f"H{idx+1}")
                hyp_title = str(hyp.get("title") or hyp_id)
                hyp_text = str(hyp.get("hypothesis") or "")
                plan_steps = hyp.get("validation_plan_steps") or hyp.get("steps") or []
                expected_artifacts = hyp.get("expected_artifacts") or hyp.get("artifacts") or []
                run_entry = self._hypothesis_result_entry(hyp_id, hypothesis_results)
                evidence_entry = self._hypothesis_evidence_entry(hyp_id, hypothesis_evidence)
                contrast_entry = self._hypothesis_contrast_entry(hyp_id, hypothesis_contrast)
                missing = run_entry.get("missing", []) if isinstance(run_entry, dict) else []
                step_map = run_entry.get("steps", {}) if isinstance(run_entry, dict) else {}
                quant_metrics = evidence_entry.get("quant_metrics", {}) if isinstance(evidence_entry, dict) else {}
                if not quant_metrics:
                    if "quant_metrics_missing" not in missing:
                        missing = list(missing) + ["quant_metrics_missing"]
                lines.append(f"### {hyp_id} {hyp_title}")
                if hyp_text:
                    lines.append(f"**假设内容**：{hyp_text}")
                    lines.append("")
                lines.append("**验证方案**：")
                if plan_steps:
                    for i, step in enumerate(plan_steps, 1):
                        lines.append(f"{i}. {step}")
                else:
                    lines.append("- 未提供结构化验证步骤。")
                lines.append("")
                lines.append("**执行结果**：")
                if step_map:
                    step_desc: list[str] = []
                    for step_name, payload in step_map.items():
                        status = payload.get("status") if isinstance(payload, dict) else ""
                        output = payload.get("output") if isinstance(payload, dict) else ""
                        step_desc.append(f"{step_name}(status={status}, output={output})")
                    lines.append("；".join(step_desc) + "。")
                else:
                    lines.append("未读取到执行步骤明细。")
                if expected_artifacts:
                    lines.append(f"计划产物：{', '.join([str(x) for x in expected_artifacts])}。")
                if missing:
                    lines.append(f"缺失产物：{', '.join([str(x) for x in missing])}。")
                else:
                    lines.append("缺失产物：无。")
                lines.append("")
                lines.append("**结果分析**：")
                details = self._hypothesis_data_analysis(hyp_id, session_root)
                lines.append(
                    self._render_result_analysis_paragraph(
                        hyp_id,
                        hyp_text,
                        details,
                        missing,
                        quant_metrics,
                        str(contrast_entry.get("status", "inconclusive")) if isinstance(contrast_entry, dict) else "inconclusive",
                    )
                )
                lines.append("")
                lines.append(
                    f"**分析来源**：自动提取证据 + 规则化解释。"
                    f"{'（定量指标不足，已降级为不确定结论）' if not quant_metrics else ''}"
                )
                lines.append("")
                if contrast_entry:
                    pa = contrast_entry.get("path_a", {}) if isinstance(contrast_entry, dict) else {}
                    pb = contrast_entry.get("path_b", {}) if isinstance(contrast_entry, dict) else {}
                    lines.append("**路径对照（A/B）**：")
                    lines.append("<table border=1 cellpadding=4 cellspacing=0>")
                    lines.append("<thead><tr><th>路径</th><th>状态</th><th>指标摘要</th></tr></thead><tbody>")
                    lines.append(
                        f"<tr><td>A</td><td>{pa.get('status','')}</td><td>{json.dumps(pa.get('metrics', {}), ensure_ascii=False)[:220]}</td></tr>"
                    )
                    lines.append(
                        f"<tr><td>B</td><td>{pb.get('status','')}</td><td>{json.dumps(pb.get('metrics', {}), ensure_ascii=False)[:220]}</td></tr>"
                    )
                    lines.append("</tbody></table>")
                    lines.append(
                        f"一致性判定：{contrast_entry.get('consistency','unknown')}；"
                        f"状态：{contrast_entry.get('status','inconclusive')}。"
                    )
                    if contrast_entry.get("conflict_reason"):
                        lines.append(f"冲突说明：{contrast_entry.get('conflict_reason')}")
                    if str(contrast_entry.get("status", "")).lower() == "inconclusive":
                        lines.append(
                            "一致性解释：A/B 路径出现冲突或证据不足，当前仅能给出不确定结论，"
                            "需要补充数据、改进特征工程或增加独立验证路径后再作判断。"
                        )
                    lines.append("")
                if isinstance(evidence_entry, dict):
                    sources = evidence_entry.get("evidence_sources", []) or []
                    if sources:
                        lines.append("**证据摘录**：")
                        for src in sources[:4]:
                            rel = str(src)
                            lines.append(f"来源：`{rel}`")
                            snippet = self._extract_evidence_snippet(session_root, rel)
                            if snippet:
                                lines.append("```text")
                                lines.append(snippet[:1200])
                                lines.append("```")
                        lines.append("")
                hypothesis_outcomes.append(
                    {
                        "id": hyp_id,
                        "title": hyp_title,
                        "missing": missing,
                        "details": details,
                        "quant_metrics": quant_metrics,
                    }
                )
                bound_visuals = self._hypothesis_bound_visuals(hyp_id, visuals, binding_map)
                if bound_visuals:
                    lines.append("**图表与解释**：")
                    lines.append(self._build_visual_block(bound_visuals, session_root, binding_map, render_manifest))
                    lines.append("")
                    used_visuals.update(v.get("relative_path", "") for v in bound_visuals)
        else:
            visuals_by_category: Dict[str, List[Dict[str, Any]]] = {}
            for item in visuals:
                category = self._classify_visual(item)
                visuals_by_category.setdefault(category, []).append(item)
            sections = report_payload.get("sections") or self._auto_sections(visuals_by_category)
            for section in sections:
                section_title = section.get("title", "Section")
                section_body = section.get("body", "")
                lines.append(f"### {section_title}")
                lines.append(section_body)
                if "差异" in section_title or "Differential" in section_title:
                    scoped = visuals_by_category.get("diff", [])
                elif "相关" in section_title or "Correlation" in section_title:
                    scoped = visuals_by_category.get("correlation", [])
                elif "分布" in section_title or "统计" in section_title or "Distribution" in section_title:
                    scoped = visuals_by_category.get("distribution", [])
                elif "聚类" in section_title or "降维" in section_title or "Embedding" in section_title:
                    scoped = visuals_by_category.get("embedding", [])
                else:
                    scoped = visuals_by_category.get("other", [])
                if scoped:
                    lines.append(self._build_visual_block(scoped, session_root, binding_map, render_manifest))
                    used_visuals.update(v.get("relative_path", "") for v in scoped)
                lines.append("")
        lines.append("")

        # Section 4: cross-hypothesis synthesis
        lines.append("## 跨假设综合讨论")
        lines.append(self._render_cross_hypothesis_discussion(hypothesis_outcomes))
        lines.append("")

        # Section 5: conclusion and recommendations
        lines.append("## 结论与建议")
        lines.append(self._render_conclusion_recommendations(hypothesis_outcomes))
        lines.append("")

        # Section 6: quality, completion and risks
        lines.append("## 质量校验与未完成项")
        failure_block = self._render_validation_failures(session_root)
        quality_block = self._render_quality_warnings(session_root)
        matrix_block = self._render_hypothesis_matrix(session_root)
        coverage_block = self._render_coverage_report(session_root)
        if failure_block:
            lines.append(failure_block.replace("## 验证失败记录\n", ""))
            lines.append("")
        if quality_block:
            lines.append(quality_block.replace("## 质量门槛未达标\n", ""))
            lines.append("")
        if matrix_block:
            lines.append(matrix_block)
            lines.append("")
        if coverage_block:
            lines.append(coverage_block.replace("## 覆盖策略与遗漏项\n", ""))
            lines.append("")

        # Section 7: table previews
        if tables:
            table_blocks = self._table_preview_blocks(tables, session_root)
            if table_blocks:
                lines.append("## 关键数据表")
                lines.extend(table_blocks)
                for item in tables:
                    if item.get("name", "") in {"top_features.json", "stats_summary.json", "model_eval.json"}:
                        used_tables.add(item.get("relative_path", ""))
                lines.append("")

        # Section 8: appendix (non-duplicated)
        lines.append(self._render_appendix(document_manifest, used_visuals, used_tables, binding_map))
        lines.append("")
        if session_root:
            meta_dir = session_root / "meta"
            meta_dir.mkdir(parents=True, exist_ok=True)
            (meta_dir / "render_manifest.json").write_text(
                json.dumps({"resources": render_manifest}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        lines.append(self._preview_script())
        lines.append("")
        return "\n".join(lines).strip()
