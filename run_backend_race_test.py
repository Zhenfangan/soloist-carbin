"""后端竞态条件与幂等性轰炸测试"""
from __future__ import annotations

import concurrent.futures
import os
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


def main():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(db_path)
    clock = SimulatedClock()
    set_clock(clock)
    set_event_bus(EventBus())

    settings_repo = SettingsRepo(db_path)
    settings_svc = SettingsService(settings_repo)
    checkin_repo = CheckinRepo(db_path)
    checkin_svc = CheckinService(checkin_repo, settings_repo)
    ledger_repo = LedgerRepo(db_path)
    bet_repo = BetRepo(db_path)
    bet_svc = BetService(bet_repo, ledger_repo, settings_repo)

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
    # T-1: 10 线程并发轰炸同一打卡时段
    # ============================================================
    print("\n=== T-1: 10 线程并发打卡 (2026-06-01 morning) ===")
    clock.set_date_and_time("2026-06-01", "09:00")

    def bomb_checkin(i: int):
        try:
            return checkin_svc.check_in("2026-06-01", "morning")
        except Exception as e:
            return e

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(bomb_checkin, i) for i in range(10)]
        results = [f.result() for f in futures]

    successes = [r for r in results if not isinstance(r, Exception)]
    exceptions = [r for r in results if isinstance(r, Exception)]
    check("10 次并发至少 1 次成功", len(successes) >= 1, f"成功: {len(successes)}")
    check("无未捕获异常导致进程崩溃", len(exceptions) == 0,
          f"异常数: {len(exceptions)}, 类型: {[type(e).__name__ for e in exceptions]}")

    # DB 幂等性验证
    records = checkin_repo.get_all_by_date("2026-06-01")
    morning_records = [r for r in records if r.period == "morning"]
    check("DB 中 morning 记录仅 1 条", len(morning_records) == 1,
          f"实际: {len(morning_records)}")
    if morning_records:
        check("checkin_time 不为 NULL", morning_records[0].checkin_time is not None)
        check("checkin_time 为 09:00:00", morning_records[0].checkin_time == "09:00:00",
              f"实际: {morning_records[0].checkin_time}")

    # ============================================================
    # T-2: 并发 +1 任务进度 (原子递增验证)
    # ============================================================
    print("\n=== T-2: 10 线程并发递增任务进度 ===")
    task = bet_svc.create_task("2026-06-01", "并发测试任务", target_qty=10)
    task_id = task.id
    check("任务创建成功", task_id is not None)

    def bomb_increment(i: int):
        try:
            return bet_svc.update_task_progress(task_id, 1)
        except Exception as e:
            return e

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(bomb_increment, i) for i in range(10)]
        results = [f.result() for f in futures]

    exceptions = [r for r in results if isinstance(r, Exception)]
    check("10 次并发递增无异常", len(exceptions) == 0,
          f"异常数: {len(exceptions)}, 类型: {[type(e).__name__ for e in exceptions]}")

    final_task = bet_repo.get_tasks_by_week("2026-06-01")[0]
    check("并发递增后 current_qty 精确等于 10（无丢失更新）",
          final_task.current_qty == 10,
          f"实际: {final_task.current_qty}")

    # ============================================================
    # T-3: settle_week 重复调用幂等性
    # ============================================================
    print("\n=== T-3: settle_week 重复调用幂等性 ===")
    # 先配置并结算
    bet_svc.set_week_config("2026-06-08", 50.0, 20.0, 30.0)
    first = bet_svc.settle_week("2026-06-08")
    check("第一次结算正常返回", first is not None)

    # 立即第二次结算同一周
    second = bet_svc.settle_week("2026-06-08")
    check("第二次结算不抛异常", second is not None)
    check("第二次结算 net 为 0", second.net == 0.0, f"实际: {second.net}")
    check("第二次结算 ledger_entries 为空", len(second.ledger_entries) == 0,
          f"实际: {len(second.ledger_entries)}")

    # 账本中无重复记录
    week_08_entries = ledger_repo.get_by_week("2026-06-08")
    check("ledger 中 06-08 周无重复记录", len(week_08_entries) <= 1,
          f"实际: {len(week_08_entries)}")

    # ============================================================
    # T-4: UNIQUE 约束完备性扫描
    # ============================================================
    print("\n=== T-4: Schema UNIQUE 约束完备性 ===")
    import sqlite3
    raw_conn = sqlite3.connect(db_path)
    raw_conn.row_factory = sqlite3.Row

    tables_to_check = {
        "checkins": ["checkin_date", "period"],
        "bet_configs": ["week_start"],
        "settings": ["key"],
        "boyfriend_promises": ["promise_date"],
        "shooting_days": ["shoot_date"],
        "shooting_reflections": ["shoot_date"],
    }

    for table, expected_cols in tables_to_check.items():
        # 查询建表 SQL
        row = raw_conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        if row:
            ddl = row["sql"].upper() if row["sql"] else ""
            # 检查 PRIMARY KEY（隐含 UNIQUE）
            has_pk = f"PRIMARY KEY" in ddl and any(
                col.upper() in ddl for col in expected_cols
            )
            # 检查 UNIQUE 约束
            has_unique = "UNIQUE" in ddl
            ok = has_pk or has_unique
            check(f"{table} 有 UNIQUE/PRIMARY KEY 约束", ok,
                  f"DDL 摘要: {ddl[:120]}")
        else:
            check(f"{table} 表存在", False, "表不存在")

    # bet_tasks 缺少 UNIQUE(week_start, task_desc) — 记录为已知风险
    row = raw_conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='bet_tasks'",
    ).fetchone()
    if row and row["sql"]:
        has_unique = "UNIQUE" in row["sql"].upper()
        check("bet_tasks 有 UNIQUE 约束",
              has_unique,
              "建议添加 UNIQUE(week_start, task_desc) 防止重复任务")

    raw_conn.close()

    # ============================================================
    # T-5: busy_timeout 验证
    # ============================================================
    print("\n=== T-5: busy_timeout 配置验证 ===")
    raw_conn2 = sqlite3.connect(db_path)
    try:
        timeout = raw_conn2.execute("PRAGMA busy_timeout").fetchone()[0]
        check("busy_timeout >= 3000ms", timeout >= 3000, f"实际: {timeout}ms")
    finally:
        raw_conn2.close()

    # ============================================================
    # 清理
    # ============================================================
    close_db()
    try:
        os.unlink(db_path)
    except PermissionError:
        pass  # Windows 可能延迟释放文件句柄

    print(f"\n=== 竞态条件测试完毕 ===")
    print(f"通过: {passed}, 失败: {failed}")
    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
