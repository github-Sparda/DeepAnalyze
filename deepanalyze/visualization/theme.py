from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChartTheme:
    background: str
    font_family: str
    font_size: int
    title_size: int
    legend: bool
    grid: bool
    border: bool


ACADEMIC_THEME = ChartTheme(
    background="#FFFFFF",
    font_family="Times New Roman",
    font_size=12,
    title_size=14,
    legend=True,
    grid=True,
    border=True,
)

DASHBOARD_THEME = ChartTheme(
    background="#F7F9FB",
    font_family="Inter",
    font_size=12,
    title_size=16,
    legend=True,
    grid=False,
    border=False,
)
