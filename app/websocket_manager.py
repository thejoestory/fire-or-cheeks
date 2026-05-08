import json
from typing import Dict, List
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # game_code -> list of websockets
        self.connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, game_code: str, websocket: WebSocket):
        await websocket.accept()
        if game_code not in self.connections:
            self.connections[game_code] = []
        self.connections[game_code].append(websocket)

    def disconnect(self, game_code: str, websocket: WebSocket):
        if game_code in self.connections:
            try:
                self.connections[game_code].remove(websocket)
            except ValueError:
                pass

    async def broadcast(self, game_code: str, message: dict):
        if game_code not in self.connections:
            return
        dead = []
        for ws in self.connections[game_code]:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(game_code, ws)

    def connection_count(self, game_code: str) -> int:
        return len(self.connections.get(game_code, []))


manager = ConnectionManager()
