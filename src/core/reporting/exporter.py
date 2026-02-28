from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import markdown as md
from docx import Document

try:
    from weasyprint import HTML
except Exception:  # pragma: no cover - optional runtime dependency
    HTML = None

from .templates import DEFAULT_TEMPLATE, ReportTemplate


_MD_EXTENSIONS = ["extra", "tables", "fenced_code", "sane_lists"]


class ReportExporter:
    """报告导出器"""
    def __init__(self):
        pass
    
    def export(self, content, format="html", **kwargs):
        """导出报告"""
        return export_report(content, format=format, **kwargs)


def _wrap_html(body: str, template: ReportTemplate) -> str:
    logo_html = (
        f"<img src='{template.logo_url}' style='height:48px;'/>"
        if template.logo_url
        else ""
    )
    toc_html = "<div id='toc'></div>" if template.include_toc else ""
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'/>
<title>{template.title}</title>
<style>
body {{ font-family: {template.font_family}; margin: 40px; }}
header {{ border-bottom: 1px solid #ddd; margin-bottom: 24px; padding-bottom: 12px; }}
footer {{ border-top: 1px solid #ddd; margin-top: 24px; padding-top: 12px; color: #666; }}
</style>
</head>
<body>
<header>
  {logo_html}
  <h1>{template.title}</h1>
  <h3>{template.subtitle}</h3>
  <div>{template.author}</div>
</header>
{toc_html}
{body}
<footer>{template.footer}</footer>
</body>
</html>"""


def _strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html)


def export_report(
    content: str,
    output_dir: str | Path,
    report_format: str,
    export_mode: str,
    template: Optional[ReportTemplate] = None,
    base_name: str = "report",
) -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    template = template or DEFAULT_TEMPLATE

    fmt = report_format.lower()
    mode = export_mode.lower()

    if fmt == "html":
        if "<html" in content.lower():
            html_body = content
        else:
            has_markdown_structure = bool(
                re.search(r"(^|\n)\s{0,3}(#{1,6}\s+|[-*]\s+|\d+\.\s+)", content)
            )
            if mode in {"html_convert", "html_print"} or has_markdown_structure:
                html_body = _wrap_html(md.markdown(content, extensions=_MD_EXTENSIONS), template)
            else:
                html_body = _wrap_html(content, template)
        path = out_dir / f"{base_name}.html"
        path.write_text(html_body, encoding="utf-8")
        return path

    if fmt == "markdown":
        path = out_dir / f"{base_name}.md"
        path.write_text(content, encoding="utf-8")
        return path

    if fmt in {"pdf", "docx"}:
        # Prefer HTML conversion for export modes based on HTML
        if mode in {"html_convert", "html_print"}:
            html_body = content
            if "<html" not in content.lower():
                html_body = _wrap_html(md.markdown(content, extensions=_MD_EXTENSIONS), template)
            html_path = out_dir / f"{base_name}.html"
            html_path.write_text(html_body, encoding="utf-8")

            if fmt == "pdf":
                pdf_path = out_dir / f"{base_name}.pdf"
                if HTML is not None:
                    HTML(string=html_body).write_pdf(str(pdf_path))
                    return pdf_path
                pdf_path.write_text("PDF export unavailable (weasyprint missing).", encoding="utf-8")
                return pdf_path

            # DOCX
            docx_path = out_dir / f"{base_name}.docx"
            doc = Document()
            doc.add_paragraph(_strip_html(html_body))
            doc.save(str(docx_path))
            return docx_path

        # Academic redraw or other modes fallback: save as txt with extension
        path = out_dir / f"{base_name}.{fmt}"
        path.write_text(content, encoding="utf-8")
        return path

    # Default fallback
    path = out_dir / f"{base_name}.txt"
    path.write_text(content, encoding="utf-8")
    return path
