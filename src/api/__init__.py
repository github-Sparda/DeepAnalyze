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


def create_app(*args, **kwargs):
    from .main import create_app as _create_app

    return _create_app(*args, **kwargs)


def main(*args, **kwargs):
    from .main import main as _main

    return _main(*args, **kwargs)


__all__ = ["create_app", "main"]
