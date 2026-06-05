"""后端 I/O 耗时剖析 — 主线程阻塞审计"""
from __future__ import annotations

import os
import tempfile
import time

from app.db import init_db, close_db
from app.utils.clock import SimulatedClock, set_clock
from app.services.event_bus import EventBus, set_event_bus
from app.repositories.settings_repo import SettingsRepo
from app.repositories.checkin_repo import CheckinRepo
from app.repositories.ledger_repo import LedgerRepo
from app.repositories.bet_repo import BetRepo
from app.repositories.sync_repo import SyncRepo
from app.services.checkin_service import CheckinService
from app.services.bet_service import BetService
from app.services.report_service import ReportService
from app.services.sync_service import SyncService
from app.services.settings_service import SettingsService
from app.services.history_service import HistoryService


def fill_database(db_path: str, days: int = 365) -> None:
    """填充 N 天的模拟数据"""
    clock = SimulatedClock()
    from datetime import datetime, timedelta

    cs = CheckinService(CheckinRepo(db_path), SettingsRepo(db_path))
    bs = BetService(BetRepo(db_path), LedgerRepo(db_path), SettingsRepo(db_path))

    for i in range(days):
        d = datetime(2026, 1, 1) + timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")
        dow = d.weekday()  # 0=Mon, 6=Sun

        if dow < 5:  # 工作日
            clock.set_date_and_time(date_str, "08:55")
            cs.check_in(date_str, "morning")
            clock.set_date_and_time(date_str, "12:05")
            cs.check_out(date_str, "morning")
            clock.set_date_and_time(date_str, "13:55")
            cs.check_in(date_str, "afternoon")
            clock.set_date_and_time(date_str, "18:05")
            cs.check_out(date_str, "afternoon")

        # 每周创建对赌任务
        if dow == 0:  # 周一
            week_start = date_str
            bs.set_week_config(week_start, 50.0, 20.0, 30.0)
            for j in range(3):
                t = bs.create_task(week_start, f"周任务-{j+1}", target_qty=3)
                bs.update_task_progress(t.id, 3)
            bs.settle_week(week_start)


