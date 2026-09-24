import os
import sys
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from src.api.scheduler import scheduler
from src.db.database import Base, engine

from .routes import downloader, generator, history, livestream

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    livestream.live_stream_manager.recover()
    yield
    livestream.live_stream_manager.shutdown()
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="Autotube API",
    description="Backend API for Autotube application",
    version="2.1.0",
    lifespan=lifespan,
)

configured_origins = [
    origin.strip()
    for origin in os.getenv(
        "AUTOTUBE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(downloader.router, prefix="/api/v1")
app.include_router(generator.router, prefix="/api/v1")
app.include_router(livestream.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")

from .logger import manager


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        manager.disconnect(websocket)


@app.get("/")
def read_root():
    return {"status": "Autotube Backend API is running", "version": app.version}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "scheduler": scheduler.running,
        "ffmpeg": bool(livestream.live_stream_manager.ffmpeg_path),
        "ffprobe": bool(livestream.live_stream_manager.ffprobe_path),
    }
