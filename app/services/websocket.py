from fastapi import WebSocket
from typing import Dict, List
from app.models.user import Role


class ConnectionManager:
    def __init__(self):
        # { role: [websocket, ...] }
        self.active_connections: Dict[str, List[WebSocket]] = {
            "all": [],
            "teacher": [],
            "student": [],
        }

    async def connect(self, websocket: WebSocket, role: str):
        await websocket.accept()
        self.active_connections["all"].append(websocket)
        if role in self.active_connections:
            self.active_connections[role].append(websocket)

    def disconnect(self, websocket: WebSocket, role: str):
        self.active_connections["all"].discard(websocket) if hasattr(self.active_connections["all"], 'discard') else None
        for key in ["all", role]:
            conns = self.active_connections.get(key, [])
            if websocket in conns:
                conns.remove(websocket)

    async def broadcast(self, message: dict, target_role: str):
        targets = self.active_connections.get(target_role, [])
        dead = []
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            if ws in targets:
                targets.remove(ws)

manager = ConnectionManager()
