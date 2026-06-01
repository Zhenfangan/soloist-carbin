"""WebSocket 推送服务 — 连接池管理"""

from __future__ import annotations

from typing import Any

from fastapi.websockets import WebSocket


class PushService:
    """WebSocket 连接池 + 广播推送"""

    _connections: list[WebSocket] = []

    @classmethod
    def connect(cls, websocket: WebSocket) -> None:
        if websocket not in cls._connections:
            cls._connections.append(websocket)

    @classmethod
    def disconnect(cls, websocket: WebSocket) -> None:
        if websocket in cls._connections:
            cls._connections.remove(websocket)

    @classmethod
    async def broadcast(cls, message: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for ws in cls._connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            cls._connections.remove(ws)
