"""Repository 基类 — 统一 SQLite 连接管理"""

from __future__ import annotations

import sqlite3

from app.db import get_db


class BaseRepo:
    """所有 Repository 的基类，提供数据库连接和通用方法"""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path

    @property
    def conn(self) -> sqlite3.Connection:
        return get_db(self._db_path)

    def _execute(self, sql: str, params: tuple[object, ...] = ()) -> sqlite3.Cursor:
        """执行写操作"""
        cursor = self.conn.execute(sql, params)
        self.conn.commit()
        return cursor

    def _fetch_one(self, sql: str, params: tuple[object, ...] = ()) -> sqlite3.Row | None:
        """查询单条记录"""
        row = self.conn.execute(sql, params).fetchone()
        return row if row is not None else None

    def _fetch_all(self, sql: str, params: tuple[object, ...] = ()) -> list[sqlite3.Row]:
        """查询多条记录"""
        return self.conn.execute(sql, params).fetchall()

    def _insert(self, sql: str, params: tuple[object, ...] = ()) -> int:
        """插入并返回 lastrowid"""
        cursor = self.conn.execute(sql, params)
        self.conn.commit()
        lastrowid = cursor.lastrowid
        assert lastrowid is not None
        return lastrowid
