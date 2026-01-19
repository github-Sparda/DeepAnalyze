from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path

from API.config import (
    MAX_RECURSION_DEPTH,
    REPORT_FORMAT,
    REPORT_LANGUAGE,
    REPORT_EXPORT_MODE,
    VISUAL_STYLE,
    VISUAL_INTERACTIVE,
    USE_ORCHESTRATOR,
)
from deepanalyze.orchestration.runner import run_orchestrated_analysis

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
    max_depth = body.get("analysis_depth", MAX_RECURSION_DEPTH)
    try:
        max_depth = int(max_depth)
    except Exception:
        max_depth = MAX_RECURSION_DEPTH
    max_depth = max(0, min(max_depth, 3))
    state = run_orchestrated_analysis(
        session_id=session_id,
        config={
            "max_depth": max_depth,
            "report_format": body.get("report_format", REPORT_FORMAT),
            "report_language": body.get("report_language", REPORT_LANGUAGE),
            "report_export_mode": body.get("report_export_mode", REPORT_EXPORT_MODE),
            "visual_style": body.get("visual_style", VISUAL_STYLE),
            "visual_interactive": body.get("visual_interactive", VISUAL_INTERACTIVE),
        },
    )
    return {
        "id": f"chatcmpl-{session_id}",
        "object": "chat.completion",
        "model": "deepanalyze-orchestrator",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": state.get("report")
                    or state.get("analysis_results")
                    or state.get("plan")
                    or "",
                },
                "finish_reason": "stop",
            }
        ],
    }
