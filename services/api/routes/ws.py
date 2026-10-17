"""
WebSocket Real-Time Event Dispatcher.
Spec: 07_API_AND_DATABASE.md §2 (WebSocket /ws/events).
"""

from typing import List, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()
main_loop = None

def broadcast_sync(message: Dict[str, Any]):
    global main_loop
    if main_loop and main_loop.is_running():
        try:
            import asyncio
            asyncio.run_coroutine_threadsafe(manager.broadcast(message), main_loop)
        except Exception:
            pass

@router.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    global main_loop
    import asyncio
    main_loop = asyncio.get_running_loop()
    await manager.connect(websocket)
    try:
        # Send initial welcome / connection ack
        await websocket.send_json({
            "type": "connection.ack",
            "message": "Connected to SafeSite Vision Real-Time Feed"
        })
        while True:
            # Keep connection open and receive heartbeat/pings
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