def measure(name: str, fn, iterations: int = 10) -> dict[str, float]:
    """测量函数执行耗时，返回 p50/p99"""
    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)
    times.sort()
    p50 = times[len(times) // 2]
    p99 = times[min(int(len(times) * 0.99), len(times) - 1)]
    return {"name": name, "p50_ms": p50, "p99_ms": p99, "min_ms": times[0], "max_ms": times[-1]}


def main():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(db_path)
    clock = SimulatedClock()
    set_clock(clock)
    set_event_bus(EventBus())

    passed = 0
    failed = 0
    results: list[dict[str, float]] = []

    def check(desc: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [PASS] {desc}")
        else:
            failed += 1
            print(f"  [FAIL] {desc} — {detail}")

    print("=== 填充 365 天模拟数据 ===")
    start = time.perf_counter()
    fill_database(db_path, 365)
    fill_time = (time.perf_counter() - start) * 1000
    print(f"  [INFO] 365 天数据填充耗时: {fill_time:.0f}ms")

    # 重建 Service（冷启动后）
    sr = SettingsRepo(db_path)
    cr = CheckinRepo(db_path)
    lr = LedgerRepo(db_path)
    br = BetRepo(db_path)
    synr = SyncRepo(db_path)

    cs = CheckinService(cr, sr)
    bs = BetService(br, lr, sr)
    ss = SyncService(synr)
    rs = ReportService(cr, lr, None)
    hs = HistoryService(cr, lr, None)

    FRAME_BUDGET_MS = 16.0  # Kivy 60fps 帧预算
    WARN_THRESHOLD_MS = 32.0  # 2 帧警告
    CRITICAL_THRESHOLD_MS = 100.0  # 紧急阈值

    # ============================================================
    # T-1: export_all_data() 耗时
    # ============================================================
    print("\n=== T-1: 全量导出耗时 ===")
    r = measure("export_all_data", lambda: synr.export_all_data(), 5)
    results.append(r)
    print(f"  [INFO] p50={r['p50_ms']:.1f}ms, p99={r['p99_ms']:.1f}ms, max={r['max_ms']:.1f}ms")
    check("export p50 < 200ms", r["p50_ms"] < 200, f"p50={r['p50_ms']:.1f}ms")
    check("export p99 < 500ms", r["p99_ms"] < 500, f"p99={r['p99_ms']:.1f}ms")

    # ============================================================
    # T-2: import_all_data() 耗时
    # ============================================================
    print("\n=== T-2: 全量导入耗时 ===")
    export_data = synr.export_all_data()

    r = measure("import_all_data", lambda: synr.import_all_data(export_data), 3)
    results.append(r)
    print(f"  [INFO] p50={r['p50_ms']:.1f}ms, p99={r['p99_ms']:.1f}ms, max={r['max_ms']:.1f}ms")
    check("import p50 < 200ms（事务批量优化后）",
          r["p50_ms"] < 200, f"p50={r['p50_ms']:.1f}ms")
    check("import p99 < 500ms",
          r["p99_ms"] < 500, f"p99={r['p99_ms']:.1f}ms")

    # ============================================================
    # T-3: generate_and_save() 耗时
    # ============================================================
    print("\n=== T-3: 报表生成耗时 ===")
    r = measure("generate_and_save", lambda: rs.generate_and_save("2026-06-15"), 5)
    results.append(r)
    print(f"  [INFO] p50={r['p50_ms']:.1f}ms, p99={r['p99_ms']:.1f}ms, max={r['max_ms']:.1f}ms")
    check("报表生成 p50 < 50ms", r["p50_ms"] < 50, f"p50={r['p50_ms']:.1f}ms")
    check("报表生成 p99 < 100ms", r["p99_ms"] < 100, f"p99={r['p99_ms']:.1f}ms")

    # ============================================================
    # T-4: 常规 Service 方法耗时（帧预算对比）
    # ============================================================
    print("\n=== T-4: 常规方法帧预算对比 ===")
    clock.set_date_and_time("2026-07-01", "09:00")

    r = measure("check_in", lambda: cs.check_in("2026-07-01", "morning"), 20)
    results.append(r)
    check(f"check_in p50 < {FRAME_BUDGET_MS}ms",
          r["p50_ms"] < FRAME_BUDGET_MS, f"p50={r['p50_ms']:.1f}ms")

    r = measure("check_out", lambda: cs.check_out("2026-07-01", "morning"), 20)
    results.append(r)
    check(f"check_out p50 < {FRAME_BUDGET_MS}ms",
          r["p50_ms"] < FRAME_BUDGET_MS, f"p50={r['p50_ms']:.1f}ms")

    r = measure("get_today_status", lambda: cs.get_today_status("2026-06-15"), 20)
    results.append(r)
    check(f"get_today_status p50 < {FRAME_BUDGET_MS}ms",
          r["p50_ms"] < FRAME_BUDGET_MS, f"p50={r['p50_ms']:.1f}ms")

    r = measure("get_week_view", lambda: hs.get_week_view("2026-06-01"), 10)
    results.append(r)
    check(f"get_week_view p50 < {FRAME_BUDGET_MS}ms",
          r["p50_ms"] < FRAME_BUDGET_MS, f"p50={r['p50_ms']:.1f}ms")

    r = measure("settle_week", lambda: bs.settle_week("2026-07-06"), 5)
    results.append(r)
    check(f"settle_week p50 < {WARN_THRESHOLD_MS}ms",
          r["p50_ms"] < WARN_THRESHOLD_MS, f"p50={r['p50_ms']:.1f}ms")

    # ============================================================
    # T-5: 耗时汇总报告
    # ============================================================
    print("\n=== T-5: 耗时汇总 ===")
    print(f"  {'方法':<25} {'p50(ms)':>8} {'p99(ms)':>8} {'评级':>8}")
    print(f"  {'-'*49}")

    for r in results:
        name = r["name"]
        p50 = r["p50_ms"]
        p99 = r["p99_ms"]
        if p99 < FRAME_BUDGET_MS:
            grade = "安全"
        elif p99 < WARN_THRESHOLD_MS:
            grade = "注意"
        elif p99 < CRITICAL_THRESHOLD_MS:
            grade = "警告"
        else:
            grade = "危险"
        print(f"  {name:<25} {p50:>8.1f} {p99:>8.1f} {grade:>8}")

    # 断言无"危险"级方法
    danger = [r for r in results if r["p99_ms"] >= CRITICAL_THRESHOLD_MS]
    check("无方法 p99 超过 100ms 紧急阈值",
          len(danger) == 0,
          f"危险方法: {[r['name'] for r in danger]}")

    # ============================================================
    # 清理
    # ============================================================
    close_db()
    os.unlink(db_path)

    print(f"\n=== I/O 耗时剖析完毕 ===")
    print(f"通过: {passed}, 失败: {failed}")
    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
