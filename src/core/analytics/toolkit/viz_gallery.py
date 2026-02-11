from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import seaborn as sns

from .common import load_table, numeric_columns, normalize_output_dir, write_json
from .viz_theme import apply_theme


def run(input_path: str | Path, output_dir: str | Path, theme: dict[str, Any] | None = None) -> dict[str, Any]:
    df = load_table(input_path)
    out_dir = normalize_output_dir(output_dir, "plots")
    apply_theme(theme or {})
    outputs = []
    num_cols = numeric_columns(df)
    for col in num_cols[:3]:
        fig, ax = plt.subplots()
        sns.boxplot(y=df[col].dropna(), ax=ax)
        ax.set_title(f"Boxplot of {col}")
        path = out_dir / f"box_{col}.png"
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        outputs.append(str(path))
    write_json(Path(out_dir) / "viz_gallery.json", {"plots": outputs})
    return {"module": "viz_gallery", "status": "ok", "plots": outputs}
