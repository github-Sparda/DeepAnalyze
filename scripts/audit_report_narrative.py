#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit report narrative coverage and gate language exposure")
    parser.add_argument("--session-dir", required=True, help="Session workspace directory")
    parser.add_argument("--report-file", required=True, help="Path to report html")
    parser.add_argument("--output", default="", help="Optional output json path")
    args = parser.parse_args()

    session_dir = Path(args.session_dir)
    report_file = Path(args.report_file)
    if not report_file.exists():
        raise SystemExit(f"report file not found: {report_file}")
    report_text = report_file.read_text(encoding="utf-8", errors="ignore")

    evidence = _load_json(session_dir / "result" / "hypothesis_evidence_pack.json")
    metric_names: set[str] = set()
    for hyp in evidence.get("hypotheses", []) if isinstance(evidence, dict) else []:
        if not isinstance(hyp, dict):
            continue
        for metric in hyp.get("quant_metrics", []) if isinstance(hyp.get("quant_metrics"), list) else []:
            if isinstance(metric, dict):
                name = str(metric.get("name", "")).strip()
                if name:
                    metric_names.add(name)

    matched = []
    for name in sorted(metric_names):
        if f"（{name}）" in report_text:
            matched.append(name)
    metric_coverage = round(len(matched) / max(len(metric_names), 1), 4)

    raw_gate_tokens = ["gate_rule_type=", "gate_status=", "failed_checks=", "reason_code="]
    raw_hits = sum(report_text.count(token) for token in raw_gate_tokens)
    readable_hits = report_text.count("门槛类型：") + report_text.count("当前状态：")
    raw_exposure = round(raw_hits / max(raw_hits + readable_hits, 1), 4)

    payload = {
        "metric_names_total": len(metric_names),
        "metric_names_matched": len(matched),
        "metric_name_coverage": metric_coverage,
        "gate_raw_token_hits": raw_hits,
        "gate_readable_hits": readable_hits,
        "gate_raw_exposure_rate": raw_exposure,
    }
    out = Path(args.output) if args.output else (session_dir / "meta" / "report_narrative_audit.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
