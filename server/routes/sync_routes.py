"""数据同步 API 路由"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.websockets import WebSocket, WebSocketDisconnect

from server.services.push_service import PushService

router = APIRouter(tags=["sync"])

# 预共享 Token
VALID_TOKENS = {"soloist-carbin-token"}

# 模拟存储
_storage: dict[str, Any] = {}


async def verify_token(authorization: str = Header("")) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")
    token = authorization[7:]
    if token not in VALID_TOKENS:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token


@router.post("/sync/backup")
async def backup(data: dict[str, Any], token: str = Depends(verify_token)) -> dict[str, Any]:
    _storage["backup"] = data
    return {"status": "ok", "backed_up": True}


@router.get("/sync/restore")
async def restore(token: str = Depends(verify_token)) -> dict[str, Any]:
    data = _storage.get("backup", {})
    return {"data": data, "timestamp": "2026-06-01T00:00:00"}


@router.post("/sync/event")
async def push_event(event: dict[str, Any], token: str = Depends(verify_token)) -> dict[str, Any]:
    await PushService.broadcast(event)
    return {"status": "ok"}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = "") -> None:
    if token not in VALID_TOKENS:
        await websocket.close(code=4001)
        return
    await websocket.accept()
    PushService.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        PushService.disconnect(websocket)
