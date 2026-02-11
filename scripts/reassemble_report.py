#!/usr/bin/env python3
"""
Reassemble report HTML from existing artifacts without running full pipeline.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.reporting.assembler import ReportAssembler, normalize_report_payload
from src.core.reporting.exporter import export_report
from src.core.reporting.templates import template_from_config
from src.core.orchestration.document_manager import DocumentManager


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _find_outline(session_dir: Path) -> str:
    candidates = [
        session_dir / "report" / "report_outline.md",
        session_dir / "artifacts" / "report_outline.md",
    ]
    for candidate in candidates:
        if candidate.exists():
            return _read_text(candidate)
    # fallback: search any report_outline.md in workspace
    for candidate in session_dir.rglob("report_outline.md"):
        return _read_text(candidate)
    return ""


def _find_analysis(session_dir: Path) -> str:
    candidates = [
        session_dir / "result" / "analysis_results.md",
    ]
    for candidate in candidates:
        if candidate.exists():
            return _read_text(candidate)
    # fallback: search
    for candidate in session_dir.rglob("analysis_results.md"):
        return _read_text(candidate)
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Reassemble report from existing artifacts")
    parser.add_argument("--session-dir", required=True, help="Path to session workspace")
    parser.add_argument("--language", default="zh")
    parser.add_argument("--report-format", default="html")
    parser.add_argument("--export-mode", default="html_print")
    parser.add_argument("--output-name", default="report_v2")
    args = parser.parse_args()

    session_dir = Path(args.session_dir)
    if not session_dir.exists():
        raise SystemExit(f"Session dir not found: {session_dir}")

    outline = _find_outline(session_dir)
    analysis_md = _find_analysis(session_dir)
    doc_manager = DocumentManager(session_dir)
    manifest = doc_manager.manifest()
    assembler = ReportAssembler(language=args.language)
    report_payload = normalize_report_payload({})
    report = assembler.assemble(
        outline=outline,
        analysis_md=analysis_md,
        document_manifest=manifest,
        report_payload=report_payload,
        execution_warning="",
    )
    report_path = export_report(
        report,
        output_dir=session_dir / "report",
        report_format=args.report_format,
        export_mode=args.export_mode,
        template=template_from_config(args.language),
        base_name=args.output_name,
    )
    print(f"Reassembled report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
