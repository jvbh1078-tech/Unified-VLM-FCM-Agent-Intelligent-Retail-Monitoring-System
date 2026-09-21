from __future__ import annotations
import json
from fastapi import WebSocket

class WebSocketManager:
    def __init__(self): self.active: list[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept(); self.active.append(websocket)
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active: self.active.remove(websocket)
    async def broadcast(self, payload: dict):
        text=json.dumps(payload, ensure_ascii=False)
        for ws in list(self.active):
            try: await ws.send_text(text)
            except Exception: self.disconnect(ws)
