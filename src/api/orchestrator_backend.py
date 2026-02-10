from fastapi import FastAPI, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
from typing import Any, Mapping
import time

import sys
import os

# Add project root to sys.path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.api.config import (
    MAX_RECURSION_DEPTH,
    REPORT_FORMAT,
    REPORT_LANGUAGE,
    REPORT_EXPORT_MODE,
    VISUAL_STYLE,
    VISUAL_INTERACTIVE,
    USE_ORCHESTRATOR,
    WORKSPACE_BASE_DIR,
)
from src.api.utils import execute_code_safe
from src.core.orchestration.document_manager import DocumentManager
from src.core.orchestration.intent_router import ChatIntent, classify_intent
from src.core.orchestration.runner import run_orchestrated_docs_analysis

app = FastAPI(title="DeepAnalyze Orchestrator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat/completions")
async def orchestrated_chat(body: dict = Body(...)):
    if not USE_ORCHESTRATOR:
        return JSONResponse(
            {"error": "Orchestrator disabled"}, status_code=501
        )
    session_id = body.get("session_id", "default")
    data_sessions_active_dir = Path(WORKSPACE_BASE_DIR) / session_id
    document_manager = DocumentManager(data_sessions_active_dir)
    manifest = document_manager.load_manifest()
    messages = body.get("messages", [])
    user_text = _last_user_message(messages)
    decision = classify_intent(user_text, manifest)
    max_depth = body.get("docs/analysis_depth", MAX_RECURSION_DEPTH)
    depth_decision = str(body.get("depth_decision", "")).strip().lower()
    try:
        max_depth = int(max_depth)
    except Exception:
        max_depth = MAX_RECURSION_DEPTH
    max_depth = max(0, min(max_depth, 3))
    if decision.intent == ChatIntent.REUSE_ARTIFACT and decision.artifact_preview:
        preview = decision.artifact_preview
        message = f"Reusing existing {preview.get('kind')} “{preview.get('name', '')}”."
        return _reuse_response(session_id, message, preview)

    state = run_orchestrated_docs_analysis(
        session_id=session_id,
        config={
            "max_depth": max_depth,
            "report_format": body.get("report_format", REPORT_FORMAT),
            "report_language": body.get("report_language", REPORT_LANGUAGE),
            "report_export_mode": body.get("report_export_mode", REPORT_EXPORT_MODE),
            "visual_style": body.get("visual_style", VISUAL_STYLE),
            "visual_interactive": body.get("visual_interactive", VISUAL_INTERACTIVE),
            "depth_decision": depth_decision,
            "docs/analysis_goal": decision.goal or "",
            "user_intent": decision.intent.value,
        },
    )
    depth_prompt = state.get("depth_prompt", "")
    return {
        "id": f"chatcmpl-{session_id}",
        "object": "chat.completion",
        "model": "src/core-orchestrator",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": state.get("report")
                    or state.get("docs/analysis_results")
                    or state.get("plan")
                    or "",
                },
                "finish_reason": "stop",
            }
        ],
        "depth_prompt": depth_prompt,
        "depth_confirmation": depth_prompt,
        "continuation_required": state.get("continuation_required", False),
        "intent": decision.intent.value,
        "manifest": manifest,
    }


@app.post("/execute")
async def execute_code(body: dict = Body(...)):
    session_id = body.get("session_id", "default")
    code = body.get("code", "")
    data_sessions_active_dir = Path(WORKSPACE_BASE_DIR) / session_id
    data_sessions_active_dir.mkdir(parents=True, exist_ok=True)
    try:
        output = execute_code_safe(code, str(data_sessions_active_dir))
        return {"result": output}
    except Exception as exc:  # pragma: no cover
        return {
            "error": "execution_failed",
            "message": str(exc),
        }


@app.get("/documents/summary")
async def documents_summary(session_id: str = Query("default")):
    data_sessions_active_dir = Path(WORKSPACE_BASE_DIR) / session_id
    manager = DocumentManager(data_sessions_active_dir)
    manifest = manager.manifest()
    return manifest


def _last_user_message(messages: list[Mapping[str, Any]]) -> str:
    for message in reversed(messages or []):
        if message.get("role") == "user":
            return str(message.get("content", "") or "")
    return ""


def _reuse_response(session_id: str, message: str, preview: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-{session_id}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "src/core-orchestrator",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": message,
                },
                "finish_reason": "stop",
            }
        ],
        "depth_prompt": "",
        "depth_confirmation": "",
        "continuation_required": False,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=48200)
