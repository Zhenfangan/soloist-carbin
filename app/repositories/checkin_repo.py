"""打卡记录 Repository"""

from __future__ import annotations

import sqlite3

from app.models.checkin import Checkin
from app.repositories.base import BaseRepo


class CheckinRepo(BaseRepo):
    """打卡记录数据访问"""

    def get_by_date_period(self, date: str, period: str) -> Checkin | None:
        """查询指定日期和时段的打卡记录"""
        row = self._fetch_one(
            "SELECT * FROM checkins WHERE checkin_date = ? AND period = ?",
            (date, period),
        )
        return self._row_to_checkin(row) if row else None

    def upsert(self, checkin: Checkin) -> Checkin:
        """原子 upsert — 使用 INSERT ON CONFLICT 消除 TOCTOU 竞态"""
        self._execute(
            """INSERT INTO checkins (checkin_date, period, checkin_time,
               checkout_time, checkout_type, status, is_shooting,
               created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
               ON CONFLICT(checkin_date, period) DO UPDATE SET
               checkin_time = excluded.checkin_time,
               checkout_time = excluded.checkout_time,
               checkout_type = excluded.checkout_type,
               status = excluded.status,
               is_shooting = excluded.is_shooting,
               updated_at = datetime('now')""",
            (
                checkin.checkin_date,
                checkin.period,
                checkin.checkin_time,
                checkin.checkout_time,
                checkin.checkout_type,
                checkin.status,
                checkin.is_shooting,
            ),
        )
        row = self._fetch_one(
            "SELECT * FROM checkins WHERE checkin_date = ? AND period = ?",
            (checkin.checkin_date, checkin.period),
        )
        if row:
            checkin.id = row["id"]
        return checkin

    def get_all_by_date(self, date: str) -> list[Checkin]:
        """查询指定日期所有时段的打卡记录"""
        rows = self._fetch_all(
            "SELECT * FROM checkins WHERE checkin_date = ? ORDER BY period", (date,)
        )
        return [self._row_to_checkin(r) for r in rows]

    def get_all_by_week(self, week_start: str) -> list[Checkin]:
        """查询指定周的所有打卡记录"""
        rows = self._fetch_all(
            "SELECT * FROM checkins WHERE checkin_date >= ? AND checkin_date < date(?, '+7 days') ORDER BY checkin_date, period",
            (week_start, week_start),
        )
        return [self._row_to_checkin(r) for r in rows]

    def get_all_by_month(self, year: int, month: int) -> list[Checkin]:
        """查询指定月的所有打卡记录"""
        month_str = f"{month:02d}"
        rows = self._fetch_all(
            "SELECT * FROM checkins WHERE checkin_date LIKE ? ORDER BY checkin_date, period",
            (f"{year}-{month_str}%",),
        )
        return [self._row_to_checkin(r) for r in rows]

    def get_unchecked_out(self, date: str) -> list[Checkin]:
        """查询指定日期有签到但无签退的记录"""
        rows = self._fetch_all(
            """SELECT * FROM checkins
               WHERE checkin_date = ? AND checkin_time IS NOT NULL
               AND checkout_time IS NULL""",
            (date,),
        )
        return [self._row_to_checkin(r) for r in rows]

    @staticmethod
    def _row_to_checkin(row: sqlite3.Row) -> Checkin:
        return Checkin(
            id=row["id"],
            checkin_date=row["checkin_date"],
            period=row["period"],
            checkin_time=row["checkin_time"],
            checkout_time=row["checkout_time"],
            checkout_type=row["checkout_type"],
            status=row["status"],
            is_shooting=row["is_shooting"],
        )
