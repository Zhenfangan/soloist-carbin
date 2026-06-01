"""拍摄日模块数据模型"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ShootingDay:
    """拍摄日 — 对应 shooting_days 表"""
    shoot_date: str
    reward_desc: str | None = None
    status: str = "active"
    id: int | None = None


@dataclass
class ShootingReflection:
    """拍摄复盘 — 对应 shooting_reflections 表"""
    shoot_date: str
    content: str | None = None
    location: str | None = None
    was_smooth: str | None = None
    thoughts: str | None = None
    summary: str | None = None
    id: int | None = None
