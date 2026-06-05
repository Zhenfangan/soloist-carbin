"""后端持久化与数据残留审计 — 30 天冷启动验证 + 事务原子性"""
from __future__ import annotations

import os
import sqlite3
import tempfile

from app.db import init_db, close_db
from app.utils.clock import SimulatedClock, set_clock
from app.services.event_bus import EventBus, set_event_bus
from app.repositories.settings_repo import SettingsRepo
from app.repositories.checkin_repo import CheckinRepo
from app.repositories.ledger_repo import LedgerRepo
from app.repositories.bet_repo import BetRepo
from app.services.checkin_service import CheckinService
from app.services.bet_service import BetService
from app.services.settings_service import SettingsService


def snapshot(db_path: str) -> dict[str, object]:
    """对数据库当前状态拍快照"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    snap: dict[str, object] = {
        "checkins_count": conn.execute("SELECT COUNT(*) FROM checkins").fetchone()[0],
        "ledger_count": conn.execute("SELECT COUNT(*) FROM ledger_entries").fetchone()[0],
        "ledger_total": conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM ledger_entries"
        ).fetchone()[0],
        "bet_tasks_count": conn.execute("SELECT COUNT(*) FROM bet_tasks").fetchone()[0],
        "bet_completed": conn.execute(
            "SELECT COUNT(*) FROM bet_tasks WHERE is_completed=1"
        ).fetchone()[0],
        "status_dist": dict(
            conn.execute(
                "SELECT status, COUNT(*) as cnt FROM checkins"
                " WHERE status IS NOT NULL GROUP BY status"
            ).fetchall()
        ),
    }
    conn.close()
    return snap


def rebuild_services(db_path: str):
    """模拟冷启动：重新创建所有 Service"""
    init_db(db_path)
    set_event_bus(EventBus())
    clock = SimulatedClock()
    set_clock(clock)
    sr = SettingsRepo(db_path)
    ss = SettingsService(sr)
    cs = CheckinService(CheckinRepo(db_path), sr)
    lr = LedgerRepo(db_path)
    br = BetRepo(db_path)
    bs = BetService(br, lr, sr)
    return clock, cs, bs


def run_day(clock, checkin_svc, date: str, scenario: str) -> None:
    """执行单日业务流"""
    if scenario == "normal":
        clock.set_date_and_time(date, "08:55")
        checkin_svc.check_in(date, "morning")
        clock.set_date_and_time(date, "12:05")
        checkin_svc.check_out(date, "morning")
        clock.set_date_and_time(date, "13:55")
        checkin_svc.check_in(date, "afternoon")
        clock.set_date_and_time(date, "18:05")
        checkin_svc.check_out(date, "afternoon")
    elif scenario == "absent":
        clock.set_date_and_time(date, "23:00")
        checkin_svc.mark_absent(date)
    elif scenario == "leave":
        clock.set_date_and_time(date, "08:30")
        checkin_svc.apply_leave(date, "all_day")
    elif scenario == "late":
        clock.set_date_and_time(date, "09:30")
        checkin_svc.check_in(date, "morning")
        clock.set_date_and_time(date, "12:05")
        checkin_svc.check_out(date, "morning")
        clock.set_date_and_time(date, "14:00")
        checkin_svc.check_in(date, "afternoon")
        clock.set_date_and_time(date, "18:05")
        checkin_svc.check_out(date, "afternoon")


def main():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    passed = 0
    failed = 0

    def check(desc: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [PASS] {desc}")
        else:
            failed += 1
            print(f"  [FAIL] {desc} — {detail}")

    # ============================================================
    # T-1: 30 天连续存取 + 3 次冷启动注入
    # ============================================================
    print("=== T-1: 30 天连续存取 + 3 次冷启动 ===")

    clock, checkin_svc, bet_svc = rebuild_services(db_path)

    scenarios = {
        1: "normal", 2: "absent", 3: "late", 4: "leave", 5: "normal",
        6: "normal", 7: "absent",
    }

    for day in range(1, 31):
        from datetime import datetime, timedelta
        d = datetime(2026, 6, 1) + timedelta(days=day - 1)
        date_str = d.strftime("%Y-%m-%d")
        # 按周循环场景
        dow = (day - 1) % 7 + 1
        scenario = scenarios.get(dow, "normal")
        run_day(clock, checkin_svc, date_str, scenario)

        # 每 10 天冷启动一次
        if day == 10:
            snap_before = snapshot(db_path)
            close_db()
            clock, checkin_svc, bet_svc = rebuild_services(db_path)
            snap_after = snapshot(db_path)

            for key in snap_before:
                before = snap_before[key]
                after = snap_after[key]
                ok = before == after
                check(f"Day {day} 冷启动后 {key} 一致", ok,
                      f"前: {before}, 后: {after}")

            print(f"  [INFO] Day {day} 冷启动完成")

        elif day == 20:
            snap_before = snapshot(db_path)
            close_db()
            clock, checkin_svc, bet_svc = rebuild_services(db_path)
            snap_after = snapshot(db_path)

            for key in snap_before:
                before = snap_before[key]
                after = snap_after[key]
                ok = before == after
                check(f"Day {day} 冷启动后 {key} 一致", ok,
                      f"前: {before}, 后: {after}")

            print(f"  [INFO] Day {day} 冷启动完成")

    # Day 30 最终完整性
    close_db()
    clock, checkin_svc, bet_svc = rebuild_services(db_path)

    # 验证 30 天数据
    for day in range(1, 31):
        d = datetime(2026, 6, 1) + timedelta(days=day - 1)
        date_str = d.strftime("%Y-%m-%d")
        ds = checkin_svc.get_today_status(date_str)
        check(f"Day {day} ({date_str}) periods 完整",
              len(ds.periods) == 3,
              f"实际: {len(ds.periods)}")

    # ============================================================
    # T-2: 事务原子性 — 崩溃回滚验证
    # ============================================================
    print("\n=== T-2: 事务原子性崩溃回滚 ===")
    fd2, db_path2 = tempfile.mkstemp(suffix=".db")
    os.close(fd2)
    clock2, checkin_svc2, bet_svc2 = rebuild_services(db_path2)

    # 创建任务和配置
    bet_svc2.set_week_config("2026-07-01", 50.0, 20.0, 30.0)
    task = bet_svc2.create_task("2026-07-01", "原子性测试任务", target_qty=3)
    bet_svc2.update_task_progress(task.id, 3)

    # 在事务内部 ledger 写入阶段模拟：直接测试事务的 BEGIN/COMMIT
    # 通过 BetRepo 的 transaction() 上下文管理器验证
    bet_repo = BetRepo(db_path2)
    ledger_repo = LedgerRepo(db_path2)

    # 在事务中写入然后主动回滚
    from app.models.ledger import LedgerEntry
    from app.utils.config import LEDGER_TYPE_BET_REWARD

    try:
        with bet_repo.transaction():
            ledger_repo.insert(LedgerEntry(
                entry_date="2026-07-07", week_start="2026-07-01",
                type=LEDGER_TYPE_BET_REWARD, amount=50.0,
                description="事务测试写入 1",
            ))
            ledger_repo.insert(LedgerEntry(
                entry_date="2026-07-07", week_start="2026-07-01",
                type=LEDGER_TYPE_BET_REWARD, amount=30.0,
                description="事务测试写入 2",
            ))
            raise RuntimeError("模拟事务中途崩溃")
    except RuntimeError:
        pass  # 预期异常

    # 断言回滚成功：两条 ledger 均未写入
    entries = ledger_repo.get_by_week("2026-07-01")
    check("事务回滚后 ledger 为空", len(entries) == 0,
          f"实际: {len(entries)} 条, 金额: {[e.amount for e in entries]}")

    # 正常事务提交验证
    with bet_repo.transaction():
        ledger_repo.insert(LedgerEntry(
            entry_date="2026-07-07", week_start="2026-07-01",
            type=LEDGER_TYPE_BET_REWARD, amount=100.0,
            description="事务测试正常写入",
        ))

    entries = ledger_repo.get_by_week("2026-07-01")
    check("事务正常提交后 ledger 有 1 条", len(entries) == 1,
          f"实际: {len(entries)} 条")
    if entries:
        check("正常提交金额正确", entries[0].amount == 100.0,
              f"实际: {entries[0].amount}")

    close_db()
    os.unlink(db_path2)

    # ============================================================
    # T-3: 真实磁盘文件最终完整性
    # ============================================================
    print("\n=== T-3: 原始 SQL 数据完整性 ===")
    raw_conn = sqlite3.connect(db_path)
    raw_conn.row_factory = sqlite3.Row

    # 正常签到/签退记录 checkin_time 不为 NULL（排除 leave/absent 状态）
    null_checkins = raw_conn.execute(
        "SELECT COUNT(*) FROM checkins WHERE checkin_time IS NULL"
        " AND status NOT IN ('leave', 'absent_morning', 'absent_afternoon', 'late')"
    ).fetchone()[0]
    check("正常记录 checkin_time 不为 NULL", null_checkins == 0,
          f"NULL 记录数: {null_checkins}")

    # 每条 checkin 记录 status 不为 NULL
    null_status = raw_conn.execute(
        "SELECT COUNT(*) FROM checkins WHERE status IS NULL"
    ).fetchone()[0]
    check("所有 checkin 记录 status 不为 NULL", null_status == 0,
          f"NULL 记录数: {null_status}")

    # 3 periods × 30 days = 90 条记录（morning/afternoon/evening）
    total = raw_conn.execute("SELECT COUNT(*) FROM checkins").fetchone()[0]
    check("30 天 checkin 记录数合理",
          total >= 60 and total <= 90,
          f"实际: {total} (预期 60-90)")

    # 无游离 ledger 记录（ledger 表仅有 0 条，未做对赌结算）
    ledger_cnt = raw_conn.execute(
        "SELECT COUNT(*) FROM ledger_entries"
    ).fetchone()[0]
    check("未结算时 ledger 为空", ledger_cnt == 0,
          f"实际: {ledger_cnt} 条")

    raw_conn.close()

    # ============================================================
    # T-4: WAL 文件验证
    # ============================================================
    print("\n=== T-4: WAL 文件验证 ===")
    wal_path = db_path + "-wal"
    wal_exists = os.path.exists(wal_path)
    # WAL 文件在正常 checkpoint 后可能为空，在活跃写入时存在
    print(f"  [INFO] WAL 文件存在: {wal_exists}")

    # 正常关闭后 WAL 应被 checkpoint
    close_db()
    wal_still_exists = os.path.exists(wal_path)
    # 关闭后 WAL 文件应消失或为空（取决于 SQLite 版本）
    print(f"  [INFO] close_db() 后 WAL: {wal_still_exists}")

    # ============================================================
    # 清理
    # ============================================================
    try:
        os.unlink(db_path)
    except PermissionError:
        pass

    print(f"\n=== 持久化审计测试完毕 ===")
    print(f"通过: {passed}, 失败: {failed}")
    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
