"""激励模块数据模型"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AttendanceStreak:
    """连续出勤记录 — 对应 attendance_streak 表"""
    current_streak: int = 0
    last_checkin_date: str | None = None
    id: int | None = None
