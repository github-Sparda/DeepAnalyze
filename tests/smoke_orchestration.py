from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from deepanalyze.orchestration.graph import build_graph
from deepanalyze.orchestration.state import OrchestrationState


class FakeLLM:
    def chat(self, messages, max_tokens=1024):
        content = "\n".join(m.get("content", "") for m in messages)
        if "Convert the plan to JSON" in content:
            return json.dumps(
                {
                    "hypotheses": [
                        {
                            "title": "hypothesis_1",
                            "steps": ["compute summary stats"],
                            "artifacts": ["summary table"],
                        }
                    ]
                }
            )
        if "Generate Python analysis steps" in content:
            return json.dumps(
                {
                    "steps": [
                        {
                            "name": "summary",
                            "filename": "summary.py",
                            "code": "import pandas as pd\nprint(pd.read_csv('sample.csv').describe())",
                        }
                    ]
                }
            )
        if "Fix the Python code" in content:
            return "print('fixed')"
        if "Draft a report outline" in content:
            return "1. Overview\n2. Findings"
        if "Write the final report" in content:
            return "# Report\n\nSummary report."
        if "Summarize the dataset" in content:
            return "- sample.csv has 4 rows"
        if "propose multiple hypotheses" in content:
            return "Hypothesis 1: value differs by group"
        return "OK"


def main():
    fixture = Path(__file__).parent / "fixtures" / "sample.csv"
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        (workspace / fixture.name).write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")
        state: OrchestrationState = {
            "session_id": "smoke",
            "workspace_dir": str(workspace),
            "depth": 1,
            "max_depth": 1,
            "config": {"report_format": "markdown", "report_language": "en"},
        }
        graph = build_graph(FakeLLM(), state["config"])
        result = graph.invoke(state)
        report_versions = result.get("report_versions", [])
        if not report_versions:
            raise SystemExit("No report generated")
        print("OK")


if __name__ == "__main__":
    main()
