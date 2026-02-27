from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
from src.core.analytics.resources import load_feature_dictionary
from src.core.reporting.narrative import (
    detect_metric_conflicts_detailed,
    detect_metric_conflicts,
    failed_check_review_steps,
    failed_check_sentence,
    gate_rule_type_sentence,
    gate_status_sentence,
    has_failed_check_explanation,
    has_reason_code_explanation,
    metric_narrative,
    recovery_action_sentence,
    reason_code_sentence,
)


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

    def _load_feature_dict(self, session_root: Path | None) -> dict[str, dict[str, Any]]:
        if not session_root:
            return {}
        try:
            payload = load_feature_dictionary(session_root)
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    def _feature_display(self, feature: str, feature_dict: dict[str, dict[str, Any]]) -> str:
        key = str(feature)
        info = feature_dict.get(key, {}) if isinstance(feature_dict, dict) else {}
        display = str(info.get("display_name") or info.get("name") or key).strip() or key
        meaning = str(info.get("meaning") or info.get("description") or "").strip()
        if meaning:
            return f"{display}（{meaning}）"
        return f"{display}（未知语义）"

    def _preview_script(self) -> str:
        return (
            "<script>\n"
            "async function renderTable(block){\n"
            "  const src = block.dataset.src;\n"
            "  const title = block.dataset.title || src;\n"
            "  if (window.location.protocol === 'file:') {\n"
            "    block.innerHTML = `<h4>${title}</h4><div>本地 file:// 模式下附件表格预览可能受浏览器策略限制。请使用本地 HTTP 服务打开报告；仍可通过路径访问: <code>${src}</code></div>`;\n"
            "    return;\n"
            "  }\n"
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
            "  if (window.location.protocol === 'file:') {\n"
            "    block.textContent = 'file:// 模式预览受限，请通过本地 HTTP 服务打开；附件路径: ' + src;\n"
            "    return;\n"
            "  }\n"
            "  try {\n"
            "    const res = await fetch(src);\n"
            "    const text = await res.text();\n"
            "    block.textContent = text.slice(0, 4000);\n"
            "  } catch (e) {\n"
            "    block.textContent = '预览失败: ' + e + '；附件路径: ' + src;\n"
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
        # Normalize accidental absolute filesystem paths to relative-like display path.
        if path.startswith("/"):
            return f"..{path}"
        if path.startswith("../"):
            return path
        return f"../{path}"

    def _normalize_relative_path(self, session_root: Path | None, raw_path: str) -> str:
        if not raw_path:
            return ""
        text = str(raw_path).strip()
        if not text:
            return ""
        lower = text.lower()
        if lower.startswith(("http://", "https://", "data:")):
            return text
        p = Path(text)
        if p.is_absolute() and session_root:
            try:
                return str(p.relative_to(session_root))
            except Exception:
                return text
        return text

    def _resource_health(self, session_root: Path | None, relative_path: str) -> tuple[bool, str]:
        if not relative_path:
            return False, "empty_path"
        lower = relative_path.lower()
        if lower.startswith(("http://", "https://", "data:")):
            return True, "ok_remote"
        if "://" in relative_path:
            return False, "illegal_scheme"
        if relative_path.startswith("/"):
            if session_root:
                try:
                    _ = Path(relative_path).relative_to(session_root)
                    return True, "ok_absolute_under_session"
                except Exception:
                    return False, "absolute_path_forbidden"
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
        feature_dict: dict[str, dict[str, Any]],
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
                    feat_label = self._feature_display(str(feat), feature_dict)
                    top_items.append(f"{feat_label} (mean_diff={diff:.3g}, p={pval:.3g})")
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
            pair_display = (
                self._feature_display(str(pair[0]), feature_dict),
                self._feature_display(str(pair[1]), feature_dict),
            )
            max_corr = arr[max_idx]
            return (
                "<div class=\"chart-explain\">"
                f"<p><strong>假设</strong>：{bound_hypothesis or '峰值之间存在相关性结构'}。</p>"
                "<p><strong>验证</strong>：计算相关矩阵并绘制热力图。</p>"
                "<p><strong>坐标/颜色</strong>：X/Y 为峰值变量，颜色表示相关系数（-1~1）。</p>"
                f"<p><strong>结论</strong>：最大绝对相关约 {max_corr:.3g}，"
                f"对应 {pair_display[0]} 与 {pair_display[1]}。</p>"
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
            pair_display = (
                self._feature_display(str(pair[0]), feature_dict),
                self._feature_display(str(pair[1]), feature_dict),
            )
            max_corr = arr[max_idx]
            edge_count = int((np.abs(arr) > 0.5).sum() / 2)
            return (
                "<div class=\"chart-explain\">"
                f"<p><strong>假设</strong>：{bound_hypothesis or '存在强相关的峰值网络结构'}。</p>"
                "<p><strong>验证</strong>：对相关矩阵阈值筛边（|corr|>0.5）构建网络。</p>"
                "<p><strong>颜色/图例</strong>：蓝线为正相关，红线为负相关，"
                "仅显示 |corr|>0.5 的边。</p>"
                f"<p><strong>结论</strong>：最强相关对为 {pair_display[0]} 与 {pair_display[1]}（|corr|≈{abs(max_corr):.3g}），"
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
            x_label = self._feature_display(str(x_col), feature_dict)
            y_label = self._feature_display(str(y_col), feature_dict)
            corr_text = f"{corr_val:.3g}" if isinstance(corr_val, (int, float)) else "未知"
            return (
                "<div class=\"chart-explain\">"
                f"<p><strong>假设</strong>：{bound_hypothesis or (x_label + ' 与 ' + y_label + ' 之间存在相关关系')}。</p>"
                "<p><strong>验证</strong>：选取绝对相关最高的两个变量绘制散点图。</p>"
                f"<p><strong>坐标</strong>：X={x_label}, Y={y_label}。</p>"
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
                        names.append(self._feature_display(str(item["feature"]), feature_dict))
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
        feature_dict: dict[str, dict[str, Any]],
        render_manifest: list[dict[str, Any]] | None = None,
    ) -> str:
        lines: list[str] = []
        feature_dict = self._load_feature_dict(session_root)
        for item in visuals:
            name = item.get("name", "visual")
            note = self._normalize_relative_path(session_root, str(item.get("relative_path", "")))
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
            explanation = self._visual_explanation(item, session_root, binding_map, feature_dict)
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
        process = self._sanitize_process_section(process)
        return hypotheses, process

    def _load_plan_markdown(self, session_root: Path | None) -> str:
        if not session_root:
            return ""
        candidates = [session_root / "plan" / "analysis_plan.md"]
        artifact_root = session_root / "artifacts"
        if artifact_root.exists():
            candidates.extend(list(artifact_root.glob("*/plan/analysis_plan.md")))
        for path in candidates:
            if path.exists():
                try:
                    return path.read_text(encoding="utf-8")
                except Exception:
                    continue
        return ""

    def _extract_hypothesis_steps_from_plan_markdown(self, plan_md: str, hyp_id: str) -> list[str]:
        if not plan_md:
            return []
        hid = str(hyp_id).strip().upper()
        if not hid.startswith("H"):
            return []
        try:
            num = int(hid[1:])
        except Exception:
            return []
        header = re.compile(rf"^####\s*假设\s*{num}\b[：: ]?.*$", re.MULTILINE)
        m = header.search(plan_md)
        if not m:
            return []
        start = m.end()
        next_m = re.compile(r"^####\s*假设\s*\d+\b.*$", re.MULTILINE).search(plan_md, start)
        end = next_m.start() if next_m else len(plan_md)
        block = plan_md[start:end]
        steps: list[str] = []
        for raw in block.splitlines():
            line = raw.strip()
            if not line:
                continue
            line = re.sub(r"^\*\s*", "", line)
            line = re.sub(r"^-\s*", "", line)
            line = re.sub(r"^\d+\.\s*", "", line)
            line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
            if not line:
                continue
            if any(k in line for k in ("预期产物", "成功判据", "后续行动", "核心假设")):
                continue
            if any(k in line for k in ("验证路径",)):
                steps.append(line)
                continue
            if any(k in line for k in ("检验", "分析", "模型", "聚类", "降维", "校正")):
                steps.append(line)
        dedup: list[str] = []
        seen: set[str] = set()
        for step in steps:
            if step in seen:
                continue
            seen.add(step)
            dedup.append(step)
            if len(dedup) >= 8:
                break
        return dedup

    def _extract_hypothesis_title_from_plan_markdown(self, plan_md: str, hyp_id: str) -> str:
        if not plan_md:
            return ""
        hid = str(hyp_id).strip().upper()
        if not hid.startswith("H"):
            return ""
        try:
            num = int(hid[1:])
        except Exception:
            return ""
        m = re.search(rf"^####\s*假设\s*{num}\s*[：:]\s*(.+)$", plan_md, flags=re.MULTILINE)
        return m.group(1).strip() if m else ""

    def _extract_title_from_run_hypothesis(self, run_hypothesis: str, hyp_id: str) -> str:
        text = str(run_hypothesis or "").strip()
        if not text:
            return ""
        hid = str(hyp_id).strip().upper()
        prefix = f"{hid}:"
        if text.upper().startswith(prefix):
            return text[len(prefix) :].strip()
        return ""

    def _focus_from_gate_rule(self, gate_rule_type: str) -> str:
        rule = str(gate_rule_type or "").strip().lower()
        mapping = {
            "significance_and_effect": "difference",
            "predictive_performance": "predictive",
            "correlation_structure": "correlation",
            "embedding_structure": "embedding",
        }
        return mapping.get(rule, "generic")

    def _text_matches_focus(self, text: str, focus: str) -> bool:
        t = str(text or "")
        if not t:
            return True
        rules = {
            "difference": ["差异", "显著", "检验", "fdr", "p 值", "q 值"],
            "predictive": ["预测", "分类", "auc", "roc", "模型", "训练", "测试", "交叉验证"],
            "correlation": ["相关", "网络", "热图", "corr", "相关性"],
            "embedding": ["降维", "聚类", "pca", "tsne", "umap", "轮廓系数"],
        }
        keys = rules.get(focus, [])
        if not keys:
            return True
        return any(k.lower() in t.lower() for k in keys)

    def _step_io_hint(self, step_text: str, step_map: dict[str, Any]) -> str:
        if not isinstance(step_map, dict) or not step_map:
            return ""
        st = str(step_text).lower()
        for step_name, payload in step_map.items():
            name = str(step_name).strip()
            if not name:
                continue
            if name.lower() in st or st in name.lower():
                if isinstance(payload, dict):
                    status = str(payload.get("status", "")).strip()
                    output = str(payload.get("output", "")).strip()
                    output_name = Path(output).name if output else "未标注"
                    if status or output:
                        return f"（输入：上一步产物；输出：{output_name}；状态：{status or 'unknown'}）"
                return "（输入：上一步产物；输出：见执行事实）"
        return ""

    def _render_method_steps(self, plan_steps: list[str], step_map: dict[str, Any] | None = None) -> list[str]:
        if not plan_steps:
            return ["- 未找到可用验证步骤（结构化字段和计划文本均未命中，步骤证据不足）。"]
        path_a: list[str] = []
        path_b: list[str] = []
        common: list[str] = []
        current = "common"
        for raw in plan_steps:
            step = str(raw).strip()
            if not step:
                continue
            step = re.sub(r"\*\*(.+?)\*\*", r"\1", step)
            if any(k in step for k in ("预期产物", "成功判据", "后续行动", "核心假设")):
                continue
            low = step.lower()
            if re.search(r"验证路径\s*[aAＡ]", step) or "path a" in low:
                current = "a"
                continue
            if re.search(r"验证路径\s*[bBＢ]", step) or "path b" in low:
                current = "b"
                continue
            if current == "a":
                path_a.append(step)
            elif current == "b":
                path_b.append(step)
            else:
                common.append(step)

        lines: list[str] = []
        if common:
            lines.append("通用步骤：")
            lines.append("<ol>")
            for item in common[:8]:
                lines.append(f"<li>{item}{self._step_io_hint(item, step_map or {})}</li>")
            lines.append("</ol>")
        if path_a:
            lines.append("验证路径 A：")
            lines.append("<ol>")
            for item in path_a[:8]:
                lines.append(f"<li>{item}{self._step_io_hint(item, step_map or {})}</li>")
            lines.append("</ol>")
        if path_b:
            lines.append("验证路径 B：")
            lines.append("<ol>")
            for item in path_b[:8]:
                lines.append(f"<li>{item}{self._step_io_hint(item, step_map or {})}</li>")
            lines.append("</ol>")
        if not lines:
            lines.append("<ol>")
            for item in plan_steps[:8]:
                lines.append(f"<li>{item}</li>")
            lines.append("</ol>")
        return lines

    def _render_global_process_summary(self, process_md: str) -> list[str]:
        if not process_md:
            return ["未解析到详细过程，建议检查 plan/analysis_plan.md。"]
        points: list[str] = []
        for raw in process_md.splitlines():
            line = str(raw).strip()
            if not line:
                continue
            line = re.sub(r"^\d+\.\s*", "", line)
            line = re.sub(r"^[-*]\s*", "", line)
            line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
            line = line.replace("*", "").strip()
            low = line.lower()
            if (
                "假设" in line
                or "验证路径" in line
                or "预期产物" in line
                or "成功判据" in line
                or "后续行动" in line
                or "下一步指令" in line
                or "请确认是否开始执行" in line
                or low.startswith("###")
            ):
                continue
            if any(k in line for k in ("清洗", "标准化", "检验", "校正", "建模", "交叉验证", "可视化", "装配")):
                points.append(line)
        dedup: list[str] = []
        seen: set[str] = set()
        for p in points:
            if p in seen:
                continue
            seen.add(p)
            dedup.append(p)
            if len(dedup) >= 8:
                break
        if not dedup:
            return ["未提取到全局流程要点（已过滤假设级重复内容）。"]
        lines = ["本节仅保留全局流程摘要，假设级细节请见后续“假设验证与结果分析”。", "<ol>"]
        for item in dedup:
            lines.append(f"<li>{item}</li>")
        lines.append("</ol>")
        return lines

    def _render_hypothesis_problem_block(
        self,
        hyp_title: str,
        effective_hypothesis: str,
        mismatch_note: str,
        planned_title: str,
        planned_hypothesis: str,
        executed_hypothesis: str,
    ) -> list[str]:
        lines: list[str] = []
        lines.append(f"<p><strong>研究问题</strong>：{hyp_title}。</p>")
        if planned_hypothesis:
            lines.append(f"<p><strong>计划假设（来自分析计划）</strong>：{planned_hypothesis}</p>")
        else:
            lines.append("<p><strong>计划假设（来自分析计划）</strong>：未提供。</p>")
        if effective_hypothesis:
            lines.append(f"<p><strong>实际执行假设（来自执行结果）</strong>：{effective_hypothesis}</p>")
        else:
            lines.append("<p><strong>实际执行假设（来自执行结果）</strong>：未提供。</p>")
        if mismatch_note:
            lines.append(f"<p><strong>一致性注记（偏差说明）</strong>：{mismatch_note}</p>")
            lines.append("<ul>")
            if planned_title:
                lines.append(f"<li>计划标题：{planned_title}</li>")
            if executed_hypothesis:
                lines.append(f"<li>执行标题：{executed_hypothesis}</li>")
            lines.append("</ul>")
            lines.append("<p>本节后续结论以实际执行结果为主，计划内容仅用于对照。</p>")
        return lines

    def _predictive_completeness_missing(
        self,
        gate_entry: dict[str, Any],
        evidence_entry: dict[str, Any],
        step_map: dict[str, Any],
        contrast_entry: dict[str, Any],
    ) -> list[str]:
        gate_rule = str(gate_entry.get("gate_rule_type", "")).strip().lower()
        if gate_rule != "predictive_performance":
            return []
        missing: list[str] = []
        quant_rows = evidence_entry.get("quant_metrics", []) if isinstance(evidence_entry.get("quant_metrics"), list) else []
        quant_names = {
            str(item.get("name", "")).strip().lower()
            for item in quant_rows
            if isinstance(item, dict)
        }
        method_trace = evidence_entry.get("method_trace", []) if isinstance(evidence_entry.get("method_trace"), list) else []
        model_found = False
        for item in method_trace:
            if not isinstance(item, dict):
                continue
            model_name = str(item.get("model_name") or item.get("model") or item.get("estimator") or "").strip()
            if model_name:
                model_found = True
                break
        if not model_found:
            for step_name in step_map.keys():
                low = str(step_name).lower()
                if any(k in low for k in ("logistic", "randomforest", "xgboost", "svm", "classifier", "model")):
                    model_found = True
                    break
        if not model_found:
            missing.append("predictive_model_name_missing")

        has_split = bool({"cv_mean_accuracy", "cv_std_accuracy", "test_accuracy", "train_accuracy"} & quant_names)
        if not has_split:
            missing.append("predictive_data_split_strategy_missing")
        has_primary_perf = bool({"auc", "accuracy", "f1", "precision", "recall", "centroid_accuracy", "majority_accuracy"} & quant_names)
        if not has_primary_perf:
            missing.append("predictive_primary_metric_missing")
        conflict_reason = str(contrast_entry.get("conflict_reason", "")).strip()
        reason_code = str(gate_entry.get("reason_code", "")).strip()
        has_conflict_explain = bool(conflict_reason or reason_code)
        if not has_conflict_explain:
            missing.append("predictive_conflict_explain_missing")
        return missing

    def _missing_item_label(self, item: str) -> str:
        mapping = {
            "quant_metrics_missing": "缺少可解释的定量指标",
            "insufficient_quant_metric_count": "定量指标数量不足（<2）",
            "evidence_binding_missing": "缺少证据来源绑定",
            "predictive_model_name_missing": "预测假设缺少模型名称",
            "predictive_data_split_strategy_missing": "预测假设缺少训练/验证设置说明",
            "predictive_primary_metric_missing": "预测假设缺少主性能指标（如 Accuracy/AUC/F1）",
            "predictive_conflict_explain_missing": "预测假设缺少冲突/风险说明",
        }
        return mapping.get(item, item)

    def _execution_steps_from_step_map(self, step_map: dict[str, Any], gate_rule_type: str) -> list[str]:
        steps: list[str] = []
        if isinstance(step_map, dict):
            for key, payload in step_map.items():
                status = ""
                if isinstance(payload, dict):
                    status = str(payload.get("status", "")).strip()
                if status:
                    steps.append(f"{key}（执行状态：{status}）")
                else:
                    steps.append(str(key))
        rule = str(gate_rule_type or "").strip().lower()
        if rule == "predictive_performance":
            steps.extend(
                [
                    "基于已产出的模型评估结果汇总预测性能（如 accuracy / AUC / CV 指标）。",
                    "核对训练/验证划分策略与标签映射，避免评估设置不一致。",
                ]
            )
        elif rule == "correlation_structure":
            steps.extend(
                [
                    "基于相关矩阵与网络图产物验证变量相关结构。",
                    "核对强相关边阈值与网络拓扑指标的一致性。",
                ]
            )
        elif rule == "embedding_structure":
            steps.extend(
                [
                    "基于降维与聚类产物验证样本分离结构。",
                    "核对聚类数量与分离度指标（如 silhouette）是否一致。",
                ]
            )
        elif rule == "significance_and_effect":
            steps.extend(
                [
                    "基于显著性检验与多重校正结果验证差异性。",
                    "核对效应量证据是否充足，避免仅凭 p 值下结论。",
                ]
            )
        dedup: list[str] = []
        seen: set[str] = set()
        for s in steps:
            if s in seen:
                continue
            seen.add(s)
            dedup.append(s)
        return dedup[:8]

    def _render_plan_hypothesis_overview(self, plan_json: dict[str, Any]) -> str:
        hypotheses = plan_json.get("hypotheses", []) if isinstance(plan_json, dict) else []
        if not hypotheses:
            return ""
        lines: list[str] = []
        lines.append("<ul>")
        for item in hypotheses:
            if not isinstance(item, dict):
                continue
            hid = str(item.get("id", "")).strip()
            title = str(item.get("title", "")).strip()
            hyp = str(item.get("hypothesis", "")).strip()
            if not hid:
                continue
            if hyp:
                lines.append(f"<li>{hid} {title}：{hyp}</li>")
            else:
                lines.append(f"<li>{hid} {title}</li>")
        lines.append("</ul>")
        return "\n".join(lines)

    def _sanitize_process_section(self, process: str) -> str:
        if not process:
            return process
        lines = process.splitlines()
        out: list[str] = []
        in_hypothesis_subsection = False
        for line in lines:
            stripped = line.strip()
            if re.match(r"^(#+\s*)?1\.\s*假设列表", stripped, flags=re.IGNORECASE):
                in_hypothesis_subsection = True
                continue
            if in_hypothesis_subsection and re.match(r"^(#+\s*)?\d+\.\s*", stripped):
                in_hypothesis_subsection = False
            if in_hypothesis_subsection:
                continue
            if "下一步指令" in stripped or "请确认是否开始执行" in stripped:
                continue
            out.append(line)
        return "\n".join(out).strip()

    def _render_appendix(
        self,
        document_manifest: Dict[str, Any],
        used_visuals: set[str],
        used_tables: set[str],
        session_root: Path | None = None,
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
                rel = self._normalize_relative_path(session_root, str(item.get("relative_path", "")))
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
                rel = self._normalize_relative_path(session_root, str(item.get("relative_path", "")))
                lines.append(f"  - <div class=\"appendix-item\" data-hypothesis=\"ALL\">{self._report_relative(rel)} (fallback path: {rel})</div>")
                lines.append(f"    <div class=\"table-preview\" data-src=\"{self._report_relative(rel)}\" data-title=\"{item.get('name','table')}\"></div>")
        for group, paths in extra_groups.items():
            uniq = sorted(set(paths))
            if not uniq:
                continue
            lines.append(f"- {group}:")
            for rel in uniq:
                rel2 = self._normalize_relative_path(session_root, str(rel))
                lines.append(f"  - <div class=\"appendix-item\" data-hypothesis=\"ALL\">{self._report_relative(rel2)} (fallback path: {rel2})</div>")
                lower = rel2.lower()
                if lower.endswith((".txt", ".md", ".log")):
                    lines.append(f"    <pre class=\"attachment-preview\" data-src=\"{self._report_relative(rel2)}\"></pre>")
                elif lower.endswith(".json"):
                    lines.append(f"    <pre class=\"attachment-preview\" data-src=\"{self._report_relative(rel2)}\"></pre>")
                elif lower.endswith(".csv"):
                    lines.append(f"    <div class=\"table-preview\" data-src=\"{self._report_relative(rel2)}\" data-title=\"{Path(rel2).name}\"></div>")
                elif lower.endswith(".pdf"):
                    lines.append(
                        f"    <object data=\"{self._report_relative(rel2)}\" type=\"application/pdf\" "
                        "style=\"width:100%;height:420px;border:1px solid #ddd;\">"
                        f"<a href=\"{self._report_relative(rel2)}\" target=\"_blank\">PDF 预览失败，点击打开原文件</a>"
                        "</object>"
                    )
                elif lower.endswith((".html", ".htm")):
                    lines.append(
                        f"    <iframe src=\"{self._report_relative(rel2)}\" loading=\"lazy\" "
                        "style=\"width:100%;height:360px;border:1px solid #ddd;\"></iframe>"
                    )
                    lines.append(
                        f"    <div>若 iframe 失败，请直接打开: <a href=\"{self._report_relative(rel2)}\" target=\"_blank\">{Path(rel2).name}</a></div>"
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

    def _table_preview_blocks(
        self,
        tables: list[Dict[str, Any]],
        session_root: Path | None,
        feature_dict: dict[str, dict[str, Any]],
    ) -> list[str]:
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
                top_features_note = ""
                if session_root:
                    top_path = session_root / "result" / "top_features.json"
                    if top_path.exists():
                        try:
                            payload = self._load_json(top_path)
                            if isinstance(payload, list):
                                mapped = []
                                for row in payload[:5]:
                                    if isinstance(row, dict) and row.get("feature"):
                                        mapped.append(self._feature_display(str(row.get("feature")), feature_dict))
                                if mapped:
                                    top_features_note = "<p><strong>特征语义</strong>：" + "；".join(mapped) + "。</p>"
                        except Exception:
                            top_features_note = ""
                blocks.append(
                    "<div class=\"table-explain\">"
                    "<p><strong>输入</strong>：统计检验结果。</p>"
                    "<p><strong>输出</strong>：按 p/q 值排序的 Top 特征列表。</p>"
                    "<p><strong>结论</strong>：用于定位差异最显著的峰值。</p>"
                    f"{top_features_note}"
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
        lines = ["## 质量规则未达标"]
        if missing_required:
            lines.append(f"- 缺失核心产物: {', '.join(missing_required)}")
        if gate_missing:
            lines.append(f"- 缺失质量规则: {', '.join(gate_missing)}")
        return "\n".join(lines)

    def _render_completion_validation(self, session_root: Path | None) -> str:
        if not session_root:
            return ""
        path = session_root / "meta" / "completion_validation.json"
        if not path.exists():
            return ""
        payload = self._load_json(path)
        if not isinstance(payload, dict):
            return ""
        checks = payload.get("checks", {}) if isinstance(payload.get("checks"), dict) else {}
        reasons = payload.get("blocking_reasons", []) if isinstance(payload.get("blocking_reasons"), list) else []
        actions = payload.get("recovery_actions", []) if isinstance(payload.get("recovery_actions"), list) else []
        lines = ["## 完成态校验"]
        lines.append(f"- 结论: {'通过' if payload.get('complete', False) else '未通过'}")
        if reasons:
            lines.append(f"- 阻塞原因: {', '.join([str(r) for r in reasons])}")
        missing_files = checks.get("missing_essential_files", []) if isinstance(checks, dict) else []
        if missing_files:
            lines.append(f"- 缺失核心产物: {', '.join([str(x) for x in missing_files])}")
        unresolved = checks.get("unresolved_gate_hypotheses", []) if isinstance(checks, dict) else []
        if unresolved:
            lines.append(f"- 未闭环假设: {', '.join([str(x) for x in unresolved])}")
        if actions:
            lines.append("- 建议恢复动作:")
            for action in actions:
                lines.append(f"  - {action}")
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
        path = session_root / "result" / "hypothesis_evidence_pack.json"
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

    def _load_hypothesis_gate(self, session_root: Path | None) -> dict[str, Any]:
        if not session_root:
            return {}
        path = session_root / "result" / "hypothesis_gate_report.json"
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
                if isinstance(item.get("quant_metrics"), list):
                    # normalize evidence-pack metric list into legacy dict for renderer
                    metric_map: dict[str, Any] = {}
                    for metric in item.get("quant_metrics", []):
                        if not isinstance(metric, dict):
                            continue
                        key = str(metric.get("name", "")).strip()
                        if key:
                            metric_map[key] = metric.get("value")
                    return {**item, "quant_metrics_map": metric_map}
                return item
        return {}

    def _hypothesis_contrast_entry(self, hyp_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        for item in payload.get("hypotheses", []) if isinstance(payload, dict) else []:
            if str(item.get("hypothesis_id", "")).upper() == hyp_id.upper():
                return item
        return {}

    def _hypothesis_gate_entry(self, hyp_id: str, payload: dict[str, Any]) -> dict[str, Any]:
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

    def _evidence_detail_lines(
        self,
        evidence_entry: dict[str, Any],
        feature_dict: dict[str, dict[str, Any]],
    ) -> list[str]:
        lines: list[str] = []
        quant_list = evidence_entry.get("quant_metrics", [])
        if isinstance(quant_list, list) and quant_list:
            for metric in quant_list[:8]:
                if not isinstance(metric, dict):
                    continue
                display = metric.get("display_name") or metric.get("name")
                value = metric.get("value")
                unit = metric.get("unit") or ""
                threshold = metric.get("threshold") or ""
                piece = f"指标“{display}”当前值为 {value}{unit}"
                if threshold:
                    piece += f"，对照阈值 {threshold}"
                lines.append(piece + "。")
        effects = evidence_entry.get("effect_metrics", [])
        if isinstance(effects, list) and effects:
            for effect in effects[:5]:
                if not isinstance(effect, dict):
                    continue
                lines.append(f"效应量结果显示“{effect.get('name')}”取值为 {effect.get('value')}。")
        sources = evidence_entry.get("evidence_sources", [])
        if isinstance(sources, list):
            feature_refs: list[str] = []
            for src in sources:
                if isinstance(src, dict):
                    path = str(src.get("path", ""))
                else:
                    path = str(src)
                if "top_features" in path:
                    feature_refs.append(path)
            if feature_refs:
                lines.append("关键特征主要来自以下文件：" + "、".join(feature_refs) + "。")
        top_features = evidence_entry.get("top_features", [])
        if isinstance(top_features, list) and top_features:
            mapped = [self._feature_display(str(f), feature_dict) for f in top_features[:5]]
            lines.append("重点特征语义包括：" + "；".join(mapped) + "。")
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

    def _to_float(self, value: Any) -> float | None:
        try:
            if isinstance(value, bool):
                return None
            return float(value)
        except Exception:
            return None

    def _split_readable_paragraph(self, text: str, max_len: int = 180) -> list[str]:
        raw = str(text or "").strip()
        if not raw:
            return []
        if len(raw) <= max_len:
            return [raw]
        chunks = re.split(r"[；。]\s*", raw)
        chunks = [c.strip() for c in chunks if c.strip()]
        out: list[str] = []
        buf = ""
        for c in chunks:
            piece = c if c.endswith("。") else c + "。"
            if not buf:
                buf = piece
                continue
            if len(buf) + len(piece) <= max_len:
                buf += piece
            else:
                out.append(buf)
                buf = piece
        if buf:
            out.append(buf)
        return out if out else [raw]

    def _quantitative_judgement_lines(self, evidence_entry: dict[str, Any], style_offset: int = 0) -> list[str]:
        lines: list[str] = []
        quant = evidence_entry.get("quant_metrics", [])
        if not isinstance(quant, list):
            return lines
        for idx, metric in enumerate(quant[:12]):
            if not isinstance(metric, dict):
                continue
            if not str(metric.get("name") or metric.get("display_name") or "").strip():
                continue
            lines.append(metric_narrative(metric, idx + style_offset))
        return lines

    def _gate_check_label(self, key: str) -> str:
        mapping = {
            "has_dual_path_status": "双路径执行状态有效",
            "path_consistency": "路径一致性通过",
            "has_significance_metric": "存在显著性指标",
            "has_effect_metric": "存在效应量证据",
            "significance_count_ge_min": "显著特征数量达到阈值",
            "has_primary_performance": "存在主性能指标",
            "has_secondary_performance": "存在交叉验证性能指标",
            "primary_performance_ge_min": "主性能达到阈值",
            "secondary_performance_ge_min": "交叉验证性能达到阈值",
            "has_corr_strength": "存在相关强度指标",
            "has_corr_edge_support": "存在相关网络边支撑指标",
            "corr_strength_ge_min": "相关强度达到阈值",
            "corr_edge_ge_min": "相关边数量达到阈值",
            "has_cluster_or_embedding_metric": "存在聚类/嵌入指标",
            "cluster_count_ge_min": "聚类数量达到阈值",
            "quant_metric_count_ge_min": "定量指标数量达到阈值",
            "effect_or_consistency_support": "效应或一致性证据满足",
        }
        return mapping.get(key, key)

    def _bool_zh(self, value: Any) -> str:
        if value is True:
            return "通过"
        if value is False:
            return "未通过"
        return str(value)

    def _render_result_analysis_paragraph(
        self,
        hyp_id: str,
        hyp_text: str,
        details: list[str],
        missing: list[str],
        quant_metrics: dict[str, Any] | None = None,
        conclusion_status: str = "inconclusive",
        quant_evaluations: list[str] | None = None,
        gate_entry: dict[str, Any] | None = None,
        contrast_entry: dict[str, Any] | None = None,
        evidence_sources: list[str] | None = None,
    ) -> str:
        premise = hyp_text.strip() or f"{hyp_id} 假设"
        quant_metrics = quant_metrics or {}
        quant_evaluations = quant_evaluations or []
        gate_entry = gate_entry or {}
        contrast_entry = contrast_entry or {}
        evidence_sources = evidence_sources or []
        quant_text = ""
        if quant_evaluations:
            quant_text = "关键数值见本节“定量结果（指标与证据）”。"
        elif quant_metrics:
            quant_text = "已提取到定量指标，但阈值判定信息不完整。"
        gate_status = str(gate_entry.get("gate_status", "")).lower()
        gate_rule_type = str(gate_entry.get("gate_rule_type", "")).strip()
        failed_checks = gate_entry.get("failed_checks", []) if isinstance(gate_entry.get("failed_checks"), list) else []
        reason_code = str(gate_entry.get("reason_code", "")).strip() or str(contrast_entry.get("conflict_category", "")).strip()
        recovery_action = str(gate_entry.get("recovery_action", "")).strip()
        conflict_reason = str(contrast_entry.get("conflict_reason", "")).strip()
        gate_text = (
            f"判定规则说明：{gate_rule_type_sentence(gate_rule_type)} "
            f"判定状态说明：{gate_status_sentence(gate_status)}"
        )
        if failed_checks:
            gate_text += " 未通过项包括：" + "；".join([failed_check_sentence(str(x)) for x in failed_checks[:5]]) + "。"
        reason_text = reason_code_sentence(reason_code)
        if reason_text:
            gate_text += f" 原因解释：{reason_text}。"
        rule_type = str(gate_entry.get("gate_rule_type", "")).strip()
        conflict_input: list[dict[str, Any]] = []
        if isinstance(quant_metrics, dict):
            for k, v in quant_metrics.items():
                conflict_input.append({"name": k, "value": v})
        conflict_findings = detect_metric_conflicts(conflict_input)
        conflict_details = detect_metric_conflicts_detailed(conflict_input)
        if details:
            normalized_detail: list[str] = []
            for item in details[:4]:
                text = str(item).strip()
                if not text:
                    continue
                text = re.sub(r"[。；;]+$", "", text)
                normalized_detail.append(text)
            body = "；".join(normalized_detail)
            evidence_sentence = f"围绕“{premise}”，当前关键观测为：{body}。{quant_text}"
            if rule_type == "significance_and_effect":
                rule_sentence = "规则解释：差异性路径要求“显著性证据 + 效应量证据”同时成立，避免仅凭 p 值下结论。"
            elif rule_type == "predictive_performance":
                rule_sentence = "规则解释：预测路径要求主性能与交叉验证同时达标，用于约束泛化风险。"
            elif rule_type == "correlation_structure":
                rule_sentence = "规则解释：相关路径同时关注相关强度与网络边支撑，避免孤立强相关误判。"
            elif rule_type == "embedding_structure":
                rule_sentence = "规则解释：嵌入路径强调分离结构与聚类证据的协同支持。"
            else:
                rule_sentence = "规则解释：当前为通用证据路径，结论依赖定量指标完整性与一致性。"
            if conflict_reason:
                conflict_sentence = f"反证/冲突：{conflict_reason}。"
            elif conflict_findings:
                conflict_sentence = "反证/冲突：" + " ".join(conflict_findings[:2])
            else:
                conflict_sentence = "反证/冲突：未检测到显式路径冲突。"
            if conclusion_status in {"inconclusive", "failed"}:
                boundary_sentence = "边界：多路径证据尚未形成一致支持，当前仅可输出不确定结论。"
            elif missing:
                boundary_sentence = f"边界：仍存在未完成产物（{', '.join(missing)}），当前结论为阶段性结论。"
            else:
                boundary_sentence = "边界：当前证据满足主要判定条件，但仍需在独立数据或替代方法下复核稳健性。"
            extra_conflict = ""
            if conflict_details:
                first = conflict_details[0] if isinstance(conflict_details[0], dict) else {}
                steps = first.get("next_steps", []) if isinstance(first, dict) else []
                if steps:
                    extra_conflict = " 冲突复核建议：" + "；".join([str(x) for x in steps[:2]]) + "。"
            next_sentence = (
                f"下一步：{recovery_action_sentence(recovery_action) or '补充外部验证并复核关键指标稳定性。'}"
                if recovery_action
                else "下一步：补充外部验证并复核关键指标稳定性。"
            )
            evidence_binding_sentence = (
                "证据来源：" + "、".join([str(x) for x in evidence_sources[:4]])
                if evidence_sources
                else "证据来源：未提供结构化来源，本节结论降级为“待验证”。"
            )
            metric_block = ""
            if quant_evaluations:
                metric_lines = "".join([f"<li>{x}</li>" for x in quant_evaluations[:4]])
                metric_block = f"<p>关键数值与阈值判定如下：</p><ul>{metric_lines}</ul>"
            paragraphs: list[str] = []
            paragraphs.extend([f"<p>依据：{x}</p>" for x in self._split_readable_paragraph(evidence_sentence)])
            if metric_block:
                paragraphs.append(metric_block)
            paragraphs.extend([f"<p>{x}</p>" for x in self._split_readable_paragraph(gate_text)])
            paragraphs.extend([f"<p>{x}</p>" for x in self._split_readable_paragraph(rule_sentence)])
            paragraphs.extend([f"<p>{x}</p>" for x in self._split_readable_paragraph(conflict_sentence)])
            paragraphs.extend([f"<p>{x}</p>" for x in self._split_readable_paragraph(boundary_sentence)])
            paragraphs.extend([f"<p>{x}</p>" for x in self._split_readable_paragraph(evidence_binding_sentence)])
            paragraphs.extend([f"<p>{x}</p>" for x in self._split_readable_paragraph(next_sentence + extra_conflict)])
            return "\n".join(paragraphs)
        if missing:
            return "\n".join(
                [
                    f"<p>针对“{premise}”的分析尚未形成足够证据，关键缺失产物为 {', '.join(missing)}。</p>",
                    f"<p>{gate_text}</p>",
                    (
                        f"<p>证据来源：{'、'.join([str(x) for x in evidence_sources[:4]])}</p>"
                        if evidence_sources
                        else "<p>证据来源：未提供结构化来源，当前结论仅供排查参考。</p>"
                    ),
                    "<p>当前无法给出可靠判断，建议优先补齐执行链路后再评估。</p>",
                ]
            )
        return "\n".join(
            [
                f"<p>针对“{premise}”未提取到可自动解释的定量结果。</p>",
                f"<p>{gate_text}</p>",
                (
                    f"<p>证据来源：{'、'.join([str(x) for x in evidence_sources[:4]])}</p>"
                    if evidence_sources
                    else "<p>证据来源：未提供结构化来源。</p>"
                ),
                "<p>请结合 result 目录中的原始产物进行人工复核。</p>",
            ]
        )

    def _gate_evidence_alignment_notes(self, gate_entry: dict[str, Any], evidence_entry: dict[str, Any]) -> list[str]:
        notes: list[str] = []
        if not gate_entry:
            return notes
        quant_metrics = evidence_entry.get("quant_metrics", []) if isinstance(evidence_entry.get("quant_metrics"), list) else []
        quant_names = {str(item.get("name", "")).strip().lower() for item in quant_metrics if isinstance(item, dict)}
        gate_rule_type = str(gate_entry.get("gate_rule_type", "")).strip().lower()
        checks = gate_entry.get("checks", {}) if isinstance(gate_entry.get("checks"), dict) else {}
        check_details = gate_entry.get("check_details", {}) if isinstance(gate_entry.get("check_details"), dict) else {}
        missing_detail_keys = [k for k in checks.keys() if k not in check_details]
        if missing_detail_keys:
            notes.append("以下检查缺少 check_details 证据绑定：" + "、".join(missing_detail_keys))

        reason_gate = str(gate_entry.get("reason_code", "")).strip()
        reason_evidence = str(evidence_entry.get("reason_code", "")).strip()
        if reason_gate and reason_evidence and reason_gate != reason_evidence:
            notes.append(f"reason_code 不一致：gate={reason_gate}，evidence_pack={reason_evidence}。")

        if gate_rule_type == "predictive_performance":
            need_one = {"centroid_accuracy", "auc"}
            if not (need_one & quant_names):
                notes.append("预测性能路径缺少主性能指标（centroid_accuracy 或 auc）。")
            if "cv_mean_accuracy" not in quant_names:
                notes.append("预测性能路径缺少交叉验证性能指标（cv_mean_accuracy）。")
        elif gate_rule_type == "significance_and_effect":
            if not ({"significant_p_lt_0_05", "q_lt_0_05"} & quant_names):
                notes.append("差异路径缺少显著性计数指标（significant_p_lt_0_05 或 q_lt_0_05）。")
            effect_metrics = evidence_entry.get("effect_metrics", []) if isinstance(evidence_entry.get("effect_metrics"), list) else []
            if not effect_metrics:
                notes.append("差异路径缺少效应量证据（effect_metrics 为空）。")
        return notes

    def _chart_table_conflict_notes(self, session_root: Path | None) -> list[str]:
        notes: list[str] = []
        if not session_root:
            return notes
        top_path = session_root / "result" / "top_features.json"
        stats_path = session_root / "result" / "stats_results.json"
        if not (top_path.exists() and stats_path.exists()):
            return notes
        top_payload = self._load_json(top_path)
        stats_payload = self._load_json(stats_path)
        top_names: list[str] = []
        if isinstance(top_payload, list):
            for row in top_payload[:20]:
                if isinstance(row, dict) and row.get("feature"):
                    top_names.append(str(row.get("feature")))
        stats_names: set[str] = set()
        if isinstance(stats_payload, list):
            for row in stats_payload:
                if isinstance(row, dict) and row.get("feature"):
                    stats_names.add(str(row.get("feature")))
        elif isinstance(stats_payload, dict):
            rows = stats_payload.get("rows", [])
            if isinstance(rows, list):
                for row in rows:
                    if isinstance(row, dict) and row.get("feature"):
                        stats_names.add(str(row.get("feature")))
        if top_names and stats_names:
            missing = [x for x in top_names if x not in stats_names]
            if missing:
                notes.append("图表-表格一致性告警：top_features 中部分特征未在 stats_results 出现：" + "、".join(missing[:8]))
        return notes

    def _render_gate_readable_block(self, gate_entry: dict[str, Any]) -> list[str]:
        lines: list[str] = []
        if not gate_entry:
            return lines
        rule_type = str(gate_entry.get("gate_rule_type", "")).strip()
        gate_status = str(gate_entry.get("gate_status", "")).strip().lower()
        lines.append(f"- 判定规则（原规则类型）：{gate_rule_type_sentence(rule_type)}")
        lines.append(f"- 当前判定状态：{gate_status_sentence(gate_status)}")

        checks = gate_entry.get("checks", {}) if isinstance(gate_entry.get("checks"), dict) else {}
        if checks:
            lines.append("- 检查结果：")
            lines.append("<ul>")
            for key, value in checks.items():
                status_text = "通过" if value is True else "未通过"
                lines.append(f"<li>{failed_check_sentence(key)} 当前结果：{status_text}。</li>")
            lines.append("</ul>")

        failed_checks = gate_entry.get("failed_checks", []) if isinstance(gate_entry.get("failed_checks"), list) else []
        unknown_checks: list[str] = []
        if failed_checks:
            lines.append("- 失败项重点说明：")
            for item in failed_checks[:6]:
                lines.append(f"  - {failed_check_sentence(str(item))}")
                if not has_failed_check_explanation(str(item)):
                    unknown_checks.append(str(item))
                review_steps = failed_check_review_steps(str(item))
                for step in review_steps[:2]:
                    lines.append(f"    - 建议复核：{step}")

        reason_code = str(gate_entry.get("reason_code", "")).strip()
        reason_text = reason_code_sentence(reason_code)
        if reason_text:
            lines.append(f"- 原因码解释：{reason_text}")
        if reason_code and not has_reason_code_explanation(reason_code):
            lines.append(f"- 解释覆盖告警：当前原因码缺少预定义中文映射，请补充字典。（{reason_code}）")
        if unknown_checks:
            lines.append(
                "- 解释覆盖告警：以下失败检查尚未配置标准中文释义，请补充映射："
                + "、".join(unknown_checks)
                + "。"
            )

        recovery_action = str(gate_entry.get("recovery_action", "")).strip()
        if recovery_action:
            lines.append(f"- 建议动作：{recovery_action_sentence(recovery_action)}")
        return lines

    def _render_cross_hypothesis_discussion(self, outcomes: list[dict[str, Any]]) -> str:
        if not outcomes:
            return "当前运行未形成可汇总的假设级结果。"
        total = len(outcomes)
        complete = sum(1 for x in outcomes if not x.get("missing"))
        partial = total - complete
        gate_pass = sum(1 for x in outcomes if str(x.get("gate_status", "")).lower() == "pass")
        gate_partial = sum(1 for x in outcomes if str(x.get("gate_status", "")).lower() == "partial")
        gate_fail = sum(1 for x in outcomes if str(x.get("gate_status", "")).lower() == "fail")
        conflict_count = sum(1 for x in outcomes if int(x.get("conflict_count", 0)) > 0)
        lines: list[str] = []
        lines.append(
            f"本次共评估 {total} 条核心假设，其中 {complete} 条在当前产物范围内形成了相对完整的证据链，"
            f"{partial} 条仍存在不同程度的证据缺口。"
        )
        lines.append(
            f"从判定状态看：通过 {gate_pass} 条、部分通过 {gate_partial} 条、未通过 {gate_fail} 条；"
            f"检测到显式指标冲突的假设有 {conflict_count} 条。"
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
        supported = [
            x
            for x in outcomes
            if x.get("details")
            and not x.get("missing")
            and str(x.get("gate_status", "")).lower() == "pass"
            and int(x.get("conflict_count", 0)) == 0
        ]
        uncertain = [
            x
            for x in outcomes
            if x.get("missing")
            or str(x.get("gate_status", "")).lower() in {"partial", "fail"}
            or int(x.get("conflict_count", 0)) > 0
        ]
        lines: list[str] = []
        if supported:
            ids = "、".join([x["id"] for x in supported])
            lines.append(f"结论上，{ids} 在当前数据与流程下形成了较完整证据，可作为后续解释与验证工作的优先基础。")
        if uncertain:
            ids = "、".join([x["id"] for x in uncertain])
            lines.append(f"同时，{ids} 仍处于证据不充分或存在冲突状态，暂不建议输出强结论。")
        lines.append("建议后续工作按“补齐缺失产物 → 交叉验证/对照验证 → 复现实验”顺序推进，并将失败路径与修复过程持续记录到报告附件。")
        return "\n\n".join(lines)

    def _extract_hypothesis_sections(self, report_text: str, hypothesis_ids: list[str]) -> dict[str, str]:
        section_map: dict[str, str] = {}
        if not report_text:
            return section_map
        ids = [str(x).upper() for x in hypothesis_ids if str(x).strip()]
        for idx, hyp_id in enumerate(ids):
            title_pattern = re.compile(rf"^###\s+{re.escape(hyp_id)}\b.*$", re.MULTILINE)
            match = title_pattern.search(report_text)
            if not match:
                continue
            start = match.end()
            end = len(report_text)
            next_markers: list[int] = []
            if idx + 1 < len(ids):
                next_pattern = re.compile(rf"^###\s+{re.escape(ids[idx+1])}\b.*$", re.MULTILINE)
                n = next_pattern.search(report_text, pos=start)
                if n:
                    next_markers.append(n.start())
            major_heading = re.compile(r"^##\s+.+$", re.MULTILINE).search(report_text, pos=start)
            if major_heading:
                next_markers.append(major_heading.start())
            if next_markers:
                end = min(next_markers)
            section_map[hyp_id] = report_text[start:end]
        return section_map

    def _build_report_substance_audit(self, outcomes: list[dict[str, Any]], report_text: str) -> dict[str, Any]:
        total = len(outcomes)
        numeric_sections = 0
        traceable_sections = 0
        actionable_sections = 0
        basis_sections = 0
        conflict_sections = 0
        boundary_sections = 0
        next_step_sections = 0
        hypothesis_ids = [str(item.get("id", "")).upper() for item in outcomes if str(item.get("id", "")).strip()]
        section_map = self._extract_hypothesis_sections(report_text, hypothesis_ids)
        missing_elements_by_hypothesis: list[dict[str, Any]] = []
        for item in outcomes:
            hid = str(item.get("id", "")).upper()
            section_text = section_map.get(hid, "")
            detail_text = " ".join([str(x) for x in item.get("details", [])])
            quant = item.get("quant_metrics", {}) if isinstance(item.get("quant_metrics"), dict) else {}
            missing = item.get("missing", []) if isinstance(item.get("missing"), list) else []
            if quant and re.search(r"\d", detail_text + " " + " ".join([str(v) for v in quant.values()])):
                numeric_sections += 1
            evidence_sources = item.get("evidence_sources", []) if isinstance(item.get("evidence_sources"), list) else []
            if quant and evidence_sources:
                traceable_sections += 1
            if missing or ("下一步：" in section_text):
                actionable_sections += 1
            has_basis = "依据：" in section_text
            has_conflict = "反证/冲突：" in section_text
            has_boundary = "边界：" in section_text
            has_next = "下一步：" in section_text
            if has_basis:
                basis_sections += 1
            if has_conflict:
                conflict_sections += 1
            if has_boundary:
                boundary_sections += 1
            if has_next:
                next_step_sections += 1
            missing_keys: list[str] = []
            if not has_basis:
                missing_keys.append("basis")
            if not has_conflict:
                missing_keys.append("conflict")
            if not has_boundary:
                missing_keys.append("boundary")
            if not has_next:
                missing_keys.append("next_step")
            if not evidence_sources:
                missing_keys.append("evidence_binding")
            if missing_keys:
                missing_elements_by_hypothesis.append({"hypothesis_id": hid or "UNKNOWN", "missing_elements": missing_keys})
        numeric_density = round((numeric_sections / total), 4) if total else 0.0
        traceable_density = round((traceable_sections / total), 4) if total else 0.0
        actionable_density = round((actionable_sections / total), 4) if total else 0.0
        basis_density = round((basis_sections / total), 4) if total else 0.0
        conflict_density = round((conflict_sections / total), 4) if total else 0.0
        boundary_density = round((boundary_sections / total), 4) if total else 0.0
        next_step_density = round((next_step_sections / total), 4) if total else 0.0
        fluff_phrases = ["需要进一步分析", "建议后续研究", "可能存在", "仍需验证"]
        fluff_hits = sum(report_text.count(p) for p in fluff_phrases)
        key_metrics_count = report_text.count("取值解读：")
        unknown_raw_hits = report_text.count("阈值未定义，判定=unknown，方向解释=unknown")
        raw_gate_tokens = ["gate_rule_type=", "gate_status=", "failed_checks=", "reason_code="]
        raw_gate_hits = sum(report_text.count(token) for token in raw_gate_tokens)
        gate_readable_hits = (
            report_text.count("门槛类型：")
            + report_text.count("当前状态：")
            + report_text.count("判定规则（原规则类型）：")
            + report_text.count("当前判定状态：")
        )
        gate_exposure_rate = round(raw_gate_hits / max(raw_gate_hits + gate_readable_hits, 1), 4)
        return {
            "hypothesis_count": total,
            "basis_coverage": basis_density,
            "conflict_coverage": conflict_density,
            "boundary_coverage": boundary_density,
            "next_step_coverage": next_step_density,
            "numeric_sentence_coverage": numeric_density,
            "evidence_binding_coverage": traceable_density,
            "actionable_next_step_coverage": actionable_density,
            "missing_elements_by_hypothesis": missing_elements_by_hypothesis,
            "template_fluff_hits": fluff_hits,
            "fluff_phrases": fluff_phrases,
            "key_metric_interpretation_hits": key_metrics_count,
            "unknown_raw_string_hits": unknown_raw_hits,
            "gate_raw_token_hits": raw_gate_hits,
            "gate_readable_block_hits": gate_readable_hits,
            "gate_raw_exposure_rate": gate_exposure_rate,
        }

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
        feature_dict = self._load_feature_dict(session_root)
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
        plan_markdown = self._load_plan_markdown(session_root)
        lines.append("## 研究目标与原始假设")
        overview = self._render_plan_hypothesis_overview(plan_json)
        if overview:
            lines.append("以下为结构化假设总览：")
            lines.append(overview)
        elif hypotheses_md:
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
        lines.extend(self._render_global_process_summary(process_md))
        lines.append("")

        # Section 3: per-hypothesis validation sections
        lines.append("## 假设验证与结果分析")
        hypothesis_results = self._load_hypothesis_results(session_root)
        hypothesis_evidence = self._load_hypothesis_evidence(session_root)
        hypothesis_contrast = self._load_hypothesis_contrast(session_root)
        hypothesis_gate = self._load_hypothesis_gate(session_root)
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
                planned_hyp_text = hyp_text
                plan_steps = hyp.get("validation_plan_steps") or hyp.get("steps") or []
                if not plan_steps:
                    plan_steps = self._extract_hypothesis_steps_from_plan_markdown(plan_markdown, hyp_id)
                expected_artifacts = hyp.get("expected_artifacts") or hyp.get("artifacts") or []
                run_entry = self._hypothesis_result_entry(hyp_id, hypothesis_results)
                evidence_entry = self._hypothesis_evidence_entry(hyp_id, hypothesis_evidence)
                contrast_entry = self._hypothesis_contrast_entry(hyp_id, hypothesis_contrast)
                gate_entry = self._hypothesis_gate_entry(hyp_id, hypothesis_gate)
                step_map = run_entry.get("steps", {}) if isinstance(run_entry, dict) else {}
                run_hypothesis = str(run_entry.get("hypothesis", "")) if isinstance(run_entry, dict) else ""
                executed_title = self._extract_title_from_run_hypothesis(run_hypothesis, hyp_id)
                if executed_title:
                    hyp_title = executed_title
                evidence_claim = str(evidence_entry.get("claim", "")).strip() if isinstance(evidence_entry, dict) else ""
                gate_rule = str(gate_entry.get("gate_rule_type", "")).strip() if isinstance(gate_entry, dict) else ""
                executed_focus = self._focus_from_gate_rule(gate_rule)
                plan_md_title = self._extract_hypothesis_title_from_plan_markdown(plan_markdown, hyp_id)
                mismatch_note = ""
                if evidence_claim:
                    if hyp_text and not self._text_matches_focus(hyp_text, executed_focus):
                        mismatch_note = (
                            "计划假设文本与执行证据类型存在偏差，当前小节已按实际执行结果解释。"
                        )
                        hyp_text = evidence_claim
                        plan_steps = self._execution_steps_from_step_map(
                            step_map if isinstance(step_map, dict) else {},
                            gate_rule,
                        )
                    elif not hyp_text:
                        hyp_text = evidence_claim
                missing = run_entry.get("missing", []) if isinstance(run_entry, dict) else []
                quant_metrics = (
                    evidence_entry.get("quant_metrics_map")
                    if isinstance(evidence_entry.get("quant_metrics_map"), dict)
                    else evidence_entry.get("quant_metrics", {}) if isinstance(evidence_entry, dict) else {}
                )
                if not quant_metrics or len(quant_metrics) < 2:
                    if "quant_metrics_missing" not in missing:
                        missing = list(missing) + ["quant_metrics_missing"]
                    if len(quant_metrics) < 2 and "insufficient_quant_metric_count" not in missing:
                        missing = list(missing) + ["insufficient_quant_metric_count"]
                evidence_sources = (
                    evidence_entry.get("evidence_sources", [])
                    if isinstance(evidence_entry, dict) and isinstance(evidence_entry.get("evidence_sources"), list)
                    else []
                )
                if not evidence_sources:
                    if "evidence_binding_missing" not in missing:
                        missing = list(missing) + ["evidence_binding_missing"]
                predictive_missing = self._predictive_completeness_missing(
                    gate_entry if isinstance(gate_entry, dict) else {},
                    evidence_entry if isinstance(evidence_entry, dict) else {},
                    step_map if isinstance(step_map, dict) else {},
                    contrast_entry if isinstance(contrast_entry, dict) else {},
                )
                for item in predictive_missing:
                    if item not in missing:
                        missing = list(missing) + [item]
                lines.append(f"### {hyp_id} {hyp_title}")
                lines.append("#### 研究问题与假设")
                lines.extend(
                    self._render_hypothesis_problem_block(
                        hyp_title=hyp_title,
                        effective_hypothesis=hyp_text,
                        mismatch_note=mismatch_note,
                        planned_title=plan_md_title,
                        planned_hypothesis=planned_hyp_text,
                        executed_hypothesis=run_hypothesis,
                    )
                )
                lines.append("")
                if (not isinstance(plan_steps, list) or not plan_steps) and isinstance(step_map, dict) and step_map:
                    plan_steps = self._execution_steps_from_step_map(step_map, gate_rule)
                lines.append("#### 方法与前置条件检查")
                lines.extend(self._render_method_steps(plan_steps if isinstance(plan_steps, list) else [], step_map if isinstance(step_map, dict) else {}))
                if gate_entry:
                    checks = gate_entry.get("checks", {}) if isinstance(gate_entry.get("checks"), dict) else {}
                    if checks:
                        lines.append("")
                        lines.append("前置条件检查（执行可用性）：")
                        lines.append("<ul>")
                        for key in ["has_dual_path_status", "path_consistency"]:
                            if key in checks:
                                lines.append(f"<li>{self._gate_check_label(key)}：{self._bool_zh(checks.get(key))}</li>")
                        lines.append("</ul>")
                        lines.append("")
                        lines.append("证据判定检查（证据充分性）：")
                        lines.append("<ul>")
                        for key, value in checks.items():
                            if key in {"has_dual_path_status", "path_consistency"}:
                                continue
                            lines.append(f"<li>{self._gate_check_label(key)}：{self._bool_zh(value)}</li>")
                        lines.append("</ul>")
                lines.append("")
                lines.append("#### 执行事实（产物与状态）")
                if step_map:
                    lines.append("<ul>")
                    for step_name, payload in step_map.items():
                        status = payload.get("status") if isinstance(payload, dict) else ""
                        output = payload.get("output") if isinstance(payload, dict) else ""
                        lines.append(f"<li><strong>{step_name}</strong>：状态={status}；输出={output}</li>")
                    lines.append("</ul>")
                else:
                    lines.append("未读取到执行步骤明细。")
                if expected_artifacts:
                    lines.append("计划产物：")
                    lines.append("<ul>")
                    for x in expected_artifacts:
                        lines.append(f"<li>{x}</li>")
                    lines.append("</ul>")
                if missing:
                    lines.append("缺失产物：")
                    lines.append("<ul>")
                    for x in missing:
                        lines.append(f"<li>{self._missing_item_label(str(x))}</li>")
                    lines.append("</ul>")
                else:
                    lines.append("缺失产物：无。")
                lines.append("")
                lines.append("#### 定量结果（指标与证据）")
                quant_metric_rows = (
                    evidence_entry.get("quant_metrics", [])
                    if isinstance(evidence_entry, dict) and isinstance(evidence_entry.get("quant_metrics"), list)
                    else []
                )
                if quant_metric_rows:
                    for idx, metric in enumerate(quant_metric_rows[:12]):
                        if not isinstance(metric, dict):
                            continue
                        lines.append(f"- {metric_narrative(metric, idx)}")
                elif quant_metrics:
                    lines.append("<ul>")
                    for key, value in quant_metrics.items():
                        lines.append(f"<li>{key}：{value}</li>")
                    lines.append("</ul>")
                else:
                    lines.append("- 无可用定量指标。")
                lines.append("")
                lines.append("#### 结果解释（引用具体数值）")
                details = self._evidence_detail_lines(evidence_entry if isinstance(evidence_entry, dict) else {}, feature_dict)
                quant_evaluations = self._quantitative_judgement_lines(
                    evidence_entry if isinstance(evidence_entry, dict) else {},
                    idx,
                )
                lines.append(
                    self._render_result_analysis_paragraph(
                        hyp_id,
                        hyp_text,
                        details,
                        missing,
                        quant_metrics,
                        (
                            "validated"
                            if str(gate_entry.get("gate_status", "")).lower() == "pass"
                            else "inconclusive"
                        )
                        if isinstance(gate_entry, dict) and gate_entry
                        else str(contrast_entry.get("status", "inconclusive")) if isinstance(contrast_entry, dict) else "inconclusive",
                        quant_evaluations,
                        gate_entry if isinstance(gate_entry, dict) else {},
                        contrast_entry if isinstance(contrast_entry, dict) else {},
                        evidence_sources,
                    )
                )
                lines.append("")
                lines.append("#### 一致性与冲突解释（A/B 路径）")
                if gate_entry:
                    lines.extend(self._render_gate_readable_block(gate_entry if isinstance(gate_entry, dict) else {}))
                    alignment_notes = self._gate_evidence_alignment_notes(
                        gate_entry if isinstance(gate_entry, dict) else {},
                        evidence_entry if isinstance(evidence_entry, dict) else {},
                    )
                    if alignment_notes:
                        lines.append("- 证据绑定检查：")
                        for note in alignment_notes:
                            lines.append(f"  - {note}")
                    else:
                        lines.append("- 证据绑定检查：核心 gate 字段与 evidence pack 关键字段已对齐。")
                    if hyp_id.upper() == "H1":
                        chart_notes = self._chart_table_conflict_notes(session_root)
                        if chart_notes:
                            lines.append("- 图表/表格一致性检查：")
                            for note in chart_notes:
                                lines.append(f"  - {note}")
                    if gate_entry.get("calibration_profile"):
                        lines.append(f"- 校准档位：{gate_entry.get('calibration_profile')}")
                    recovery_plan = gate_entry.get("recovery_plan", []) if isinstance(gate_entry.get("recovery_plan"), list) else []
                    if recovery_plan:
                        lines.append("- 恢复计划：")
                        for step in recovery_plan[:4]:
                            if not isinstance(step, dict):
                                continue
                            lines.append(
                                f"  - [{step.get('priority','P2')}] {step.get('action','')} | 预期产物={','.join([str(x) for x in step.get('expected_artifacts', [])])}"
                            )
                    decision_evidence = gate_entry.get("decision_evidence", []) if isinstance(gate_entry.get("decision_evidence"), list) else []
                    if decision_evidence:
                        lines.append("- 判定依据：")
                        lines.append("<ul>")
                        for item in decision_evidence[:6]:
                            if not isinstance(item, dict):
                                continue
                            check_name = failed_check_sentence(str(item.get("check", "")))
                            lines.append(
                                f"<li>{check_name} 当前结果：{self._bool_zh(item.get('passed'))}；细节={json.dumps(item.get('detail', {}), ensure_ascii=False)}</li>"
                            )
                        lines.append("</ul>")
                lines.append(
                    f"分析来源：自动提取证据 + 规则化解释。"
                    f"{'（定量指标不足，已降级为不确定结论）' if not quant_metrics else ''}"
                )
                lines.append("")
                if contrast_entry:
                    pa = contrast_entry.get("path_a", {}) if isinstance(contrast_entry, dict) else {}
                    pb = contrast_entry.get("path_b", {}) if isinstance(contrast_entry, dict) else {}
                    lines.append("路径对照（A/B）：")
                    lines.append("<table border=1 cellpadding=4 cellspacing=0>")
                    lines.append("<thead><tr><th>验证路径</th><th>执行状态</th><th>指标摘要</th></tr></thead><tbody>")
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
                else:
                    lines.append("未读取到 A/B 路径对照信息。")
                lines.append("")
                lines.append("#### 局限性与下一步")
                if missing:
                    lines.append(
                        f"当前假设存在缺口（{', '.join([str(x) for x in missing])}），"
                        "应优先补齐缺失产物后再进行复核。"
                    )
                elif gate_entry and str(gate_entry.get("gate_status", "")).lower() != "pass":
                    lines.append("当前证据判定未通过，建议按恢复动作补充实验或替代路径后重试。")
                else:
                    lines.append("当前证据链相对完整，建议进入跨假设综合与外部复核阶段。")
                if str(gate_entry.get("gate_rule_type", "")).lower() == "predictive_performance" and not missing:
                    lines.append("可复现实验摘要：已满足预测类假设的最小信息要求（模型、评估设置、主性能指标与冲突说明齐备）。")
                lines.append("")
                if isinstance(evidence_entry, dict):
                    sources = evidence_entry.get("evidence_sources", []) or []
                    if sources:
                        lines.append("**证据摘录（默认折叠）**：")
                        for src in sources[:4]:
                            rel = str(src)
                            lines.append(f"<details><summary>来源：<code>{rel}</code></summary>")
                            snippet = self._extract_evidence_snippet(session_root, rel)
                            if snippet:
                                lines.append("<pre>")
                                lines.append(snippet[:1200].replace('<', '&lt;').replace('>', '&gt;'))
                                lines.append("</pre>")
                            else:
                                lines.append("<div>暂无可提取内容。</div>")
                            lines.append("</details>")
                        lines.append("")
                outcome_conflict_input: list[dict[str, Any]] = []
                if isinstance(quant_metrics, dict):
                    for k, v in quant_metrics.items():
                        outcome_conflict_input.append({"name": k, "value": v})
                hypothesis_outcomes.append(
                    {
                        "id": hyp_id,
                        "title": hyp_title,
                        "missing": missing,
                        "details": details,
                        "quant_metrics": quant_metrics,
                        "gate_status": str(gate_entry.get("gate_status", "")).lower() if isinstance(gate_entry, dict) else "",
                        "conflict_count": len(detect_metric_conflicts_detailed(outcome_conflict_input)),
                        "evidence_sources": (
                            evidence_entry.get("evidence_sources", [])
                            if isinstance(evidence_entry, dict) and isinstance(evidence_entry.get("evidence_sources"), list)
                            else []
                        ),
                    }
                )
                bound_visuals = self._hypothesis_bound_visuals(hyp_id, visuals, binding_map)
                if bound_visuals:
                    lines.append("**图表与解释**：")
                    lines.append(
                        self._build_visual_block(
                            bound_visuals,
                            session_root,
                            binding_map,
                            feature_dict,
                            render_manifest,
                        )
                    )
                    lines.append("")
                    used_visuals.update(v.get("relative_path", "") for v in bound_visuals)
        else:
            lines.append("未检测到可追溯假设结构，已禁用自由文本直出。")
            lines.append("请补充 `plan/analysis_plan.json` 的 hypotheses 与 validation_paths，再重新装配报告。")
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
        completion_block = self._render_completion_validation(session_root)
        matrix_block = self._render_hypothesis_matrix(session_root)
        coverage_block = self._render_coverage_report(session_root)
        if failure_block:
            lines.append(failure_block.replace("## 验证失败记录\n", ""))
            lines.append("")
        if completion_block:
            lines.append(completion_block.replace("## 完成态校验\n", ""))
            lines.append("")
        if quality_block:
            lines.append(quality_block.replace("## 质量规则未达标\n", ""))
            lines.append("")
        if matrix_block:
            lines.append(matrix_block)
            lines.append("")
        if coverage_block:
            lines.append(coverage_block.replace("## 覆盖策略与遗漏项\n", ""))
            lines.append("")

        # Section 7: table previews
        if tables:
            table_blocks = self._table_preview_blocks(tables, session_root, feature_dict)
            if table_blocks:
                lines.append("## 关键数据表")
                lines.extend(table_blocks)
                for item in tables:
                    if item.get("name", "") in {"top_features.json", "stats_summary.json", "model_eval.json"}:
                        used_tables.add(item.get("relative_path", ""))
                lines.append("")

        # Section 8: appendix (non-duplicated)
        lines.append(self._render_appendix(document_manifest, used_visuals, used_tables, session_root, binding_map))
        lines.append("")
        if session_root:
            meta_dir = session_root / "meta"
            meta_dir.mkdir(parents=True, exist_ok=True)
            full_report = "\n".join(lines)
            substance_audit = self._build_report_substance_audit(hypothesis_outcomes, full_report)
            (meta_dir / "render_manifest.json").write_text(
                json.dumps({"resources": render_manifest}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (meta_dir / "report_substance_audit.json").write_text(
                json.dumps(substance_audit, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        lines.append(self._preview_script())
        lines.append("")
        return "\n".join(lines).strip()
