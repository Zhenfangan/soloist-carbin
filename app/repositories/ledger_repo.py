"""账本流水 Repository"""

from __future__ import annotations

import sqlite3

from app.models.ledger import BoyfriendPromise, LedgerEntry
from app.repositories.base import BaseRepo


class LedgerRepo(BaseRepo):
    """账本流水数据访问"""

    def insert(self, entry: LedgerEntry) -> LedgerEntry:
        rid = self._insert(
            """INSERT INTO ledger_entries (entry_date, week_start, type, amount,
               description, reward_item, reward_qty, fulfilled, source_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (
                entry.entry_date,
                entry.week_start,
                entry.type,
                entry.amount,
                entry.description,
                entry.reward_item,
                entry.reward_qty,
                entry.fulfilled,
                entry.source_id,
            ),
        )
        entry.id = rid
        return entry

    def get_by_date(self, date: str) -> list[LedgerEntry]:
        rows = self._fetch_all(
            "SELECT * FROM ledger_entries WHERE entry_date = ?", (date,)
        )
        return [self._row_to_entry(r) for r in rows]

    def get_by_week(self, week_start: str) -> list[LedgerEntry]:
        rows = self._fetch_all(
            """SELECT * FROM ledger_entries
               WHERE entry_date >= ? AND entry_date < date(?, '+7 days')
               ORDER BY entry_date""",
            (week_start, week_start),
        )
        return [self._row_to_entry(r) for r in rows]

    def get_by_month(self, year: int, month: int) -> list[LedgerEntry]:
        month_str = f"{month:02d}"
        rows = self._fetch_all(
            "SELECT * FROM ledger_entries WHERE entry_date LIKE ? ORDER BY entry_date",
            (f"{year}-{month_str}%",),
        )
        return [self._row_to_entry(r) for r in rows]

    def get_by_year(self, year: int) -> list[LedgerEntry]:
        rows = self._fetch_all(
            "SELECT * FROM ledger_entries WHERE entry_date LIKE ? ORDER BY entry_date",
            (f"{year}%",),
        )
        return [self._row_to_entry(r) for r in rows]

    def get_daily_summary(self, date: str) -> dict[str, float]:
        rows = self._fetch_all(
            """SELECT type, SUM(amount) as total FROM ledger_entries
               WHERE entry_date = ? GROUP BY type""",
            (date,),
        )
        return {r["type"]: r["total"] for r in rows}

    # ── 男友承诺 ──

    def upsert_promise(self, promise: BoyfriendPromise) -> BoyfriendPromise:
        existing = self._fetch_one(
            "SELECT * FROM boyfriend_promises WHERE promise_date = ?",
            (promise.promise_date,),
        )
        if existing:
            self._execute(
                """UPDATE boyfriend_promises SET reward_desc = ?, reward_qty = ?,
                   fulfilled = ? WHERE promise_date = ?""",
                (promise.reward_desc, promise.reward_qty, promise.fulfilled, promise.promise_date),
            )
            promise.id = existing["id"]
        else:
            rid = self._insert(
                """INSERT INTO boyfriend_promises (promise_date, reward_desc, reward_qty, fulfilled)
                   VALUES (?, ?, ?, ?)""",
                (promise.promise_date, promise.reward_desc, promise.reward_qty, promise.fulfilled),
            )
            promise.id = rid
        return promise

    def get_promise(self, date: str) -> BoyfriendPromise | None:
        row = self._fetch_one(
            "SELECT * FROM boyfriend_promises WHERE promise_date = ?", (date,)
        )
        return self._row_to_promise(row) if row else None

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> LedgerEntry:
        return LedgerEntry(
            id=row["id"],
            entry_date=row["entry_date"],
            week_start=row["week_start"],
            type=row["type"],
            amount=row["amount"],
            description=row["description"],
            reward_item=row["reward_item"],
            reward_qty=row["reward_qty"],
            fulfilled=row["fulfilled"],
            source_id=row["source_id"],
        )

    @staticmethod
    def _row_to_promise(row: sqlite3.Row) -> BoyfriendPromise:
        return BoyfriendPromise(
            id=row["id"],
            promise_date=row["promise_date"],
            reward_desc=row["reward_desc"],
            reward_qty=row["reward_qty"],
            fulfilled=row["fulfilled"],
        )
