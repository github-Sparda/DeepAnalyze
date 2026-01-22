"""DeepAnalyze core package."""

import sys
import os

# Add project root to sys.path for consistent imports
project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from .legacy import DeepAnalyzeVLLM

__all__ = ["DeepAnalyzeVLLM"]
