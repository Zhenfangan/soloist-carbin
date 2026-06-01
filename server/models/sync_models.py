"""同步模块数据模型"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class BackupRequest(BaseModel):
    data: dict[str, list[dict[str, Any]]]
    timestamp: str = ""


class RestoreResponse(BaseModel):
    data: dict[str, list[dict[str, Any]]]
    timestamp: str = ""


class EventMessage(BaseModel):
    type: str
    timestamp: str
    payload: dict[str, Any]


class ReviewStatus(BaseModel):
    date: str
    morning: dict[str, str] | None = None
    afternoon: dict[str, str] | None = None
    night: dict[str, str] | None = None
