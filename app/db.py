"""数据库初始化模块 — SQLite 建表 + 连接管理"""

from __future__ import annotations

import sqlite3
import threading

from app.utils.config import DB_PATH

DDL_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS checkins (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        checkin_date  TEXT NOT NULL,
        period        TEXT NOT NULL,
        checkin_time  TEXT,
        checkout_time TEXT,
        checkout_type TEXT DEFAULT 'manual',
        status        TEXT,
        is_shooting   INTEGER DEFAULT 0,
        created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at    TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(checkin_date, period)
    )""",
    """CREATE TABLE IF NOT EXISTS ledger_entries (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date    TEXT NOT NULL,
        week_start    TEXT,
        type          TEXT NOT NULL,
        amount        REAL NOT NULL,
        description   TEXT,
        reward_item   TEXT,
        reward_qty    INTEGER DEFAULT 1,
        fulfilled     INTEGER DEFAULT 0,
        source_id     INTEGER,
        created_at    TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS boyfriend_promises (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        promise_date  TEXT NOT NULL UNIQUE,
        reward_desc   TEXT NOT NULL,
        reward_qty    INTEGER DEFAULT 1,
        fulfilled     INTEGER DEFAULT 0,
        created_at    TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS bet_tasks (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        week_start    TEXT NOT NULL,
        task_desc     TEXT NOT NULL,
        target_qty    INTEGER DEFAULT 1,
        current_qty   INTEGER DEFAULT 0,
        is_completed  INTEGER DEFAULT 0,
        is_extra      INTEGER DEFAULT 0,
        created_at    TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS bet_configs (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        week_start        TEXT NOT NULL UNIQUE,
        base_reward       REAL NOT NULL,
        extra_reward      REAL NOT NULL,
        penalty           REAL NOT NULL,
        status            TEXT DEFAULT 'active',
        created_at        TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS shooting_days (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        shoot_date    TEXT NOT NULL UNIQUE,
        reward_desc   TEXT,
        status        TEXT DEFAULT 'active',
        created_at    TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS shooting_reflections (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        shoot_date      TEXT NOT NULL UNIQUE,
        content         TEXT,
        location        TEXT,
        was_smooth      TEXT,
        thoughts        TEXT,
        summary         TEXT,
        created_at      TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS task_items (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        task_date     TEXT NOT NULL,
        content       TEXT NOT NULL,
        is_completed  INTEGER DEFAULT 0,
        sort_order    INTEGER DEFAULT 0,
        created_at    TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS settings (
        key           TEXT PRIMARY KEY,
        value         TEXT NOT NULL,
        updated_at    TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS attendance_streak (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        current_streak    INTEGER DEFAULT 0,
        last_checkin_date TEXT,
        updated_at        TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
]

# 线程本地连接
_local = threading.local()


def get_db(path: str | None = None) -> sqlite3.Connection:
    """获取当前线程的 SQLite 连接（自动初始化表结构）"""
    db_path = path or DB_PATH
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
        _init_tables(conn)
    return conn


def _init_tables(conn: sqlite3.Connection) -> None:
    """执行建表 DDL"""
    for ddl in DDL_STATEMENTS:
        conn.execute(ddl)
    conn.commit()


def init_db(path: str | None = None) -> None:
    """显式初始化数据库（建表），幂等。"""
    conn = get_db(path)
    conn.commit()


def close_db() -> None:
    """关闭当前线程的数据库连接"""
    conn: sqlite3.Connection | None = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None
