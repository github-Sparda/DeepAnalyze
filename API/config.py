"""
Configuration module for DeepAnalyze API Server
Contains all configuration constants and environment setup
"""

import os
from pathlib import Path
from urllib.parse import urlparse

# Environment setup
os.environ.setdefault("MPLBACKEND", "Agg")

def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file()

def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


# API Configuration (model/vLLM backend)
API_BASE = os.getenv("DEEPANALYZE_VLLM_BASE_URL", "http://localhost:48000/v1")
VLLM_BASE_URL = API_BASE
VLLM_BASE_URL_NO_V1 = API_BASE[:-3] if API_BASE.endswith("/v1") else API_BASE
DEEPANALYZE_VLLM_API_KEY = os.getenv("DEEPANALYZE_VLLM_API_KEY", "")
MODEL_PATH = os.getenv("DEEPANALYZE_MODEL_PATH", "DeepAnalyze-8B")
DEEPANALYZE_VLLM_API_KEY = os.getenv("DEEPANALYZE_VLLM_API_KEY", "<Enter-Your-vLLM-API-Key>")


# Workspace and file server
WORKSPACE_BASE_DIR = os.getenv("DEEPANALYZE_WORKSPACE_DIR", "workspace")
FILE_SERVER_HOST = os.getenv("DEEPANALYZE_FILE_SERVER_HOST", "localhost")
HTTP_SERVER_PORT = _get_int_env("DEEPANALYZE_FILE_SERVER_PORT", 48100)
HTTP_SERVER_BASE = f"http://{FILE_SERVER_HOST}:{HTTP_SERVER_PORT}"

# API Server Configuration
API_HOST = os.getenv("DEEPANALYZE_API_HOST", "0.0.0.0")
API_PORT = _get_int_env("DEEPANALYZE_API_PORT", _get_int_env("API_PORT", 48200))
API_PUBLIC_HOST = os.getenv("DEEPANALYZE_API_PUBLIC_HOST", "localhost")
API_PUBLIC_BASE = f"http://{API_PUBLIC_HOST}:{API_PORT}"
API_PUBLIC_BASE_V1 = f"{API_PUBLIC_BASE}/v1"
API_TITLE = "DeepAnalyze OpenAI-Compatible API"
API_VERSION = "1.0.0"

# Thread cleanup configuration
CLEANUP_TIMEOUT_HOURS = 12
CLEANUP_INTERVAL_MINUTES = 30

# Code execution configuration
CODE_EXECUTION_TIMEOUT = 120
MAX_NEW_TOKENS = 32768

# File handling configuration
FILE_STORAGE_DIR = os.path.join(WORKSPACE_BASE_DIR, "_files")
VALID_FILE_PURPOSES = ["fine-tune", "answers", "file-extract", "assistants"]

# Model configuration
DEFAULT_TEMPERATURE = 0.4
DEFAULT_MODEL = os.getenv("DEEPANALYZE_DEFAULT_MODEL", os.getenv("DEFAULT_MODEL", "DeepAnalyze-8B"))

# Stop token IDs for DeepAnalyze model
# [151676, 151645] for DeepAnalyze-8B
STOP_TOKEN_IDS = []

# Supported tools
SUPPORTED_TOOLS = ["code_interpreter"]

# Demo/Frontend settings
FRONTEND_HOST = os.getenv("DEEPANALYZE_FRONTEND_HOST", "localhost")
FRONTEND_PORT = _get_int_env("DEEPANALYZE_FRONTEND_PORT", 4000)
FRONTEND_BASE = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}"

WEBSOCKET_HOST = os.getenv("DEEPANALYZE_WEBSOCKET_HOST", "localhost")
WEBSOCKET_PORT = _get_int_env("DEEPANALYZE_WEBSOCKET_PORT", 8001)
WEBSOCKET_URL = f"ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}"

# Jupyter demo settings
JUPYTER_PORT = _get_int_env("DEEPANALYZE_JUPYTER_PORT", 8888)


def get_vllm_port() -> int | None:
    parsed = urlparse(API_BASE)
    if parsed.port:
        return parsed.port
    if parsed.scheme == "https":
        return 443
    if parsed.scheme == "http":
        return 80
    return None
