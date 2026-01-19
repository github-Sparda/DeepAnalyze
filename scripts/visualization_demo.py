from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt

from deepanalyze.visualization.writer import visualization_writer


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualization archival demo")
    parser.add_argument("--workspace", default="workspace", help="Workspace directory")
    parser.add_argument("--plan-id", default="", help="Plan ID to use")
    args = parser.parse_args()

    workspace_dir = Path(args.workspace)
    plan_id = args.plan_id or f"demo_{int(time.time())}"

    df = pd.DataFrame({"x": list(range(10)), "y": [v * v for v in range(10)]})

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(df["x"], df["y"], marker="o")
    ax.set_title("Academic Demo")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    fig.tight_layout()
    academic_entries = visualization_writer(
        fig,
        workspace_dir=workspace_dir,
        plan_id=plan_id,
        style="academic",
        name="academic_demo",
        metadata={"demo": True},
    )
    plt.close(fig)

    plotly_fig = px.line(df, x="x", y="y", title="Dashboard Demo")
    dashboard_entries = visualization_writer(
        plotly_fig,
        workspace_dir=workspace_dir,
        plan_id=plan_id,
        style="dashboard",
        name="dashboard_demo",
        metadata={"demo": True},
    )

    print("Academic outputs:")
    for entry in academic_entries:
        print(entry["path"])
    print("Dashboard outputs:")
    for entry in dashboard_entries:
        print(entry["path"])


if __name__ == "__main__":
    main()
