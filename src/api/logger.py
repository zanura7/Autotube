import logging
from typing import List
from fastapi import WebSocket

# Standard Python logger
logger = logging.getLogger("autotube")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_log(self, message: str, level: str = "INFO"):
        logger.log(logging.INFO if level == "INFO" else logging.WARNING if level == "WARNING" else logging.ERROR if level == "ERROR" else logging.INFO, message)
        
        # Broadcast to all connected clients
        for connection in self.active_connections:
            try:
                await connection.send_json({"type": "log", "message": message, "level": level})
            except Exception:
                pass

    async def broadcast_progress(self, current: int, total: int, text: str = ""):
        for connection in self.active_connections:
            try:
                await connection.send_json({
                    "type": "progress",
                    "current": current,
                    "total": total,
                    "text": text
                })
            except Exception:
                pass

    def sync_broadcast_log(self, message: str, level: str = "INFO"):
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast_log(message, level))
        except RuntimeError:
            # If no running loop (e.g. in thread pool), use asyncio.run or standard logging
            logger.log(logging.INFO if level == "INFO" else logging.WARNING if level == "WARNING" else logging.ERROR if level == "ERROR" else logging.INFO, message)

    def sync_broadcast_progress(self, current: int, total: int, text: str = ""):
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast_progress(current, total, text))
        except RuntimeError:
            pass

manager = ConnectionManager()
