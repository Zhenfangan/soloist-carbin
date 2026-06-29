"""L2 扩展自动化测试 —— Streak/auto_checkout/Promise/激励语/边界补充/压力。

全部使用 SimulatedClock + 内存数据库。
"""

from __future__ import annotations

import os
import sys
import tempfile

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import close_db, init_db
from app.repositories.checkin_repo import CheckinRepo
from app.repositories.settings_repo import SettingsRepo
from app.repositories.ledger_repo import LedgerRepo
from app.repositories.streak_repo import StreakRepo
from app.repositories.bet_repo import BetRepo
from app.services.checkin_service import CheckinService
from app.services.motivation_service import MotivationService
from app.services.boyfriend_promise_service import BoyfriendPromiseService
from app.services.report_service import ReportService
from app.services.penalty_service import PenaltyService
from app.interfaces.notifier import NoOpNotifier
from app.utils.clock import SimulatedClock, set_clock, get_clock

passed = 0
failed = 0

def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name} — {detail}")

def setup_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    return path

def cleanup_db(path: str) -> None:
    close_db()
    if os.path.exists(path):
        os.unlink(path)


# ═══════════════════════════════════════════════════════════════
# STREAK ST2-ST6
# ═══════════════════════════════════════════════════════════════

def test_streak() -> None:
    print("\n── STREAK ──")

    # ST2: late → 归零
    db = setup_db()
    checkin_svc = CheckinService(CheckinRepo(db), SettingsRepo(db))
    ledger_repo = LedgerRepo(db)
    streak_repo = StreakRepo(db)
    settings_repo = SettingsRepo(db)
    mot_svc = MotivationService(checkin_svc._checkin_repo, streak_repo, settings_repo, NoOpNotifier())

    clock = get_clock()
    assert isinstance(clock, SimulatedClock)

    # 先建几天正常打卡建立 streak
    clock.set_date_and_time("2026-06-01", "08:30")
    checkin_svc.check_in("2026-06-01", "morning")
    clock.set_date_and_time("2026-06-01", "12:05")
    checkin_svc.check_out("2026-06-01", "morning")
    clock.set_date_and_time("2026-06-01", "14:00")
    checkin_svc.check_in("2026-06-01", "afternoon")
    clock.set_date_and_time("2026-06-01", "18:05")
    checkin_svc.check_out("2026-06-01", "afternoon")
    s1 = mot_svc.update_streak("2026-06-01")
    check("ST1 全normal→streak>0", s1 > 0, f"got {s1}")

    # ST2: 第二天 late → 归零
    clock.set_date_and_time("2026-06-02", "09:10")
    checkin_svc.check_in("2026-06-02", "morning")
    clock.set_date_and_time("2026-06-02", "12:05")
    checkin_svc.check_out("2026-06-02", "morning")
    clock.set_date_and_time("2026-06-02", "14:00")
    checkin_svc.check_in("2026-06-02", "afternoon")
    clock.set_date_and_time("2026-06-02", "18:05")
    checkin_svc.check_out("2026-06-02", "afternoon")
    s2 = mot_svc.update_streak("2026-06-02")
    check("ST2 late→streak归零", s2 == 0, f"got {s2}")
    cleanup_db(db)

    # ST3: absent → 归零
    db = setup_db()
    checkin_svc = CheckinService(CheckinRepo(db), SettingsRepo(db))
    mot_svc = MotivationService(checkin_svc._checkin_repo, StreakRepo(db), SettingsRepo(db), NoOpNotifier())
    # 先建 streak
    clock.set_date_and_time("2026-06-03", "08:30")
    checkin_svc.check_in("2026-06-03", "morning")
    clock.set_date_and_time("2026-06-03", "12:05")
    checkin_svc.check_out("2026-06-03", "morning")
    clock.set_date_and_time("2026-06-03", "14:00")
    checkin_svc.check_in("2026-06-03", "afternoon")
    clock.set_date_and_time("2026-06-03", "18:05")
    checkin_svc.check_out("2026-06-03", "afternoon")
    mot_svc.update_streak("2026-06-03")
    # 第二天 absent
    clock.set_date_and_time("2026-06-04", "12:01")
    checkin_svc.mark_absent("2026-06-04")
    clock.set_date_and_time("2026-06-04", "18:01")
    checkin_svc.mark_absent("2026-06-04")
    s3 = mot_svc.update_streak("2026-06-04")
    check("ST3 absent→streak归零", s3 == 0, f"got {s3}")
    cleanup_db(db)

    # ST4: leave → 归零
    db = setup_db()
    checkin_svc = CheckinService(CheckinRepo(db), SettingsRepo(db))
    mot_svc = MotivationService(checkin_svc._checkin_repo, StreakRepo(db), SettingsRepo(db), NoOpNotifier())
    # 先建 streak
    clock.set_date_and_time("2026-06-08", "08:30")
    checkin_svc.check_in("2026-06-08", "morning")
    clock.set_date_and_time("2026-06-08", "12:05")
    checkin_svc.check_out("2026-06-08", "morning")
    clock.set_date_and_time("2026-06-08", "14:00")
    checkin_svc.check_in("2026-06-08", "afternoon")
    clock.set_date_and_time("2026-06-08", "18:05")
    checkin_svc.check_out("2026-06-08", "afternoon")
    mot_svc.update_streak("2026-06-08")
    # 第二天 leave
    clock.set_date_and_time("2026-06-09", "08:00")
    checkin_svc.apply_leave("2026-06-09", "all_day")
    s4 = mot_svc.update_streak("2026-06-09")
    check("ST4 leave→streak归零", s4 == 0, f"got {s4}")
    cleanup_db(db)

    # ST5: 周末不更新
    db = setup_db()
    checkin_svc = CheckinService(CheckinRepo(db), SettingsRepo(db))
    mot_svc = MotivationService(checkin_svc._checkin_repo, StreakRepo(db), SettingsRepo(db), NoOpNotifier())
    # 先建 streak on Friday 2026-06-05
    clock.set_date_and_time("2026-06-05", "08:30")
    checkin_svc.check_in("2026-06-05", "morning")
    clock.set_date_and_time("2026-06-05", "12:05")
    checkin_svc.check_out("2026-06-05", "morning")
    clock.set_date_and_time("2026-06-05", "14:00")
    checkin_svc.check_in("2026-06-05", "afternoon")
    clock.set_date_and_time("2026-06-05", "18:05")
    checkin_svc.check_out("2026-06-05", "afternoon")
    mot_svc.update_streak("2026-06-05")
    # Saturday 2026-06-06 — 也正常打卡但不应更新 streak
    clock.set_date_and_time("2026-06-06", "08:30")
    checkin_svc.check_in("2026-06-06", "morning")
    clock.set_date_and_time("2026-06-06", "12:05")
    checkin_svc.check_out("2026-06-06", "morning")
    clock.set_date_and_time("2026-06-06", "14:00")
    checkin_svc.check_in("2026-06-06", "afternoon")
    clock.set_date_and_time("2026-06-06", "18:05")
    checkin_svc.check_out("2026-06-06", "afternoon")
    s5 = mot_svc.update_streak("2026-06-06")
    check("ST5 周末→streak不变(非0)", s5 > 0, f"got {s5} (应保持周五的streak)")
    cleanup_db(db)


