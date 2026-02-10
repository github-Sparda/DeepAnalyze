# DeepAnalyze 核心模块包
# 重构后的新结构入口点

__version__ = "1.0.0"

# 导出主要子模块
from . import orchestration
from . import visualization
from . import reporting
from . import tools
from . import cache

try:
    from . import security
except Exception:  # Optional dependency (e.g., docker)
    security = None

# 导出核心功能
def create_graph(*args, **kwargs):
    from .orchestration.graph import create_graph as _create_graph

    return _create_graph(*args, **kwargs)


def create_plotter(*args, **kwargs):
    from .visualization.plotter import create_plotter as _create_plotter

    return _create_plotter(*args, **kwargs)


try:
    from .reporting.exporter import ReportExporter as ReportExporter
except Exception as _report_exc:  # Optional dependency errors handled lazily
    class ReportExporter:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise ImportError("ReportExporter unavailable") from _report_exc

__all__ = [
    'orchestration',
    'visualization', 
    'reporting',
    'tools',
    'cache',
    'security',
    'create_graph',
    'create_plotter',
    'ReportExporter'
]

if security is None and "security" in __all__:
    __all__.remove("security")
