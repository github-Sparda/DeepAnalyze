from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_report_narrative_audit_script_outputs_metrics(tmp_path: Path) -> None:
    session_dir = tmp_path / "session"
    (session_dir / "result").mkdir(parents=True, exist_ok=True)
    (session_dir / "meta").mkdir(parents=True, exist_ok=True)
    report_dir = session_dir / "report"
    report_dir.mkdir(parents=True, exist_ok=True)

    (session_dir / "result" / "hypothesis_evidence_pack.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "quant_metrics": [
                            {"name": "cv_mean_accuracy"},
                            {"name": "centroid_accuracy"},
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    report_path = report_dir / "report_v1.html"
    report_path.write_text(
        "<html><body>交叉验证平均准确率（cv_mean_accuracy） 质心分类准确率（centroid_accuracy） 门槛类型：x 当前状态：y</body></html>",
        encoding="utf-8",
    )

    subprocess.run(
        [
            "python",
            "scripts/audit_report_narrative.py",
            "--session-dir",
            str(session_dir),
            "--report-file",
            str(report_path),
        ],
        check=True,
    )
    payload = json.loads((session_dir / "meta" / "report_narrative_audit.json").read_text(encoding="utf-8"))
    assert payload["metric_name_coverage"] == 1.0
    assert payload["gate_raw_exposure_rate"] == 0.0
