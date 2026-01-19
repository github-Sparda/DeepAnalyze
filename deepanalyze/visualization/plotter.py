from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import seaborn as sns

from .theme import ACADEMIC_THEME, DASHBOARD_THEME, ChartTheme


def _apply_matplotlib_theme(theme: ChartTheme) -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": theme.background,
            "axes.facecolor": theme.background,
            "font.family": theme.font_family,
            "font.size": theme.font_size,
        }
    )


def _apply_seaborn_theme(theme: ChartTheme) -> None:
    sns.set_theme(
        style="whitegrid" if theme.grid else "white",
        rc={
            "axes.facecolor": theme.background,
            "figure.facecolor": theme.background,
            "font.family": theme.font_family,
            "font.size": theme.font_size,
        },
    )


def render_distribution(
    df: pd.DataFrame,
    column: str,
    output_path: str | Path,
    style: str = "academic",
    interactive: bool = False,
) -> Path:
    theme = ACADEMIC_THEME if style == "academic" else DASHBOARD_THEME
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    if interactive:
        fig = px.histogram(df, x=column, title=f"Distribution of {column}")
        fig.write_html(str(output))
        return output

    _apply_seaborn_theme(theme)
    _apply_matplotlib_theme(theme)
    plt.figure(figsize=(8, 4))
    sns.histplot(df[column].dropna(), kde=True)
    plt.title(f"Distribution of {column}")
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()
    return output


def render_correlation_heatmap(
    df: pd.DataFrame,
    output_path: str | Path,
    style: str = "academic",
    interactive: bool = False,
) -> Path:
    theme = ACADEMIC_THEME if style == "academic" else DASHBOARD_THEME
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    corr = df.corr(numeric_only=True)
    if interactive:
        fig = px.imshow(corr, text_auto=True, title="Correlation Heatmap")
        fig.write_html(str(output))
        return output

    _apply_seaborn_theme(theme)
    _apply_matplotlib_theme(theme)
    plt.figure(figsize=(8, 6))
    sns.heatmap(corr, annot=True, cmap="coolwarm")
    plt.title("Correlation Heatmap")
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()
    return output


def render_fallback_plot(
    df: pd.DataFrame,
    output_path: str | Path,
    note: str = "Fallback plot",
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(6, 3))
    plt.text(0.5, 0.5, note, ha="center", va="center")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()
    return output