# ═══════════════════════════════════════════════════════════════
# AUTO_CHECKOUT
# ═══════════════════════════════════════════════════════════════

def test_auto_checkout() -> None:
    print("\n── AUTO CHECKOUT ──")

    db = setup_db()
    svc = CheckinService(CheckinRepo(db), SettingsRepo(db))
    clock = get_clock()
    assert isinstance(clock, SimulatedClock)

    # 签到但忘记签退
    clock.set_date_and_time("2026-06-01", "09:00")
    svc.check_in("2026-06-01", "morning")

    # 调用 auto_checkout
    results = svc.auto_checkout("2026-06-01")
    check("AC1 auto_checkout补签退", len(results) == 1, f"got {len(results)}")
    if results:
        check("AC1 checkout_type=auto", results[0].checkout_type == "auto",
              f"got {results[0].checkout_type}")
        check("AC1 checkout_time=12:00", results[0].checkout_time == "12:00",
              f"got {results[0].checkout_time}")

    # 幂等:已签退的不再补
    results2 = svc.auto_checkout("2026-06-01")
    check("AC2 已签退→不再补", len(results2) == 0, f"got {len(results2)}")

    cleanup_db(db)


# ═══════════════════════════════════════════════════════════════
# EVENING E2 + 旷工触发
# ═══════════════════════════════════════════════════════════════

