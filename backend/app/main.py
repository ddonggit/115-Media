"""FastAPI application entry point."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.database import init_db
from app.core.websocket import manager as ws_manager
from app.api.v1 import get_router
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    await init_db()
    # Attempt to restore 115 client from stored cookie (with timeout)
    try:
        from app.core.p115_wrapper import init_client_from_db
        client = await asyncio.wait_for(init_client_from_db(), timeout=10)
        if client:
            logger.info("115 client restored from DB at startup")
        else:
            logger.info("No 115 client available — login via /auth/qrcode or /auth/cookie")
    except asyncio.TimeoutError:
        logger.warning("115 client init timed out — starting without 115 client")
    except Exception as e:
        logger.warning("Failed to init 115 client at startup: %s", e)

    yield


app = FastAPI(
    title="115-Media",
    description="115 netdisk personal media library manager",
    version="1.6.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all v1 API routes (lazy-loaded)
app.include_router(get_router())

# Serve frontend SPA static files (single-container deployment)
_FRONTEND_DIST = os.environ.get("FRONTEND_DIST", "/app/frontend/dist")
if os.path.isdir(_FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=f"{_FRONTEND_DIST}/assets"), name="assets")
    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        index_path = os.path.join(_FRONTEND_DIST, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        return {"detail": "Not Found"}


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket endpoint for real-time task progress — legacy path."""
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


@app.websocket("/ws/task/status")
async def ws_task_status(ws: WebSocket):
    """WebSocket for real-time task progress updates (SPEC §4.13)."""
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


@app.websocket("/ws/log/realtime")
async def ws_log_realtime(ws: WebSocket):
    """WebSocket for real-time log streaming (SPEC §4.13)."""
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
