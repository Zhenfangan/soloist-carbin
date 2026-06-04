"""后端边界与压力测试 — 异常输入、重复动作、未初始化状态"""
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
    # S-1: 异常时间轰炸
    # ============================================================

    # ── S-1a: 凌晨 3 点打卡 ──
    print("\n=== S-1a: 凌晨 3 点打卡 ===")
    clock.set_date_and_time("2026-06-01", "03:00")
    try:
        r = checkin_svc.check_in("2026-06-01", "morning")
        check("凌晨 3 点 morning 签到不抛异常", True)
        check("凌晨 3 点 morning 状态为 normal", r.status == "normal", f"实际: {r.status}")
    except Exception as e:
        check("凌晨 3 点 morning 签到不抛异常", False, f"异常: {e}")

    try:
        r = checkin_svc.check_in("2026-06-01", "afternoon")
        check("凌晨 3 点 afternoon 签到不抛异常", True)
    except Exception as e:
        check("凌晨 3 点 afternoon 签到不抛异常", False, f"异常: {e}")

    # ── S-1b: 非法 period 名称 ──
    print("\n=== S-1b: 非法 period 名称 ===")
    clock.set_date_and_time("2026-06-02", "09:00")
    try:
        r = checkin_svc.check_in("2026-06-02", "midnight")
        check("非法 period 'midnight' 不抛 KeyError", True)
        check("非法 period 返回 normal", r.status == "normal", f"实际: {r.status}")
    except KeyError as e:
        check("非法 period 'midnight' 不抛 KeyError", False, f"KeyError: {e}")
    except Exception as e:
        check("非法 period 'midnight' 不抛 KeyError", False, f"其他异常: {type(e).__name__}: {e}")

    # ── S-1c: 非法日期格式 ──
    print("\n=== S-1c: 非法日期格式 ===")
    clock.set_date_and_time("2026-06-01", "09:00")
    try:
        r = checkin_svc.check_in("not-a-date", "morning")
        check("非法日期 'not-a-date' 不抛异常", True)
    except Exception as e:
        check("非法日期 'not-a-date' 不抛异常", False, f"异常: {type(e).__name__}: {e}")

    # ── S-1d: 签退时间早于上班时间 ──
    print("\n=== S-1d: 签退时间早于上班时间 ===")
    clock.set_date_and_time("2026-06-03", "06:00")
    checkin_svc.check_in("2026-06-03", "morning")
    clock.set_date_and_time("2026-06-03", "07:00")
    try:
        r = checkin_svc.check_out("2026-06-03", "morning")
        check("签退早于上班时间不抛异常", True)
        check("签退早于上班时间为 early_leave", r.status == "early_leave", f"实际: {r.status}")
    except Exception as e:
        check("签退早于上班时间不抛异常", False, f"异常: {type(e).__name__}: {e}")

    # ============================================================
    # S-2: 并发/重复动作幂等性
    # ============================================================

    # ── S-2a: 同日期同时段连续 3 次打卡 ──
    print("\n=== S-2a: 连续 3 次打卡 ===")
    clock.set_date_and_time("2026-06-04", "08:55")
    r1 = checkin_svc.check_in("2026-06-04", "morning")
    r2 = checkin_svc.check_in("2026-06-04", "morning")
    r3 = checkin_svc.check_in("2026-06-04", "morning")
    check("3 次打卡均返回 CheckinResult", all(r is not None for r in [r1, r2, r3]))
    check("3 次打卡 checkin_time 相同",
          r1.checkin_time == r2.checkin_time == r3.checkin_time,
          f"实际: {r1.checkin_time}, {r2.checkin_time}, {r3.checkin_time}")

    # DB 幂等性
    checkin_repo = CheckinRepo(db_path)
    records = checkin_repo.get_all_by_date("2026-06-04")
    morning_records = [r for r in records if r.period == "morning"]
    check("morning 记录仅 1 条", len(morning_records) == 1, f"实际: {len(morning_records)}")
    if morning_records:
        check("morning 记录 checkin_time 不为 NULL",
              morning_records[0].checkin_time is not None,
              f"实际: {morning_records[0].checkin_time}")

    # ── S-2b: 同日期同时段连续 3 次签退 ──
    print("\n=== S-2b: 连续 3 次签退 ===")
    clock.set_date_and_time("2026-06-04", "12:05")
    try:
        q1 = checkin_svc.check_out("2026-06-04", "morning")
        q2 = checkin_svc.check_out("2026-06-04", "morning")
        q3 = checkin_svc.check_out("2026-06-04", "morning")
        check("3 次签退均不抛异常", True)
    except Exception as e:
        check("3 次签退均不抛异常", False, f"异常: {type(e).__name__}: {e}")

    records = checkin_repo.get_all_by_date("2026-06-04")
    morning_records = [r for r in records if r.period == "morning"]
    check("签退后 morning 记录仍仅 1 条", len(morning_records) == 1, f"实际: {len(morning_records)}")
    if morning_records:
        check("签退后 checkout_time 不为 NULL",
              morning_records[0].checkout_time is not None)

    # ── S-2c: 签退未签到时段 ──
    print("\n=== S-2c: 签退未签到时段 ===")
    try:
        checkin_svc.check_out("2026-07-15", "morning")
        check("未签到直接签退应抛 ValueError", False, "没有抛出异常")
    except ValueError as e:
        check("未签到直接签退抛 ValueError", "尚未签到" in str(e), f"消息: {e}")
    except Exception as e:
        check("未签到直接签退抛 ValueError", False, f"异常类型错误: {type(e).__name__}: {e}")

    # DB 中不应存在
    records = checkin_repo.get_all_by_date("2026-07-15")
    check("DB 中不存在 2026-07-15 记录", len(records) == 0, f"实际: {len(records)}")

    # ============================================================
    # S-3: 未初始化结算
    # ============================================================
    print("\n=== S-3: 未初始化结算 ===")

    ledger_repo = LedgerRepo(db_path)
    bet_repo = BetRepo(db_path)
    bet_svc = BetService(bet_repo, ledger_repo, settings_repo)

    # ── S-3a: 不配置周赏罚金额直接结算 ──
    print("\n=== S-3a: 空 bet_configs 结算 ===")
    try:
        summary = bet_svc.get_week_summary("2026-06-01")
        check("summary 为 dict", isinstance(summary, dict), f"实际类型: {type(summary)}")
        check("total_reward 为 0", summary.get("total_reward", -1) == 0,
              f"实际: {summary.get('total_reward')}")
        check("completion_rate 为 0", summary.get("completion_rate", -1) == 0,
              f"实际: {summary.get('completion_rate')}")
    except Exception as e:
        check("空配置结算不抛异常", False, f"异常: {type(e).__name__}: {e}")

    # ── S-3b: 未完成任何打卡时强行结算 ──
    print("\n=== S-3b: 无打卡记录结算 ===")
    try:
        summary = bet_svc.get_week_summary("2026-07-01")
        check("无打卡结算不抛异常", True)
        check("无打卡结算返回 dict", isinstance(summary, dict))
        check("无打卡 total_reward 为 0", summary.get("total_reward", -1) == 0,
              f"实际: {summary.get('total_reward')}")
    except Exception as e:
        check("无打卡结算不抛异常", False, f"异常: {type(e).__name__}: {e}")

    # ── S-3c: 空 DB 状态查询 ──
    print("\n=== S-3c: 空 DB 状态查询 ===")
    # 全新临时 DB
    fd2, db_path2 = tempfile.mkstemp(suffix=".db")
    os.close(fd2)
    init_db(db_path2)
    empty_svc = CheckinService(CheckinRepo(db_path2), SettingsRepo(db_path2))
    try:
        day_status = empty_svc.get_today_status("2099-01-01")
        check("空 DB 查询不抛异常", True)
        check("periods 长度为 3", len(day_status.periods) == 3,
              f"实际: {len(day_status.periods)}")
        all_pending = all(p.status == "pending" for p in day_status.periods)
        check("全部 status 为 pending", all_pending,
              f"实际: {[p.status for p in day_status.periods]}")
    except Exception as e:
        check("空 DB 查询不抛异常", False, f"异常: {type(e).__name__}: {e}")
    close_db()
    os.unlink(db_path2)

    # ============================================================
    # S-4: 快速状态翻转（状态机抖动）
    # ============================================================
    print("\n=== S-4: 快速状态翻转 ===")
    clock.set_date_and_time("2026-06-10", "08:55")
    try:
        s1 = checkin_svc.check_in("2026-06-10", "morning")
        check("第 1 次签到 normal", s1.status == "normal", f"实际: {s1.status}")
    except Exception as e:
        check("第 1 次签到不抛异常", False, f"异常: {e}")

    try:
        s2 = checkin_svc.check_out("2026-06-10", "morning")
        check("第 1 次签退 early_leave", s2.status == "early_leave",
              f"实际: {s2.status} (08:55 < 12:00)")
    except Exception as e:
        check("第 1 次签退不抛异常", False, f"异常: {e}")

    try:
        s3 = checkin_svc.check_in("2026-06-10", "morning")
        check("第 2 次签到不抛异常", True)
        check("第 2 次签到返回 CheckinResult", s3 is not None)
    except Exception as e:
        check("第 2 次签到不抛异常", False, f"异常: {type(e).__name__}: {e}")

    # 检查 checkout_time 被覆盖
    records = checkin_repo.get_all_by_date("2026-06-10")
    morning_records = [r for r in records if r.period == "morning"]
    check("快速翻转后 morning 记录仍仅 1 条", len(morning_records) == 1,
          f"实际: {len(morning_records)}")
    if morning_records:
        rec = morning_records[0]
        check("快速翻转后 checkout_time 被清空",
              rec.checkout_time is None,
              f"实际 checkout_time: {rec.checkout_time}")

    # ============================================================
    # S-5: None / 空字符串注入
    # ============================================================
    print("\n=== S-5: None / 空字符串注入 ===")
    try:
        checkin_svc.check_in("", "morning")
        check("空日期 '' 不抛异常", True)
    except Exception as e:
        check("空日期 '' 不抛异常", False, f"异常: {type(e).__name__}: {e}")

    try:
        checkin_svc.check_in("2026-12-01", "")
        check("空 period '' 不抛异常", True)
    except Exception as e:
        check("空 period '' 不抛异常", False, f"异常: {type(e).__name__}: {e}")

    try:
        settings_svc.set("morning_start", "")
        check("设置空 morning_start 不抛异常", True)
    except Exception as e:
        check("设置空 morning_start 不抛异常", False, f"异常: {type(e).__name__}: {e}")

    try:
        clock.set_date_and_time("2026-12-02", "09:00")
        r = checkin_svc.check_in("2026-12-02", "morning")
        check("空 morning_start 后签到不抛异常", True)
        check("空 morning_start 后签到返回 normal", r.status == "normal",
              f"实际: {r.status}")
    except Exception as e:
        check("空 morning_start 后签到不抛异常", False, f"异常: {type(e).__name__}: {e}")

    # ============================================================
    # 清理
    # ============================================================
    close_db()
    os.unlink(db_path)

    print(f"\n=== 边界压力测试完毕 ===")
    print(f"通过: {passed}, 失败: {failed}")
    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
