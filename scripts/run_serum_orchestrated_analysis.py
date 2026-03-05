#!/usr/bin/env python3
"""
Run LLM-orchestrated analysis for the serum dataset using the orchestration graph.
This script targets the full hypothesis -> codegen -> execution -> analysis -> report flow.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import threading
import warnings
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*swig.*")

from src.api.config import (
    WORKSPACE_BASE_DIR,
    REPORT_EXPORT_MODE,
    REPORT_FORMAT,
    REPORT_LANGUAGE,
    MAX_RECURSION_DEPTH,
    API_BASE,
)
from src.core.orchestration.runner import run_orchestrated_docs_analysis
from src.core.orchestration.llm import LLMClient


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def _check_llm_connection(strict: bool = False) -> bool:
    try:
        client = LLMClient()
        client.chat(
            [
                {"role": "system", "content": "You are a connectivity check."},
                {"role": "user", "content": "Reply with OK."},
            ],
            max_tokens=1,
        )
        return True
    except Exception as exc:
        msg = f"LLM connectivity check failed for {API_BASE}: {exc}"
        if strict:
            raise SystemExit(msg) from exc
        print(f"⚠️ {msg}")
        print("⚠️ Continue in fallback mode: structured deterministic paths will be used where possible.")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM-orchestrated serum analysis runner.")
    parser.add_argument(
        "--data-file",
        default="data/examples/serum/Normal_EP_serum_data.xlsx",
        help="Input dataset path",
    )
    parser.add_argument("--output-dir", default="outputs/serum_orchestrated", help="Output directory")
    parser.add_argument("--max-depth", type=int, default=None, help="Max recursion depth")
    parser.add_argument("--report-format", default=REPORT_FORMAT, help="Report format")
    parser.add_argument("--report-language", default=REPORT_LANGUAGE, help="Report language")
    parser.add_argument("--report-export-mode", default=REPORT_EXPORT_MODE, help="Report export mode")
    parser.add_argument(
        "--analysis-goal",
        default="对血清数据进行全面分析，提出假设并验证，生成完整报告与可视化。",
        help="LLM analysis goal prompt",
    )
    parser.add_argument(
        "--no-print-steps",
        action="store_true",
        default=True,
        help="Print orchestrator node progress as it runs",
    )
    parser.add_argument(
        "--strict-llm-check",
        action="store_true",
        default=False,
        help="Exit immediately when startup LLM connectivity check fails",
    )
    parser.add_argument(
        "--workspace-dir",
        default=None,
        help="Workspace base directory for session artifacts (defaults to <output-dir>/workspace)",
    )
    parser.add_argument(
        "--strict-fallback-mode",
        dest="strict_fallback_mode",
        action="store_true",
        default=True,
        help="Enable strict fallback quality gates when LLM is unavailable (default: enabled).",
    )
    parser.add_argument(
        "--no-strict-fallback-mode",
        dest="strict_fallback_mode",
        action="store_false",
        help="Disable strict fallback quality gates and allow permissive fallback behavior.",
    )
    args = parser.parse_args()

    _check_llm_connection(strict=args.strict_llm_check)

    data_file = Path(args.data_file).expanduser().resolve()
    if not data_file.exists():
        raise SystemExit(f"Data file not found: {data_file}")

    os.environ["DEEPANALYZE_USE_ORCHESTRATOR"] = "1"

    max_depth = args.max_depth if args.max_depth is not None else MAX_RECURSION_DEPTH

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir = (
        Path(args.workspace_dir).expanduser().resolve()
        if args.workspace_dir
        else output_dir / "workspace"
    )
    workspace_dir.mkdir(parents=True, exist_ok=True)

    session_id = f"serum_{int(time.time())}"
    session_dir = workspace_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(data_file, session_dir / data_file.name)

    stop_event = threading.Event()
    monitor_thread = None
    if not args.no_print_steps:
        nodes_dir = session_dir / "outputs_logs" / "nodes"
        nodes_dir.mkdir(parents=True, exist_ok=True)

        def _monitor_nodes() -> None:
            seen: set[Path] = set()
            while not stop_event.is_set():
                for path in sorted(nodes_dir.glob("*.json")):
                    if path in seen:
                        continue
                    seen.add(path)
                    try:
                        payload = json.loads(path.read_text(encoding="utf-8"))
                        node = payload.get("node", "unknown")
                        error = payload.get("error")
                        status = "error" if error else "success"
                        print(f"[step] {node}: {status}")
                    except Exception:
                        print(f"[step] {path.name}")
                time.sleep(0.5)

        monitor_thread = threading.Thread(target=_monitor_nodes, daemon=True)
        monitor_thread.start()

    config = {
        "max_depth": max_depth,
        "report_format": args.report_format,
        "report_language": args.report_language,
        "report_export_mode": args.report_export_mode,
        "analysis_goal": args.analysis_goal,
        "docs/analysis_goal": args.analysis_goal,
        "workspace_base_dir": str(workspace_dir),
        "strict_fallback_mode": bool(args.strict_fallback_mode),
    }

    state = run_orchestrated_docs_analysis(session_id=session_id, config=config)
    if stop_event:
        stop_event.set()
    if monitor_thread:
        monitor_thread.join(timeout=2.0)

    _write_json(output_dir / "run_state.json", state)

    report_dir = Path(state.get("data_sessions_active_dirs", {}).get("report", "")) if isinstance(state, dict) else Path()
    report_candidates = []
    if report_dir.exists():
        report_candidates = sorted(report_dir.glob("report_v*.*"), key=lambda p: p.stat().st_mtime)
    latest_report = report_candidates[-1] if report_candidates else None

    summary = {
        "session_id": session_id,
        "data_file": str(data_file),
        "workspace": str(session_dir),
        "workspace_root": str(workspace_dir),
        "report": str(latest_report) if latest_report else "",
        "output_dir": str(output_dir),
        "max_depth": max_depth,
    }
    _write_json(output_dir / "run_summary.json", summary)

    print(f"✅ Orchestrated serum analysis completed. Output: {output_dir}")


if __name__ == "__main__":
    main()
