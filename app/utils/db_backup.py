"""数据库外部备份 / 恢复 —— 让打卡记录在卸载重装后不丢。

背景: 安卓私有目录(活库 soloist.db 所在)在卸载时被系统清空, 重装即丢
全部打卡数据。照片之所以能留是因为写在卸载不清的外部共享存储。这里给
DB 加同样的保命机制:

- 活库始终在私有目录跑(WAL 模式在内部存储稳定、快)。
- 备份: 用 SQLite Online Backup API 生成一致性快照到本地临时文件(含 WAL
  里尚未 checkpoint 的改动), 再"纯文件字节拷贝"到外部存储。绝不在外部
  路径上开 SQLite 连接 —— 外部是 FUSE 文件系统, WAL 的共享内存/文件锁
  在上面常出问题。
- 恢复: 启动时若私有活库不存在(重装后)但外部有备份, 拷回私有目录。

外部路径复用照片那套已验证可写的目录(get_pictures_dir)。桌面端无"卸载
清空"概念, 外部路径返回 None, 备份/恢复全部空操作。
"""

from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path

from kivy.logger import Logger

_BACKUP_NAME = "soloist_backup.db"


def _external_backup_path() -> Path | None:
    """外部备份文件路径(仅安卓)。桌面返回 None —— 数据不会被卸载清空, 无需备份。"""
    try:
        from app.utils.storage import _platform, get_pictures_dir
        if _platform() != "android":
            return None
        return get_pictures_dir() / _BACKUP_NAME
    except Exception:
        return None


def backup(live_db_path: str, dest_path: str | None = None) -> bool:
    """把活库快照备份到外部存储。dest_path 仅供测试注入; 生产留空走外部路径。

    返回是否成功备份。活库不存在 / 无外部路径(桌面) → False 且不报错。
    """
    live = Path(live_db_path)
    if not live.exists():
        return False
    dest = Path(dest_path) if dest_path else _external_backup_path()
    if dest is None:
        return False

    # 1) 用 backup API 在本地生成一致性快照(内部存储, 可靠; 含 WAL 中的改动)
    local_tmp = live.with_name(live.name + ".bak.tmp")
    src: sqlite3.Connection | None = None
    dst: sqlite3.Connection | None = None
    try:
        src = sqlite3.connect(str(live))
        src.execute("PRAGMA busy_timeout=5000")
        dst = sqlite3.connect(str(local_tmp))
        with dst:
            src.backup(dst)
    except Exception as e:  # noqa: BLE001
        Logger.error(f"DBBackup: 生成快照失败 {e!r}")
        _safe_unlink(local_tmp)
        return False
    finally:
        for c in (dst, src):
            if c is not None:
                try:
                    c.close()
                except Exception:  # noqa: BLE001
                    pass

    # 2) 纯文件拷贝到外部(先临时文件再原子替换, 避免拷到一半损坏备份)
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        ext_tmp = dest.with_name(dest.name + ".tmp")
        shutil.copy2(local_tmp, ext_tmp)
        os.replace(ext_tmp, dest)  # 同目录(外部)内替换, 原子
        Logger.info(f"DBBackup: 已备份打卡数据 → {dest}")
        return True
    except Exception as e:  # noqa: BLE001
        Logger.error(f"DBBackup: 拷贝到外部失败 {e!r}")
        return False
    finally:
        _safe_unlink(local_tmp)


def restore_if_missing(live_db_path: str, backup_path: str | None = None) -> bool:
    """启动时: 若私有活库缺失但外部有备份, 恢复。返回是否发生恢复。

    活库已存在(正常更新, 数据未丢) → 绝不覆盖, 返回 False。
    """
    live = Path(live_db_path)
    if live.exists():
        return False
    backup_file = Path(backup_path) if backup_path else _external_backup_path()
    if backup_file is None or not backup_file.exists():
        return False
    try:
        live.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_file, live)
        Logger.info(f"DBBackup: 从外部备份恢复打卡数据 {backup_file} → {live}")
        return True
    except Exception as e:  # noqa: BLE001
        Logger.error(f"DBBackup: 恢复失败 {e!r}")
        return False


def _safe_unlink(p: Path) -> None:
    try:
        p.unlink()
    except Exception:  # noqa: BLE001
        pass
