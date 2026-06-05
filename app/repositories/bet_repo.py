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

    def update_task_progress(self, task_id: int, current_qty: int) -> BetTask | None:
        """原子递增任务进度 — 使用 SET x = x + ? 消除丢失更新"""
        self._execute(
            "UPDATE bet_tasks SET current_qty = current_qty + ?,"
            " is_completed = CASE WHEN current_qty + ? >= target_qty THEN 1 ELSE is_completed END"
            " WHERE id = ?",
            (current_qty, current_qty, task_id),
        )
        row = self._fetch_one("SELECT * FROM bet_tasks WHERE id = ?", (task_id,))
        return self._row_to_task(row) if row else None

    def delete_task(self, task_id: int) -> None:
        self._execute("DELETE FROM bet_tasks WHERE id = ?", (task_id,))

    # ── 配置 CRUD ──

    def upsert_config(self, config: BetConfig) -> BetConfig:
        """原子 upsert — 使用 INSERT ON CONFLICT 消除 TOCTOU 竞态"""
        self._execute(
            """INSERT INTO bet_configs (week_start, base_reward, extra_reward, penalty, status)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(week_start) DO UPDATE SET
               base_reward = excluded.base_reward,
               extra_reward = excluded.extra_reward,
               penalty = excluded.penalty,
               status = excluded.status""",
            (config.week_start, config.base_reward, config.extra_reward,
             config.penalty, config.status),
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
        return BetConfig(
            id=row["id"],
            week_start=row["week_start"],
            base_reward=row["base_reward"],
            extra_reward=row["extra_reward"],
            penalty=row["penalty"],
            status=row["status"],
        )
