from __future__ import annotations

from pathlib import Path
from typing import Any
import json

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import seaborn as sns

from .theme import ACADEMIC_THEME, DASHBOARD_THEME, ChartTheme


def create_plotter():
    """创建绘图器实例"""
    return Plotter()

class Plotter:
    """绘图器类"""
    def __init__(self):
        pass
    
    def plot(self, data, chart_type="line", **kwargs):
        """绘制图表"""
        if chart_type == "line":
            return render_trend(data, **kwargs)
        elif chart_type == "bar":
            return render_comparison(data, **kwargs)
        elif chart_type == "heatmap":
            return render_correlation_heatmap(data, **kwargs)
        elif chart_type == "histogram":
            return render_distribution(data, **kwargs)
        else:
            return render_fallback_plot(data, **kwargs)


def _save_metadata(output: Path, metadata: dict[str, Any]) -> None:
    meta_path = output.with_suffix(output.suffix + ".json")
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


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
        _save_metadata(
            output,
            {"type": "distribution", "column": column, "interactive": True},
        )
        return output

    _apply_seaborn_theme(theme)
    _apply_matplotlib_theme(theme)
    plt.figure(figsize=(8, 4))
    sns.histplot(df[column].dropna(), kde=True)
    plt.title(f"Distribution of {column}")
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()
    _save_metadata(
        output,
        {"type": "distribution", "column": column, "interactive": False},
    )
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
        _save_metadata(
            output,
            {"type": "correlation", "interactive": True},
        )
        return output

    _apply_seaborn_theme(theme)
    _apply_matplotlib_theme(theme)
    plt.figure(figsize=(8, 6))
    sns.heatmap(corr, annot=True, cmap="coolwarm")
    plt.title("Correlation Heatmap")
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()
    _save_metadata(
        output,
        {"type": "correlation", "interactive": False},
    )
    return output


def render_trend(
    df: pd.DataFrame,
    x: str,
    y: str,
    output_path: str | Path,
    style: str = "academic",
    interactive: bool = False,
) -> Path:
    theme = ACADEMIC_THEME if style == "academic" else DASHBOARD_THEME
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    if interactive:
        fig = px.line(df, x=x, y=y, title=f"Trend of {y} over {x}")
        fig.write_html(str(output))
        _save_metadata(output, {"type": "trend", "x": x, "y": y, "interactive": True})
        return output

    _apply_seaborn_theme(theme)
    _apply_matplotlib_theme(theme)
    plt.figure(figsize=(8, 4))
    sns.lineplot(data=df, x=x, y=y)
    plt.title(f"Trend of {y} over {x}")
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()
    _save_metadata(output, {"type": "trend", "x": x, "y": y, "interactive": False})
    return output


def render_comparison(
    df: pd.DataFrame,
    category: str,
    value: str,
    output_path: str | Path,
    style: str = "academic",
    interactive: bool = False,
) -> Path:
    theme = ACADEMIC_THEME if style == "academic" else DASHBOARD_THEME
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    if interactive:
        fig = px.bar(df, x=category, y=value, title=f"{value} by {category}")
        fig.write_html(str(output))
        _save_metadata(
            output,
            {"type": "comparison", "category": category, "value": value, "interactive": True},
        )
        return output

    _apply_seaborn_theme(theme)
    _apply_matplotlib_theme(theme)
    plt.figure(figsize=(8, 4))
    sns.barplot(data=df, x=category, y=value)
    plt.title(f"{value} by {category}")
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()
    _save_metadata(
        output,
        {"type": "comparison", "category": category, "value": value, "interactive": False},
    )
    return output


def render_group_comparison(
    df: pd.DataFrame,
    category: str,
    value: str,
    output_path: str | Path,
    mode: str = "box",
    style: str = "academic",
    interactive: bool = False,
) -> Path:
    theme = ACADEMIC_THEME if style == "academic" else DASHBOARD_THEME
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    if interactive:
        if mode == "violin":
            fig = px.violin(df, x=category, y=value, box=True, points="outliers")
        elif mode == "bar":
            fig = px.bar(df, x=category, y=value)
        else:
            fig = px.box(df, x=category, y=value)
        fig.update_layout(title=f"{mode} of {value} by {category}")
        fig.write_html(str(output))
        _save_metadata(
            output,
            {
                "type": "comparison",
                "mode": mode,
                "category": category,
                "value": value,
                "interactive": True,
            },
        )
        return output

    _apply_seaborn_theme(theme)
    _apply_matplotlib_theme(theme)
    plt.figure(figsize=(8, 4))
    if mode == "violin":
        sns.violinplot(data=df, x=category, y=value)
    elif mode == "bar":
        sns.barplot(data=df, x=category, y=value)
    else:
        sns.boxplot(data=df, x=category, y=value)
    plt.title(f"{mode} of {value} by {category}")
    plt.tight_layout()
    plt.savefig(output, dpi=200)
    plt.close()
    _save_metadata(
        output,
        {
            "type": "comparison",
            "mode": mode,
            "category": category,
            "value": value,
            "interactive": False,
        },
    )
    return output


def render_chord_placeholder(
    output_path: str | Path,
    message: str = "Chord diagram not implemented.",
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    html = (
        "<html><head><meta charset=\"utf-8\"/></head>"
        "<body>"
        "<div style=\"font-family:Arial,sans-serif;padding:16px;\">"
        f"<h3>Chord Diagram</h3><p>{message}</p>"
        "</div></body></html>"
    )
    output.write_text(html, encoding="utf-8")
    _save_metadata(
        output,
        {"type": "chord", "interactive": True, "note": "placeholder"},
    )
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