def test_edge_cases() -> None:
    print("\n── EDGE CASES ──")

    # E2: 上午/下午都没签→晚上直接签
    db = setup_db()
    svc = CheckinService(CheckinRepo(db), SettingsRepo(db))
    clock = get_clock()
    assert isinstance(clock, SimulatedClock)

    # 上午+下午都旷工
    clock.set_date_and_time("2026-06-01", "18:01")
    svc.mark_absent("2026-06-01")  # 判上午+下午旷工

    # 晚上签到
    clock.set_date_and_time("2026-06-01", "19:30")
    r = svc.check_in("2026-06-01", "evening")
    check("E2 全旷→evening正常签", r.status == "normal", f"got {r.status}")
    r2 = svc.check_out("2026-06-01", "evening")
    check("E2 evening签退→normal", r2.status == "normal")
    cleanup_db(db)

    # MK1: 12:05首次打开→absent_morning自动判定
    db = setup_db()
    svc = CheckinService(CheckinRepo(db), SettingsRepo(db))
    clock.set_date_and_time("2026-06-01", "12:05")
    results = svc.mark_absent("2026-06-01")
    check("MK1 12:05首次打开→判旷工", len(results) == 1 and results[0].status == "absent_morning",
          f"got {len(results)}")
    cleanup_db(db)

    # MK2: mark_absent 不在 12:00 前判(验证边界)
    db = setup_db()
    svc = CheckinService(CheckinRepo(db), SettingsRepo(db))
    clock.set_date_and_time("2026-06-01", "11:59")
    results = svc.mark_absent("2026-06-01")
    check("MK2 11:59→不判旷工", len(results) == 0, f"got {len(results)}")
    cleanup_db(db)


# ═══════════════════════════════════════════════════════════════
# LEAVE OPTION BOUNDARIES
# ═══════════════════════════════════════════════════════════════

def test_leave_boundaries() -> None:
    print("\n── LEAVE BOUNDARIES ──")

    db = setup_db()
    svc = CheckinService(CheckinRepo(db), SettingsRepo(db))
    clock = get_clock()
    assert isinstance(clock, SimulatedClock)

    # 08:59:59 → 仍可请上午假
    opts = svc.get_leave_options("2026-06-01", "08:59")
    check("08:59→三选项", set(opts) == {"morning", "afternoon", "all_day"},
          f"got {opts}")

    # 09:00:00 → 上午请假窗口关闭
    opts = svc.get_leave_options("2026-06-01", "09:00")
    check("09:00→只剩afternoon", opts == ["afternoon"],
          f"got {opts}")

    # 13:59 → 仍可请下午假
    opts = svc.get_leave_options("2026-06-01", "13:59")
    check("13:59→只剩afternoon", opts == ["afternoon"],
          f"got {opts}")

    # 14:00 → 全关闭
    opts = svc.get_leave_options("2026-06-01", "14:00")
    check("14:00→无选项", opts == [], f"got {opts}")

    cleanup_db(db)


# ═══════════════════════════════════════════════════════════════
# REPORT SERVICE / ENCOURAGEMENT
# ═══════════════════════════════════════════════════════════════

def test_report_encouragement() -> None:
    print("\n── REPORT / ENCOURAGEMENT ──")

    db = setup_db()
    checkin_repo = CheckinRepo(db)
    ledger_repo = LedgerRepo(db)
    settings_repo = SettingsRepo(db)
    report_svc = ReportService(checkin_repo, ledger_repo, None, settings_repo)

    clock = get_clock()
    assert isinstance(clock, SimulatedClock)

    # 无自定义→回退内置 5 句
    enc = report_svc._pick_encouragement("2026-06-01")
    builtin = [
        "每个努力的日子都值得被记住，继续加油！",
        "自律是通往自由最快的路。",
        "今天辛苦啦，明天会更好！",
        "一点点进步，积累起来就是巨大的改变。",
        "坚持下去，你就是自己的光。",
    ]
    check("MT2 无自定义→回退内置", enc in builtin, f"got '{enc}'")

    # 有自定义→只用自定义
    settings_repo.set("encouragements_user", '["自定义激励A","自定义激励B"]')
    for _ in range(10):
        enc2 = report_svc._pick_encouragement("2026-06-02")
        if enc2 == "自定义激励A" or enc2 == "自定义激励B":
            pass
        else:
            check("MT1 自定义→只用自定义(不应出现内置)", False,
                  f"出现了 '{enc2}'")
            break
    else:
        check("MT1 自定义激励10次未退化", True)
    cleanup_db(db)


# ═══════════════════════════════════════════════════════════════
# PROMISE
# ═══════════════════════════════════════════════════════════════

