"""同步状态记录 Repository"""

from __future__ import annotations

from typing import Any

from app.repositories.base import BaseRepo


class SyncRepo(BaseRepo):
    """同步状态追踪"""

    def set_last_backup(self, timestamp: str) -> None:
        self._execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
            ("_last_backup", timestamp),
        )

    def get_last_backup(self) -> str | None:
        row = self._fetch_one("SELECT value FROM settings WHERE key = ?", ("_last_backup",))
        if row is None:
            return None
        val = row["value"]
        assert isinstance(val, str)
        return val

    def export_all_data(self) -> dict[str, list[dict[str, Any]]]:
        """导出所有表数据为 JSON 格式"""
        tables = [
            "checkins", "ledger_entries", "boyfriend_promises",
            "bet_tasks", "bet_configs", "shooting_days",
            "shooting_reflections", "task_items", "settings",
            "attendance_streak",
        ]
        result: dict[str, list[dict[str, Any]]] = {}
        for table in tables:
            rows = self._fetch_all(f"SELECT * FROM {table}")
            result[table] = [dict(r) for r in rows]
        return result

    def import_all_data(self, data: dict[str, list[dict[str, Any]]]) -> None:
        """从 JSON 格式导入所有表数据"""
        for table, rows in data.items():
            for row in rows:
                columns = ", ".join(row.keys())
                placeholders = ", ".join("?" for _ in row)
                values = tuple(row.values())
                self._execute(
                    f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})",
                    values,
                )
