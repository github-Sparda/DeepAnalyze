# DeepAnalyze 核心模块包
# 重构后的新结构入口点

__version__ = "1.0.0"

# 导出主要子模块
from . import orchestration
from . import visualization  
from . import reporting
from . import tools
from . import cache
from . import security

# 导出核心功能
from .orchestration.graph import create_graph
from .visualization.plotter import create_plotter
from .reporting.exporter import ReportExporter

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