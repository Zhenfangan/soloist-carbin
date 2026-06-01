"""连续出勤记录 Repository"""

from __future__ import annotations

import sqlite3

from app.models.streak import AttendanceStreak
from app.repositories.base import BaseRepo


class StreakRepo(BaseRepo):
    """连续出勤数据访问"""

    def get(self) -> AttendanceStreak:
        row = self._fetch_one("SELECT * FROM attendance_streak ORDER BY id LIMIT 1")
        if row:
            return self._row_to_streak(row)
        return AttendanceStreak()

    def update(self, streak: int, last_date: str) -> AttendanceStreak:
        existing = self._fetch_one("SELECT * FROM attendance_streak ORDER BY id LIMIT 1")
        if existing:
            self._execute(
                """UPDATE attendance_streak SET current_streak = ?, last_checkin_date = ?,
                   updated_at = datetime('now') WHERE id = ?""",
                (streak, last_date, existing["id"]),
            )
        else:
            self._insert(
                """INSERT INTO attendance_streak (current_streak, last_checkin_date)
                   VALUES (?, ?)""",
                (streak, last_date),
            )
        return AttendanceStreak(current_streak=streak, last_checkin_date=last_date)

    @staticmethod
    def _row_to_streak(row: sqlite3.Row) -> AttendanceStreak:
        return AttendanceStreak(
            id=row["id"],
            current_streak=row["current_streak"],
            last_checkin_date=row["last_checkin_date"],
        )
