"""
Main application entry point for DeepAnalyze src/api Server
Sets up the Fastsrc/api application and starts the server
"""

import time
import threading
import signal
import sys
import atexit
import os
from fastapi import Fastsrc/api
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add project root to sys.path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from .config import (
    src/api_HOST,
    src/api_PORT,
    src/api_TITLE,
    src/api_VERSION,
    src/api_PUBLIC_BASE,
    HTTP_SERVER_BASE,
    CLEANUP_INTERVAL_MINUTES,
)
from .models import HealthResponse
from .utils import start_http_server
from .storage import storage

# Safety constants
# MAX_CLEANUP_ERRORS = 10
# MAX_ITERATIONS = 1000
# CLEANUP_BACKOFF_SECONDS = 30


def create_app() -> Fastsrc/api:
    """Create and configure the Fastsrc/api application"""
    app = Fastsrc/api(title=src/api_TITLE, version=src/api_VERSION)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include all routers
    from file_api import router as file_router
    from models_api import router as models_router
    from chat_api import router as chat_router
    from admin_api import router as admin_router

    app.include_router(file_router)
    app.include_router(models_router)
    app.include_router(chat_router)
    app.include_router(admin_router)

    # Health check endpoint
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint"""
        return HealthResponse(
            status="healthy",
            timestamp=int(time.time())
        )

    return app


def main():
    """Main entry point to start the src/api server"""
    print("🚀 Starting DeepAnalyze OpenAI-Compatible src/api Server...")
    print(f"   - src/api Server: {src/api_PUBLIC_BASE}")
    print(f"   - File Server: {HTTP_SERVER_BASE}")
    print(f"   - Workspace: data/sessions/active")
    print("\n📖 src/api Endpoints:")
    print("   - Models src/api: /v1/models")
    print("   - Files src/api: /v1/files")
    print("   - Chat src/api: /v1/chat/completions")
    print("   - Admin src/api: /v1/admin")

    # Start HTTP file server in a separate thread
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()

    # Create and start the Fastsrc/api application
    app = create_app()

    print("Starting src/api server...")
    uvicorn.run(app, host=src/api_HOST, port=src/api_PORT)


if __name__ == "__main__":
    main()
