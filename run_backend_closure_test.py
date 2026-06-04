"""后端全生命周期闭环测试 — SimulatedClock 驱动一周业务流"""
from __future__ import annotations

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
from app.services.history_service import HistoryService
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
    checkin_svc = CheckinService(CheckinRepo(db_path), settings_repo)
    ledger_repo = LedgerRepo(db_path)
    bet_svc = BetService(BetRepo(db_path), ledger_repo, settings_repo)
    history_svc = HistoryService(CheckinRepo(db_path), ledger_repo, None)

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
    # Story-0: 环境校验
    # ============================================================
    print("\n=== Story-0: 环境校验 ===")

    ms = settings_svc.get("morning_start")
    check("morning_start 默认值", ms == "09:00", f"实际: {ms}")
    ae = settings_svc.get("afternoon_end")
    check("afternoon_end 默认值", ae == "18:00", f"实际: {ae}")

    # ============================================================
    # Story-1: 周一正常打卡 (2026-06-01)
    # ============================================================
    print("\n=== Story-1: 周一正常打卡 2026-06-01 ===")

    # 上午签到
    clock.set_date_and_time("2026-06-01", "08:55")
    r = checkin_svc.check_in("2026-06-01", "morning")
    check("上午签到 normal", r.status == "normal", f"实际: {r.status}")
    check("上午签到时间 08:55:00", r.checkin_time == "08:55:00", f"实际: {r.checkin_time}")

    # 上午签退
    clock.set_date_and_time("2026-06-01", "12:05")
    r = checkin_svc.check_out("2026-06-01", "morning")
    check("上午签退 normal", r.status == "normal", f"实际: {r.status}")
    check("上午签退时间 12:05:00", r.checkout_time == "12:05:00", f"实际: {r.checkout_time}")

    # 下午签到
    clock.set_date_and_time("2026-06-01", "13:55")
    r = checkin_svc.check_in("2026-06-01", "afternoon")
    check("下午签到 normal", r.status == "normal", f"实际: {r.status}")

    # 下午签退
    clock.set_date_and_time("2026-06-01", "18:05")
    r = checkin_svc.check_out("2026-06-01", "afternoon")
    check("下午签退 normal", r.status == "normal", f"实际: {r.status}")

    # ============================================================
    # Story-2: 周二全部旷工 (2026-06-02)
    # ============================================================
    print("\n=== Story-2: 周二旷工 2026-06-02 ===")

    clock.set_date_and_time("2026-06-02", "23:00")
    results = checkin_svc.mark_absent("2026-06-02")
    periods_absent = [r.period for r in results]
    check("包含 morning 旷工", "morning" in periods_absent, f"实际: {periods_absent}")
    check("包含 afternoon 旷工", "afternoon" in periods_absent, f"实际: {periods_absent}")

    day_status = checkin_svc.get_today_status("2026-06-02")
    morning_ps = next(p for p in day_status.periods if p.period == "morning")
    afternoon_ps = next(p for p in day_status.periods if p.period == "afternoon")
    check("morning 状态 absent_morning", morning_ps.status == "absent_morning",
          f"实际: {morning_ps.status}")
    check("afternoon 状态 absent_afternoon", afternoon_ps.status == "absent_afternoon",
          f"实际: {afternoon_ps.status}")

    # ============================================================
    # Story-3: 周三上午迟到、下午早退 (2026-06-03)
    # ============================================================
    print("\n=== Story-3: 周三迟到+早退 2026-06-03 ===")

    # 上午迟到签到
    clock.set_date_and_time("2026-06-03", "09:30")
    r = checkin_svc.check_in("2026-06-03", "morning")
    check("上午签到 late", r.status == "late", f"实际: {r.status}")

    # 上午早退签退
    clock.set_date_and_time("2026-06-03", "11:30")
    r = checkin_svc.check_out("2026-06-03", "morning")
    check("上午签退 early_leave 且保留 late", r.status == "late",
          f"实际: {r.status} (迟到标记应被保留)")

    # 下午正常签到
    clock.set_date_and_time("2026-06-03", "14:00")
    r = checkin_svc.check_in("2026-06-03", "afternoon")
    check("下午签到 normal", r.status == "normal", f"实际: {r.status}")

    # 下午早退签退
    clock.set_date_and_time("2026-06-03", "17:00")
    r = checkin_svc.check_out("2026-06-03", "afternoon")
    check("下午签退 early_leave", r.status == "early_leave", f"实际: {r.status}")

    # ============================================================
    # Story-4: 周四请假 (2026-06-04)
    # ============================================================
    print("\n=== Story-4: 周四请假 2026-06-04 ===")

    clock.set_date_and_time("2026-06-04", "08:30")
    options = checkin_svc.get_leave_options("2026-06-04", "08:30")
    check("包含 morning 选项", "morning" in options, f"实际: {options}")
    check("包含 afternoon 选项", "afternoon" in options, f"实际: {options}")
    check("包含 all_day 选项", "all_day" in options, f"实际: {options}")

    leave_results = checkin_svc.apply_leave("2026-06-04", "all_day")
    check("返回 2 条记录", len(leave_results) == 2, f"实际: {len(leave_results)}")
    check("记录均为 leave 状态",
          all(r.status == "leave" for r in leave_results),
          f"实际: {[r.status for r in leave_results]}")

    day_status = checkin_svc.get_today_status("2026-06-04")
    morning_ps = next(p for p in day_status.periods if p.period == "morning")
    afternoon_ps = next(p for p in day_status.periods if p.period == "afternoon")
    check("morning 状态 leave", morning_ps.status == "leave", f"实际: {morning_ps.status}")
    check("afternoon 状态 leave", afternoon_ps.status == "leave", f"实际: {afternoon_ps.status}")

    # ============================================================
    # Story-5: 周五晚间弹性打卡 (2026-06-05)
    # ============================================================
    print("\n=== Story-5: 周五白天旷工+晚间弹性打卡 2026-06-05 ===")

    clock.set_date_and_time("2026-06-05", "20:00")
    absent_results = checkin_svc.mark_absent("2026-06-05")
    absent_periods = [r.period for r in absent_results]
    check("旷工包含 morning", "morning" in absent_periods, f"实际: {absent_periods}")
    check("旷工包含 afternoon", "afternoon" in absent_periods, f"实际: {absent_periods}")

    # 晚间签到
    r = checkin_svc.check_in("2026-06-05", "evening")
    check("晚间签到 normal", r.status == "normal", f"实际: {r.status}")

    # 晚间签退
    clock.set_date_and_time("2026-06-05", "23:00")
    r = checkin_svc.check_out("2026-06-05", "evening")
    check("晚间签退 normal", r.status == "normal", f"实际: {r.status}")

    # ============================================================
    # Story-6: 周日深夜 — 对赌结算 (2026-06-07)
    # ============================================================
    print("\n=== Story-6: 周日对赌结算 2026-06-07 ===")

    clock.set_date_and_time("2026-06-07", "23:30")
    summary = bet_svc.get_week_summary("2026-06-01")
    required_keys = ["completed", "extra_count", "total_reward", "completion_rate", "total_tasks"]
    for key in required_keys:
        check(f"summary 包含 key: {key}", key in summary, f"实际 keys: {list(summary.keys())}")
    check("completed >= 0", summary.get("completed", -1) >= 0,
          f"实际: {summary.get('completed')}")
    check("total_reward 为数字", isinstance(summary.get("total_reward"), (int, float)),
          f"实际类型: {type(summary.get('total_reward'))}")

    week_view = history_svc.get_week_view("2026-06-01")
    check("WeekViewData 有 7 天", len(week_view.days) == 7, f"实际: {len(week_view.days)}")

    # ============================================================
    # Story-7: 状态一致性与自愈校验
    # ============================================================
    print("\n=== Story-7: 状态一致性校验 ===")

    # 周一状态复验
    day_status = checkin_svc.get_today_status("2026-06-01")
    monday_morning = next(p for p in day_status.periods if p.period == "morning")
    monday_afternoon = next(p for p in day_status.periods if p.period == "afternoon")
    check("周一 morning 仍为 normal", monday_morning.status == "normal",
          f"实际: {monday_morning.status}")
    check("周一 afternoon 仍为 normal", monday_afternoon.status == "normal",
          f"实际: {monday_afternoon.status}")

    # 所有 7 天均有 3 个 periods
    all_ok = True
    for i, date_str in enumerate([
        "2026-06-01", "2026-06-02", "2026-06-03",
        "2026-06-04", "2026-06-05", "2026-06-06", "2026-06-07",
    ]):
        ds = checkin_svc.get_today_status(date_str)
        periods = [p.period for p in ds.periods]
        has_all = set(periods) == {"morning", "afternoon", "evening"}
        if not has_all:
            all_ok = False
            print(f"  [FAIL] {date_str} periods 不完整: {periods}")
    check("所有 7 天均返回 3 个 periods", all_ok)

    # ============================================================
    # 清理
    # ============================================================
    close_db()
    os.unlink(db_path)

    print(f"\n=== 全生命周期测试完毕 ===")
    print(f"通过: {passed}, 失败: {failed}")
    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
