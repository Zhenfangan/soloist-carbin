"""设置参数 Repository — 键值对 CRUD"""

from __future__ import annotations

from app.repositories.base import BaseRepo


class SettingsRepo(BaseRepo):
    """设置参数数据访问"""

    def get(self, key: str) -> str | None:
        """读取单个设置项，未设返回 None"""
        row = self._fetch_one("SELECT value FROM settings WHERE key = ?", (key,))
        return row["value"] if row else None

    def set(self, key: str, value: str) -> None:
        """写入单个设置项"""
        self._execute(
            """INSERT INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))
               ON CONFLICT(key) DO UPDATE SET value = excluded.value,
               updated_at = excluded.updated_at""",
            (key, value),
        )

    def get_all(self) -> dict[str, str]:
        """读取全部设置项，返回 {key: value}"""
        rows = self._fetch_all("SELECT key, value FROM settings")
        return {row["key"]: row["value"] for row in rows}

    def batch_set(self, settings: dict[str, str]) -> None:
        """批量写入设置项"""
        for key, value in settings.items():
            self.set(key, value)
