"""拍摄日 + 复盘 Repository"""

from __future__ import annotations

import sqlite3

from app.models.shooting import ShootingDay, ShootingReflection
from app.repositories.base import BaseRepo


class ShootingRepo(BaseRepo):
    """拍摄日数据访问"""

    def get_by_date(self, date: str) -> ShootingDay | None:
        row = self._fetch_one(
            "SELECT * FROM shooting_days WHERE shoot_date = ?", (date,)
        )
        return self._row_to_shooting(row) if row else None

    def set_shooting_day(self, day: ShootingDay) -> ShootingDay:
        existing = self.get_by_date(day.shoot_date)
        if existing:
            self._execute(
                "UPDATE shooting_days SET reward_desc = ?, status = ? WHERE shoot_date = ?",
                (day.reward_desc, day.status, day.shoot_date),
            )
            day.id = existing.id
        else:
            rid = self._insert(
                """INSERT INTO shooting_days (shoot_date, reward_desc, status)
                   VALUES (?, ?, ?)""",
                (day.shoot_date, day.reward_desc, day.status),
            )
            day.id = rid
        return day

    def cancel(self, date: str) -> None:
        self._execute("DELETE FROM shooting_days WHERE shoot_date = ?", (date,))

    def save_reflection(self, ref: ShootingReflection) -> ShootingReflection:
        existing = self._fetch_one(
            "SELECT * FROM shooting_reflections WHERE shoot_date = ?", (ref.shoot_date,)
        )
        if existing:
            self._execute(
                """UPDATE shooting_reflections SET content = ?, location = ?,
                   was_smooth = ?, thoughts = ?, summary = ? WHERE shoot_date = ?""",
                (ref.content, ref.location, ref.was_smooth, ref.thoughts, ref.summary, ref.shoot_date),
            )
            ref.id = existing["id"]
        else:
            rid = self._insert(
                """INSERT INTO shooting_reflections (shoot_date, content, location, was_smooth, thoughts, summary)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (ref.shoot_date, ref.content, ref.location, ref.was_smooth, ref.thoughts, ref.summary),
            )
            ref.id = rid
        return ref

    def get_reflection(self, date: str) -> ShootingReflection | None:
        row = self._fetch_one(
            "SELECT * FROM shooting_reflections WHERE shoot_date = ?", (date,)
        )
        return self._row_to_reflection(row) if row else None

    @staticmethod
    def _row_to_shooting(row: sqlite3.Row) -> ShootingDay:
        return ShootingDay(
            id=row["id"],
            shoot_date=row["shoot_date"],
            reward_desc=row["reward_desc"],
            status=row["status"],
        )

    @staticmethod
    def _row_to_reflection(row: sqlite3.Row) -> ShootingReflection:
        return ShootingReflection(
            id=row["id"],
            shoot_date=row["shoot_date"],
            content=row["content"],
            location=row["location"],
            was_smooth=row["was_smooth"],
            thoughts=row["thoughts"],
            summary=row["summary"],
        )
