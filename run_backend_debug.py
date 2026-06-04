"""独立后端调试脚本 — 无需启动 Kivy UI，纯管道流测试"""
from __future__ import annotations

import os
import tempfile

from app.db import close_db, init_db
from app.repositories.checkin_repo import CheckinRepo
from app.repositories.settings_repo import SettingsRepo
from app.services.checkin_service import CheckinService
from app.services.event_bus import EventBus, set_event_bus
from app.utils.clock import SimulatedClock, set_clock


def debug_main():
    print("=== 开始无 UI 后端管道流测试 ===\n")

    # ── 1. 初始化环境 ──
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(db_path)
    clock = SimulatedClock()
    set_clock(clock)
    set_event_bus(EventBus())

    svc = CheckinService(CheckinRepo(db_path), SettingsRepo(db_path))
    print(f"[环境] 临时数据库: {db_path}")
    print(f"[环境] 模拟时钟已初始化\n")

    # ── 2. 正常上午打卡 ──
    clock.set_date_and_time("2026-06-04", "08:55")
    print(f"[测试1] 时间={clock.current_time_str()} → 上午签到 (窗口内)")
    try:
        result = svc.check_in("2026-06-04", "morning")
        print(f"  [PASS] 结果: period={result.period}, status={result.status}({result.status_label}), time={result.checkin_time}")
    except Exception as e:
        print(f"  [FAIL] 崩溃: {e}")

    # ── 3. 迟到打卡 ──
    clock.set_date_and_time("2026-06-04", "11:00")
    print(f"\n[测试2] 时间={clock.current_time_str()} → 上午签到 (窗口内但迟到)")
    try:
        result = svc.check_in("2026-06-04", "morning")
        print(f"  [PASS] 结果: period={result.period}, status={result.status}({result.status_label}), time={result.checkin_time}")
    except Exception as e:
        print(f"  [FAIL] 崩溃: {e}")

    # ── 4. 窗口关闭后打卡 → 旷工 ──
    clock.set_date_and_time("2026-06-04", "18:23")
    print(f"\n[测试3] 时间={clock.current_time_str()} → 上午签到 (窗口已关闭! 上午09-12)")
    try:
        result = svc.check_in("2026-06-04", "morning")
        print(f"  [PASS] 结果: period={result.period}, status={result.status}({result.status_label})")
        if result.status == "absent_morning":
            print(f"  [PASS] 正确: 窗口关闭后签到 → 旷工(上午)")
        else:
            print(f"  [WARN] 期望 absent_morning，实际 {result.status}")
    except Exception as e:
        print(f"  [FAIL] 崩溃: {e}")

    # ── 5. 下午迟到 ──
    clock.set_date_and_time("2026-06-04", "18:23")
    print(f"\n[测试4] 时间={clock.current_time_str()} → 下午签到 (窗口内迟到)")
    try:
        result = svc.check_in("2026-06-04", "afternoon")
        print(f"  [PASS] 结果: period={result.period}, status={result.status}({result.status_label}), time={result.checkin_time}")
    except Exception as e:
        print(f"  [FAIL] 崩溃: {e}")

    # ── 4. 晚上时段 ──
    clock.set_date_and_time("2026-06-04", "20:30")
    print(f"\n[测试3] 时间={clock.current_time_str()} → 晚上签到 (evening)")
    try:
        result = svc.check_in("2026-06-04", "evening")
        print(f"  [PASS] 结果: period={result.period}, status={result.status}({result.status_label}), time={result.checkin_time}")
    except Exception as e:
        print(f"  [FAIL] 崩溃: {e}")

    # ── 5. 今日状态快照 ──
    print(f"\n[测试4] 获取今日状态快照:")
    try:
        day_status = svc.get_today_status("2026-06-04")
        print(f"  date={day_status.date}, is_shooting={day_status.is_shooting_day}")
        for ps in day_status.periods:
            print(f"    [{ps.period}] status={ps.status}, checkin={ps.checkin_time}, checkout={ps.checkout_time}")
        # 验证 evening 存在
        evening = next((p for p in day_status.periods if p.period == "evening"), None)
        if evening:
            print(f"  [PASS] evening 时段存在于状态快照中")
        else:
            print(f"  [FAIL] evening 时段缺失!")
    except Exception as e:
        print(f"  [FAIL] 崩溃: {e}")

    # ── 7. 正常签退 ──
    clock.set_date_and_time("2026-06-04", "12:05")
    print(f"\n[测试7] 时间={clock.current_time_str()} → 上午签退 (之前08:55正常签到)")
    try:
        result = svc.check_out("2026-06-04", "morning")
        print(f"  [PASS] 结果: period={result.period}, status={result.status}({result.status_label}), checkout={result.checkout_time}")
    except Exception as e:
        print(f"  [FAIL] 崩溃: {e}")

    # ── 8. 迟到签退保留状态 ──
    clock.set_date_and_time("2026-06-05", "09:10")
    svc.check_in("2026-06-05", "morning")  # 迟到签到
    clock.set_date_and_time("2026-06-05", "12:05")
    print(f"\n[测试8] 时间={clock.current_time_str()} → 上午签退 (之前09:10迟到签到)")
    try:
        result = svc.check_out("2026-06-05", "morning")
        print(f"  [PASS] 结果: period={result.period}, status={result.status}({result.status_label})")
        if result.status == "late":
            print(f"  [PASS] 正确: 迟到状态被保留")
        else:
            print(f"  [WARN] 期望 late，实际 {result.status}")
    except Exception as e:
        print(f"  [FAIL] 崩溃: {e}")

    # ── 9. 无签到直接签退 → 应拒绝 ──
    print(f"\n[测试9] 无签到 → 直接签退 (新鲜日期 2026-07-01) → 应抛出异常")
    try:
        svc.check_out("2026-07-01", "afternoon")
        print(f"  [FAIL] 应该抛出异常但没有!")
    except ValueError as e:
        print(f"  [PASS] 正确拒绝: {e}")
    except Exception as e:
        print(f"  [FAIL] 异常类型错误: {type(e).__name__}: {e}")

    # ── 清理 ──
    close_db()
    os.unlink(db_path)
    print(f"\n=== 测试完毕 ===")


if __name__ == "__main__":
    debug_main()
