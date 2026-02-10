#!/usr/bin/env python3
"""
End-to-end CLI runner for serum dataset analysis.
Supports direct mode (local modules) and API mode (OpenAI-compatible API).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
CLI_DIR = PROJECT_ROOT / "src" / "cli"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*swig.*")


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _ensure_output_dir(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _run_direct_mode(data_file: Path, output_dir: Path, analysis_types: List[str], chart_type: str, report_type: str) -> None:
    try:
        from direct_cli import DirectDeepAnalyzeCLI
        from src.api.config import WORKSPACE_BASE_DIR
    except Exception as exc:
        raise RuntimeError("Direct CLI dependencies are not available") from exc

    cli = DirectDeepAnalyzeCLI()
    result = cli.analyze_data_direct(str(data_file), analysis_types=analysis_types)
    if not result:
        raise RuntimeError("Direct analysis failed; no result returned")

    _write_json(output_dir / "analysis_results.json", result)

    viz_path = cli.generate_visualization_direct(result, chart_type=chart_type, output_path=str(output_dir / "visualization.png"))

    report = cli.generate_report_direct(result, report_type=report_type, include_visualizations=True)

    report_paths: Dict[str, str] = {}
    if report is not None:
        session_id = cli.current_session_id
        report_dir = Path(WORKSPACE_BASE_DIR) / session_id / "reports" / report.report_id
        content_path = report_dir / "content.md"
        metadata_path = report_dir / "metadata.json"
        if content_path.exists():
            dest = output_dir / "report.md"
            dest.write_text(content_path.read_text(encoding="utf-8"), encoding="utf-8")
            report_paths["report_md"] = str(dest)
        if metadata_path.exists():
            dest = output_dir / "report_metadata.json"
            dest.write_text(metadata_path.read_text(encoding="utf-8"), encoding="utf-8")
            report_paths["report_metadata"] = str(dest)

    summary = {
        "mode": "direct",
        "data_file": str(data_file),
        "session_id": cli.current_session_id,
        "analysis_types": analysis_types,
        "visualization": viz_path,
        "report": report_paths,
        "output_dir": str(output_dir),
    }
    _write_json(output_dir / "run_summary.json", summary)


def _download_file(url: str, dest: Path) -> None:
    import requests

    response = requests.get(url, timeout=60)
    response.raise_for_status()
    dest.write_bytes(response.content)


def _run_api_mode(data_file: Path, output_dir: Path, analysis_types: List[str], model: str | None) -> None:
    try:
        from src.api.config import API_PUBLIC_BASE_V1, API_PUBLIC_BASE, DEFAULT_MODEL, DEEPANALYZE_VLLM_API_KEY
        from openai import OpenAI
    except Exception as exc:
        raise RuntimeError("API client dependencies are not available") from exc

    api_base = os.getenv("DEEPANALYZE_API_BASE", API_PUBLIC_BASE_V1)
    api_key = os.getenv("DEEPANALYZE_VLLM_API_KEY", DEEPANALYZE_VLLM_API_KEY)
    client = OpenAI(base_url=api_base, api_key=api_key)

    # Basic health check
    try:
        import requests

        health = requests.get(f"{API_PUBLIC_BASE}/health", timeout=5)
        if health.status_code != 200:
            raise RuntimeError(f"API server unhealthy: {health.status_code}")
    except Exception as exc:
        raise RuntimeError("API server is not reachable") from exc

    with data_file.open("rb") as f:
        file_obj = client.files.create(file=f, purpose="file-extract")

    prompt = (
        "请对上传的血清数据进行完整分析，并生成报告与可视化输出。"
        "请在回答中总结关键发现，并确保生成的文件可以通过返回的链接下载。"
    )
    if analysis_types:
        prompt += f"\n分析类型: {', '.join(analysis_types)}"

    response = client.chat.completions.create(
        model=model or DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt, "file_ids": [file_obj.id]}],
        stream=False,
    )

    response_text = response.choices[0].message.content or ""
    (output_dir / "api_response.md").write_text(response_text, encoding="utf-8")

    response_dict = None
    try:
        response_dict = response.model_dump()
    except Exception:
        try:
            response_dict = response.to_dict()
        except Exception:
            response_dict = None

    downloaded: List[str] = []
    if response_dict:
        generated_files = response_dict.get("generated_files") or response_dict.get("files")
        if generated_files:
            files_dir = output_dir / "generated_files"
            files_dir.mkdir(parents=True, exist_ok=True)
            for item in generated_files:
                url = item.get("url") if isinstance(item, dict) else None
                name = item.get("name") if isinstance(item, dict) else None
                if not url:
                    continue
                dest = files_dir / (name or Path(url).name)
                _download_file(url, dest)
                downloaded.append(str(dest))

    summary = {
        "mode": "api",
        "data_file": str(data_file),
        "analysis_types": analysis_types,
        "api_base": api_base,
        "downloaded_files": downloaded,
        "output_dir": str(output_dir),
    }
    _write_json(output_dir / "run_summary.json", summary)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run serum dataset analysis via CLI.")
    parser.add_argument("--mode", choices=["direct", "api"], default="direct", help="Execution mode")
    parser.add_argument(
        "--data-file",
        default="data/examples/serum/Normal_EP_serum_data.xlsx",
        help="Input dataset path",
    )
    parser.add_argument("--output-dir", default="outputs/serum_cli", help="Output directory")
    parser.add_argument("--analysis-types", nargs="+", default=["descriptive", "inferential"], help="Analysis types")
    parser.add_argument("--chart-type", default="auto", help="Visualization chart type")
    parser.add_argument("--report-type", default="analytical", help="Report type")
    parser.add_argument("--model", default=None, help="Model name for API mode")
    args = parser.parse_args()

    data_file = Path(args.data_file).expanduser().resolve()
    if not data_file.exists():
        raise SystemExit(f"Data file not found: {data_file}")

    output_dir = _ensure_output_dir(Path(args.output_dir))

    if args.mode == "direct":
        _run_direct_mode(data_file, output_dir, args.analysis_types, args.chart_type, args.report_type)
    else:
        _run_api_mode(data_file, output_dir, args.analysis_types, args.model)

    print(f"✅ Serum analysis completed: {output_dir}")


if __name__ == "__main__":
    main()
