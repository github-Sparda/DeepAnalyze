"""Compatibility package redirecting to src/core."""
import importlib
import os
import sys

_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_src_path = os.path.join(_repo_root, "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

_module = importlib.import_module("core." + __name__)
sys.modules[__name__] = _module
