"""DB 外部备份/恢复 — 让打卡记录在卸载重装后不丢。

安卓私有目录卸载即清空, 把 DB 快照备份到卸载不清的外部存储, 重装后
若私有库缺失就从外部恢复。核心逻辑用可注入路径, 脱离安卓也能测。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.utils import db_backup


def _make_db(path: Path, value: int, wal: bool = False) -> sqlite3.Connection | None:
    conn = sqlite3.connect(str(path))
    if wal:
        conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE t(x INTEGER)")
    conn.execute("INSERT INTO t VALUES (?)", (value,))
    conn.commit()
    if wal:
        return conn  # 保持连接打开, 数据仍在 WAL 里未 checkpoint
    conn.close()
    return None


def _read(path: Path) -> int:
    conn = sqlite3.connect(str(path))
    try:
        return int(conn.execute("SELECT x FROM t").fetchone()[0])
    finally:
        conn.close()


def test_backup_creates_snapshot(tmp_path: Path) -> None:
    live = tmp_path / "live.db"
    _make_db(live, 42)
    dest = tmp_path / "ext" / "soloist_backup.db"

    assert db_backup.backup(str(live), dest_path=str(dest)) is True
    assert dest.exists()
    assert _read(dest) == 42


def test_backup_captures_wal_changes_with_open_conn(tmp_path: Path) -> None:
    """真机活库是 WAL 且连接常开; 快照必须含 WAL 里尚未 checkpoint 的改动。"""
    live = tmp_path / "live.db"
    conn = _make_db(live, 99, wal=True)
    dest = tmp_path / "ext" / "soloist_backup.db"
    try:
        assert db_backup.backup(str(live), dest_path=str(dest)) is True
        assert _read(dest) == 99
    finally:
        if conn is not None:
            conn.close()


def test_restore_when_live_missing(tmp_path: Path) -> None:
    backup = tmp_path / "ext" / "soloist_backup.db"
    backup.parent.mkdir(parents=True)
    _make_db(backup, 7)
    live = tmp_path / "priv" / "live.db"  # 不存在(模拟重装后私有目录空)

    assert db_backup.restore_if_missing(str(live), backup_path=str(backup)) is True
    assert live.exists()
    assert _read(live) == 7


def test_restore_skips_when_live_exists(tmp_path: Path) -> None:
    """私有库已存在(正常更新, 数据未丢) → 绝不用旧备份覆盖。"""
    live = tmp_path / "live.db"
    _make_db(live, 1)
    backup = tmp_path / "ext" / "soloist_backup.db"
    backup.parent.mkdir(parents=True)
    _make_db(backup, 2)

    assert db_backup.restore_if_missing(str(live), backup_path=str(backup)) is False
    assert _read(live) == 1  # 未被备份覆盖


def test_restore_skips_when_no_backup(tmp_path: Path) -> None:
    live = tmp_path / "live.db"  # 不存在
    backup = tmp_path / "ext" / "soloist_backup.db"  # 也不存在
    assert db_backup.restore_if_missing(str(live), backup_path=str(backup)) is False


def test_backup_missing_live_is_noop(tmp_path: Path) -> None:
    live = tmp_path / "nope.db"
    dest = tmp_path / "ext" / "soloist_backup.db"
    assert db_backup.backup(str(live), dest_path=str(dest)) is False


def test_backup_then_restore_roundtrip(tmp_path: Path) -> None:
    """完整闭环: 备份 → 删私有库(模拟卸载) → 恢复 → 数据一致。"""
    live = tmp_path / "live.db"
    _make_db(live, 2026)
    dest = tmp_path / "ext" / "soloist_backup.db"

    assert db_backup.backup(str(live), dest_path=str(dest)) is True
    live.unlink()  # 模拟卸载清空私有目录
    assert db_backup.restore_if_missing(str(live), backup_path=str(dest)) is True
    assert _read(live) == 2026