def test_promise() -> None:
    print("\n── PROMISE ──")

    db = setup_db()
    ledger_repo = LedgerRepo(db)
    settings_repo = SettingsRepo(db)
    checkin_repo = CheckinRepo(db)
    promise_svc = BoyfriendPromiseService(ledger_repo, settings_repo, checkin_repo)

    # 设定承诺
    promise_svc.set_promise("2026-06-01", "一杯奶茶", 1)
    p = promise_svc.get_today_promise("2026-06-01")
    check("Promise 设定→可读取", p is not None)
    if p:
        check("Promise 描述正确", p.reward_desc == "一杯奶茶")
        check("Promise 数量正确", p.reward_qty == 1)
        check("Promise 初始未兑现", p.fulfilled == 0)

    # 工作时长不足→未兑现 — 用 checkin_service 在同一 db 创建记录
    clock = get_clock()
    assert isinstance(clock, SimulatedClock)
    csvc = CheckinService(checkin_repo, settings_repo)
    clock.set_date_and_time("2026-06-01", "09:00")
    csvc.check_in("2026-06-01", "morning")
    clock.set_date_and_time("2026-06-01", "12:00")
    csvc.check_out("2026-06-01", "morning")
    hours = promise_svc.calculate_total_hours("2026-06-01")
    check("Promise 工时计算~3h", abs(hours - 3.0) < 0.1, f"got {hours}")

    fulfilled = promise_svc.check_fulfill("2026-06-01", hours)
    check("Promise 3h<8h→未兑现", not fulfilled, "应未兑现")

    # 足够时长→兑现
    fulfilled2 = promise_svc.check_fulfill("2026-06-01", 8.5)
    check("Promise 8.5h>=8h→兑现", fulfilled2, "应兑现")
    p2 = promise_svc.get_today_promise("2026-06-01")
    check("Promise 标记 fulfilled=1", p2 is not None and p2.fulfilled == 1)

    cleanup_db(db)


# ═══════════════════════════════════════════════════════════════
# PRESSURE / EDGE TESTS
# ═══════════════════════════════════════════════════════════════

def test_pressure() -> None:
    print("\n── PRESSURE ──")

    # T1: 幂等签到(已在 L2 主脚本验证,此处补 afternoon 场景)
    db = setup_db()
    svc = CheckinService(CheckinRepo(db), SettingsRepo(db))
    clock = get_clock()
    assert isinstance(clock, SimulatedClock)
    clock.set_date_and_time("2026-06-01", "14:00")
    r1 = svc.check_in("2026-06-01", "afternoon")
    r2 = svc.check_in("2026-06-01", "afternoon")
    check("T1 afternoon幂等:时间不变", r2.checkin_time == r1.checkin_time,
          f"{r2.checkin_time} vs {r1.checkin_time}")

    # T2: 空数据库启动不崩溃
    db2 = setup_db()
    svc2 = CheckinService(CheckinRepo(db2), SettingsRepo(db2))
    status = svc2.get_today_status("2026-06-01")
    check("T2 空库启动→get_today_status不崩溃", status is not None)
    # 空库 get_today_status 返回默认 3 个 pending 时段
    check("T2 空库→有默认3时段", len(status.periods) == 3,
          f"got {len(status.periods)} periods")
    cleanup_db(db)
    cleanup_db(db2)


# ═══════════════════════════════════════════════════════════════
# SHOOTING DAY DIAGNOSIS
# ═══════════════════════════════════════════════════════════════

def test_shooting_diagnosis() -> None:
    """诊断拍摄日 is_shooting 字段是否被设置。"""
    print("\n── SHOOTING DAY DIAGNOSIS ──")

    db = setup_db()
    svc = CheckinService(CheckinRepo(db), SettingsRepo(db))
    clock = get_clock()
    assert isinstance(clock, SimulatedClock)

    # 方法1: 直接查 shooting_days 表
    from app.repositories.shooting_repo import ShootingRepo
    shoot_repo = ShootingRepo(db)
    shoot_repo.set_shooting_day(ShootingDay("2026-06-01", "测试拍摄"))

    # 方法2: 通过 ShootingService
    from app.services.shooting_service import ShootingService
    shoot_svc = ShootingService(shoot_repo)

    is_shooting_via_service = shoot_svc.is_shooting_day("2026-06-01")
    check("SD-DIAG1 ShootingService.is_shooting_day→True",
          is_shooting_via_service, "shooting_days 表有记录")

    # 方法3: CheckinService._is_shooting_day
    is_shooting_via_checkin = svc._is_shooting_day("2026-06-01")
    check("SD-DIAG2 CheckinService._is_shooting_day→False(已知BUG)",
          not is_shooting_via_checkin,
          "checkins.is_shooting 字段永不为1——这是已知问题")

    # SD-DIAG1+2 已确认: _is_shooting_day() 永远返回 False
    # shooting_days 表有记录但 CheckinService 不检查该表
    print("  ⚠️ 已知:拍摄日功能数据层正常,但签到流程未接入(is_shooting字段缺失赋值)")

    cleanup_db(db)


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

# 需要导入 ShootingDay 模型
from app.models.shooting import ShootingDay


def main() -> None:
    clock = SimulatedClock()
    set_clock(clock)

    test_streak()
    test_auto_checkout()
    test_edge_cases()
    test_leave_boundaries()
    test_report_encouragement()
    test_promise()
    test_pressure()
    test_shooting_diagnosis()

    print(f"\n{'='*50}")
    print(f"  结果: {passed} passed, {failed} failed (共 {passed+failed})")
    if failed == 0:
        print("  🎉 全部通过!")
    else:
        print(f"  ⚠️ {failed} 项失败,需检查")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
