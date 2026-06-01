"""检阅端 API 路由"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException

router = APIRouter(tags=["review"])

VALID_TOKENS = {"soloist-carbin-token"}


async def verify_token(authorization: str = Header("")) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")
    token = authorization[7:]
    if token not in VALID_TOKENS:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token


@router.get("/review/status")
async def get_status(date: str = "", token: str = Depends(verify_token)) -> dict[str, Any]:
    return {
        "date": date or "2026-06-01",
        "morning": {"status": "unknown"},
        "afternoon": {"status": "unknown"},
        "night": {"status": "unknown"},
        "total_hours": 0.0,
    }


@router.get("/review/history")
async def get_history(date: str = "", token: str = Depends(verify_token)) -> dict[str, Any]:
    return {
        "date": date or "2026-06-01",
        "records": [],
    }
