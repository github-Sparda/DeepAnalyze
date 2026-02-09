"""
DeepAnalyze src/api Package
OpenAI-compatible src/api server for DeepAnalyze model
"""

import sys
import os

# Add project root to sys.path for consistent imports
project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

__version__ = "1.0.0"
__title__ = "DeepAnalyze OpenAI-Compatible src/api"

from .main import create_app, main

__all__ = ["create_app", "main"]