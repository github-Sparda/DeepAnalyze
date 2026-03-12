"""可视化工具函数.

提供统一的可视化辅助函数，减少代码重复.
"""

from typing import Any
from pathlib import Path


def create_basic_plot_setup(
    input_path: str | Path,
    output_dir: str | Path,
    theme: dict[str, Any] | None = None,
    default_subdir: str = "plots"
) -> tuple[Any, Path]:
    """创建基础绘图设置.

    Args:
        input_path: 输入文件路径
        output_dir: 输出目录
        theme: 主题配置
        default_subdir: 默认子目录名

    Returns:
        (DataFrame, 输出目录路径)
    """
    from src.core.analytics.toolkit.common import load_table, normalize_output_dir
    from src.core.analytics.toolkit.viz_theme import apply_theme

    df = load_table(input_path)
    out_dir = normalize_output_dir(output_dir, default_subdir)
    apply_theme(theme or {})
    return df, out_dir


def save_plot_and_close(fig: Any, path: Path, bbox_inches: str = "tight") -> str:
    """保存图表并关闭.

    Args:
        fig: 图表对象
        path: 保存路径
        bbox_inches: 边界设置

    Returns:
        保存的路径字符串
    """
    import matplotlib.pyplot as plt

    fig.savefig(path, bbox_inches=bbox_inches)
    plt.close(fig)
    return str(path)
