import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from .routes import downloader, generator, livestream, history
from src.db.database import engine, Base

# Create tables
Base.metadata.create_all(bind=engine)

from contextlib import asynccontextmanager
from src.api.scheduler import scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler.start()
    yield
    # Shutdown
    scheduler.shutdown()

app = FastAPI(
    title="Autotube API",
    description="Backend API for Autotube application",
    version="2.0.0",
    lifespan=lifespan
)

# Allow CORS for Cloudflare Pages frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with the Cloudflare Pages URL
    allow_credentials=True,
    allow_methods=["*"],
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
            # We don't expect messages from client, but we must receive to keep connection open
            data = await websocket.receive_text()
    except Exception:
        manager.disconnect(websocket)

@app.get("/")
def read_root():
    return {"status": "Autotube Backend API is running"}
