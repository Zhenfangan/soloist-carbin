"""对赌任务 Repository"""

from __future__ import annotations

import sqlite3

from app.models.ledger import BetConfig, BetTask
from app.repositories.base import BaseRepo


class BetRepo(BaseRepo):
    """对赌任务数据访问"""

    # ── 任务 CRUD ──

    def create_task(self, task: BetTask) -> BetTask:
        rid = self._insert(
            """INSERT INTO bet_tasks (week_start, task_desc, target_qty, current_qty, is_completed, is_extra)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (task.week_start, task.task_desc, task.target_qty, task.current_qty,
             task.is_completed, task.is_extra),
        )
        task.id = rid
        return task

    def get_tasks_by_week(self, week_start: str) -> list[BetTask]:
        rows = self._fetch_all(
            "SELECT * FROM bet_tasks WHERE week_start = ?", (week_start,)
        )
        return [self._row_to_task(r) for r in rows]

    def complete_task(self, task_id: int) -> BetTask | None:
        self._execute(
            "UPDATE bet_tasks SET is_completed = 1 WHERE id = ?", (task_id,)
        )
        row = self._fetch_one("SELECT * FROM bet_tasks WHERE id = ?", (task_id,))
        return self._row_to_task(row) if row else None

    def update_task(
        self, task_id: int, task_desc: str, target_qty: int
    ) -> BetTask | None:
        """编辑任务描述和目标数量 (不改 current_qty / is_completed)。

        若改 target_qty 后已 current_qty 达到, 自动设 is_completed=1;
        若未达到, 自动设 is_completed=0。
        """
        self._execute(
            "UPDATE bet_tasks SET task_desc = ?, target_qty = ?,"
            " is_completed = CASE WHEN current_qty >= ? THEN 1 ELSE 0 END"
            " WHERE id = ?",
            (task_desc, target_qty, target_qty, task_id),
        )
        row = self._fetch_one("SELECT * FROM bet_tasks WHERE id = ?", (task_id,))
        return self._row_to_task(row) if row else None

    def update_task_progress(self, task_id: int, delta: int) -> BetTask | None:
        """原子递增/递减任务进度 — 使用 SET x = x + ? (delta 可正负) 消除丢失更新

        is_completed 双向自动维护:
            达到 target → 1, 低于 target → 0;
            current_qty 下限 0 (MAX 防止减成负数)。
        is_extra 自动维护: current_qty > target_qty → 1, 否则 → 0。
        """
        self._execute(
            "UPDATE bet_tasks SET current_qty = MAX(0, current_qty + ?),"
            " is_completed = CASE"
            "   WHEN MAX(0, current_qty + ?) >= target_qty THEN 1"
            "   ELSE 0 END,"
            " is_extra = CASE"
            "   WHEN MAX(0, current_qty + ?) > target_qty THEN 1"
            "   ELSE 0 END"
            " WHERE id = ?",
            (delta, delta, delta, task_id),
        )
        row = self._fetch_one("SELECT * FROM bet_tasks WHERE id = ?", (task_id,))
        return self._row_to_task(row) if row else None

    def delete_task(self, task_id: int) -> None:
        self._execute("DELETE FROM bet_tasks WHERE id = ?", (task_id,))

    # ── 配置 CRUD ──

    def upsert_config(self, config: BetConfig) -> BetConfig:
        """原子 upsert — 使用 INSERT ON CONFLICT 消除 TOCTOU 竞态"""
        self._execute(
            """INSERT INTO bet_configs (week_start, base_reward, extra_reward, penalty,
               status, late_fee_per_day, late_start_date)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(week_start) DO UPDATE SET
               base_reward = excluded.base_reward,
               extra_reward = excluded.extra_reward,
               penalty = excluded.penalty,
               status = excluded.status,
               late_fee_per_day = excluded.late_fee_per_day,
               late_start_date = excluded.late_start_date""",
            (config.week_start, config.base_reward, config.extra_reward,
             config.penalty, config.status,
             config.late_fee_per_day, config.late_start_date),
        )
        row = self._fetch_one(
            "SELECT * FROM bet_configs WHERE week_start = ?", (config.week_start,)
        )
        if row:
            config.id = row["id"]
        return config

    def get_config(self, week_start: str) -> BetConfig | None:
        row = self._fetch_one(
            "SELECT * FROM bet_configs WHERE week_start = ?", (week_start,)
        )
        return self._row_to_config(row) if row else None

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> BetTask:
        return BetTask(
            id=row["id"],
            week_start=row["week_start"],
            task_desc=row["task_desc"],
            target_qty=row["target_qty"],
            current_qty=row["current_qty"],
            is_completed=row["is_completed"],
            is_extra=row["is_extra"],
        )

    @staticmethod
    def _row_to_config(row: sqlite3.Row) -> BetConfig:
        cols = row.keys()
        return BetConfig(
            id=row["id"],
            week_start=row["week_start"],
            base_reward=row["base_reward"],
            extra_reward=row["extra_reward"],
            penalty=row["penalty"],
            status=row["status"],
            late_fee_per_day=row["late_fee_per_day"] if "late_fee_per_day" in cols else 10.0,
            late_start_date=row["late_start_date"] if "late_start_date" in cols else None,
        )

    def get_late_fee_dates(self, week_start: str) -> set[str]:
        """返回已扣滞纳金的日期集合（用于去重）。"""
        from app.utils.config import LEDGER_TYPE_BET_LATE_FEE
        rows = self._fetch_all(
            "SELECT entry_date FROM ledger_entries"
            " WHERE week_start = ? AND type = ?",
            (week_start, LEDGER_TYPE_BET_LATE_FEE),
        )
        return {r["entry_date"] for r in rows}

    def get_unsettled_weeks(self) -> list[BetConfig]:
        """返回所有未完成结算的周配置 (active / late)。"""
        rows = self._fetch_all(
            "SELECT * FROM bet_configs WHERE status IN ('active', 'late')"
        )
        return [self._row_to_config(r) for r in rows]
