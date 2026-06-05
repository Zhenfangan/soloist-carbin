"""Repository 基类 — 统一 SQLite 连接管理"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from collections.abc import Generator

from app.db import get_db

# 按连接 id 追踪活跃事务（sqlite3.Connection 是 C 扩展，不支持动态属性）
_txn_conn_ids: set[int] = set()


class BaseRepo:
    """所有 Repository 的基类，提供数据库连接和通用方法"""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path

    @property
    def conn(self) -> sqlite3.Connection:
        return get_db(self._db_path)

    @staticmethod
    def _in_transaction(conn: sqlite3.Connection) -> bool:
        return id(conn) in _txn_conn_ids

    def _execute(self, sql: str, params: tuple[object, ...] = ()) -> sqlite3.Cursor:
        """执行写操作"""
        cursor = self.conn.execute(sql, params)
        if not self._in_transaction(self.conn):
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
        if not self._in_transaction(self.conn):
            self.conn.commit()
        lastrowid = cursor.lastrowid
        assert lastrowid is not None
        return lastrowid

    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        """显式事务边界 — 用于多步写入需保证原子性的场景。

        同连接的所有 Repo 实例共享事务标志。
        使用期间会抑制所有 Repo 的自动 commit，
        commit 由上下文管理器在退出时统一执行（异常时回滚）。
        """
        conn = self.conn
        cid = id(conn)
        _txn_conn_ids.add(cid)
        conn.execute("BEGIN")
        try:
            yield
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            _txn_conn_ids.discard(cid)
