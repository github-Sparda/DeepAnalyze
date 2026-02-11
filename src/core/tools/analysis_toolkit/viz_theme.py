from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import seaborn as sns

DEFAULT_THEME = {
    "style": "whitegrid",
    "font_scale": 1.0,
    "palette": "deep",
    "legend": True,
    "title_size": 12,
    "label_size": 10,
}


def apply_theme(theme: dict[str, Any]) -> None:
    merged = DEFAULT_THEME.copy()
    merged.update(theme or {})
    sns.set_theme(style=merged["style"], palette=merged["palette"], font_scale=merged["font_scale"])
    plt.rcParams.update(
        {
            "axes.titlesize": merged["title_size"],
            "axes.labelsize": merged["label_size"],
            "legend.frameon": bool(merged.get("legend", True)),
        }
    )
