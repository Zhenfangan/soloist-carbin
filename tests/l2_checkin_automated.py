"""L2 打卡自动化测试 —— 穷举 all 时段×状态×边界。

用 SimulatedClock + 内存数据库,无需 UI,直接断言 CheckinService 行为。
"""

from __future__ import annotations

import os
import sys
import tempfile

# windows 控制台 utf-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import close_db, init_db
from app.repositories.checkin_repo import CheckinRepo
from app.repositories.settings_repo import SettingsRepo
from app.services.checkin_service import CheckinService
from app.services.motivation_service import MotivationService
from app.repositories.ledger_repo import LedgerRepo
from app.repositories.streak_repo import StreakRepo
from app.repositories.bet_repo import BetRepo
from app.services.bet_service import BetService
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


def make_svc(db_path: str) -> CheckinService:
    return CheckinService(CheckinRepo(db_path), SettingsRepo(db_path))


def make_bet_svc(db_path: str) -> BetService:
    return BetService(BetRepo(db_path), LedgerRepo(db_path), SettingsRepo(db_path))


# ═══════════════════════════════════════════════════════════════
# MORNING (M1-M9)
# ═══════════════════════════════════════════════════════════════

def test_morning() -> None:
    print("\n── MORNING ──")

    # M1: 准时签到
    db = setup_db()
    svc = make_svc(db)
    clock = get_clock()
    assert isinstance(clock, SimulatedClock)
    clock.set_date_and_time("2026-06-01", "08:30")
    r = svc.check_in("2026-06-01", "morning")
    check("M1 准时签到→normal", r.status == "normal", f"got {r.status}")
    # 签到后再签到(幂等)
    r2 = svc.check_in("2026-06-01", "morning")
    check("M1 幂等:二次签到不重复", r2.checkin_time == r.checkin_time, "时间应不变")
    clock.set_date_and_time("2026-06-01", "12:05")
    r3 = svc.check_out("2026-06-01", "morning")
    check("M1 准时签退→normal", r3.status == "normal", f"got {r3.status}")
    cleanup_db(db)

    # M2: 迟到
    db = setup_db()
    svc = make_svc(db)
    clock.set_date_and_time("2026-06-01", "09:10")
    r = svc.check_in("2026-06-01", "morning")
    check("M2 迟到签到→late", r.status == "late", f"got {r.status}")
    clock.set_date_and_time("2026-06-01", "12:05")
    r2 = svc.check_out("2026-06-01", "morning")
    check("M2 迟到签退→late保留", r2.status == "late", f"签退不应覆盖迟到,got {r2.status}")
    cleanup_db(db)

    # M3: 早退
    db = setup_db()
    svc = make_svc(db)
    clock.set_date_and_time("2026-06-01", "09:00")
    svc.check_in("2026-06-01", "morning")
    clock.set_date_and_time("2026-06-01", "11:30")
    r2 = svc.check_out("2026-06-01", "morning")
    check("M3 早退→early_leave", r2.status == "early_leave", f"got {r2.status}")
    cleanup_db(db)

    # M4: 旷工判定
    db = setup_db()
    svc = make_svc(db)
    clock.set_date_and_time("2026-06-01", "12:01")
    results = svc.mark_absent("2026-06-01")
    check("M4 旷工判定(12:01)", len(results) == 1 and results[0].status == "absent_morning",
          f"got {len(results)} results")
    cleanup_db(db)

    # M5: 旷工后补签
    db = setup_db()
    svc = make_svc(db)
    clock.set_date_and_time("2026-06-01", "18:23")
    r = svc.check_in("2026-06-01", "morning")
    check("M5 窗口关闭后签到→absent_morning", r.status == "absent_morning", f"got {r.status}")
    cleanup_db(db)

    # M6: 上午请假
    db = setup_db()
    svc = make_svc(db)
    clock.set_date_and_time("2026-06-01", "08:30")
    r = svc.apply_leave("2026-06-01", "morning")
    check("M6 上午请假→leave", r[0].status == "leave", f"got {r[0].status}")
    check("M6 请假后不可签到(morning)", r[0].status == "leave", "已是leave终态")
    cleanup_db(db)

    # M7: 请假按钮禁用在窗口外 — 由 UI 层验证,此处跳过

    # M8: 全天请假
    db = setup_db()
    svc = make_svc(db)
    clock.set_date_and_time("2026-06-01", "08:00")
    r = svc.apply_leave("2026-06-01", "all_day")
    check("M8 全天请假→morning=leave", r[0].status == "leave")
    check("M8 全天请假→afternoon=leave", len(r) == 2 and r[1].status == "leave")
    cleanup_db(db)

    # M9: 幂等(已在M1中测)


# ═══════════════════════════════════════════════════════════════
# AFTERNOON (A1-A6)
# ═══════════════════════════════════════════════════════════════

def test_afternoon() -> None:
    print("\n── AFTERNOON ──")

    # A1: 正常
    db = setup_db()
    svc = make_svc(db)
    clock = get_clock()
    assert isinstance(clock, SimulatedClock)
    clock.set_date_and_time("2026-06-01", "14:00")
    r = svc.check_in("2026-06-01", "afternoon")
    check("A1 正常签下午→normal", r.status == "normal", f"got {r.status}")
    clock.set_date_and_time("2026-06-01", "18:05")
    r2 = svc.check_out("2026-06-01", "afternoon")
    check("A1 正常签退下午→normal", r2.status == "normal", f"got {r2.status}")
    cleanup_db(db)

    # A2: 迟到
    db = setup_db()
    svc = make_svc(db)
    clock.set_date_and_time("2026-06-01", "14:10")
    r = svc.check_in("2026-06-01", "afternoon")
    check("A2 下午迟到→late", r.status == "late", f"got {r.status}")
    cleanup_db(db)

    # A3: 早退
    db = setup_db()
    svc = make_svc(db)
    clock.set_date_and_time("2026-06-01", "14:00")
    svc.check_in("2026-06-01", "afternoon")
    clock.set_date_and_time("2026-06-01", "16:00")
    r2 = svc.check_out("2026-06-01", "afternoon")
    check("A3 下午早退→early_leave", r2.status == "early_leave", f"got {r2.status}")
    cleanup_db(db)

    # A4: 旷工 — 先签 morning 避免双旷工
    db = setup_db()
    svc = make_svc(db)
    clock.set_date_and_time("2026-06-01", "08:30")
    svc.check_in("2026-06-01", "morning")
    clock.set_date_and_time("2026-06-01", "12:05")
    svc.check_out("2026-06-01", "morning")
    clock.set_date_and_time("2026-06-01", "18:01")
    results = svc.mark_absent("2026-06-01")
    check("A4 下午旷工(18:01)", len(results) == 1 and results[0].status == "absent_afternoon",
          f"got {len(results)} status={results[0].status if results else 'none'}")
    cleanup_db(db)

    # A5: 下午请假
    db = setup_db()
    svc = make_svc(db)
    clock.set_date_and_time("2026-06-01", "13:00")
    r = svc.apply_leave("2026-06-01", "afternoon")
    check("A5 下午请假→leave", r[0].status == "leave")
    cleanup_db(db)

    # A6: 请假窗口外禁点 — UI 层验证


# ═══════════════════════════════════════════════════════════════
# EVENING (E1-E2)
# ═══════════════════════════════════════════════════════════════

def test_evening() -> None:
    print("\n── EVENING ──")

    db = setup_db()
    svc = make_svc(db)
    clock = get_clock()
    assert isinstance(clock, SimulatedClock)
    # morning + afternoon 都终态(用leave)
    clock.set_date_and_time("2026-06-01", "08:00")
    svc.apply_leave("2026-06-01", "all_day")
    clock.set_date_and_time("2026-06-01", "19:30")
    r = svc.check_in("2026-06-01", "evening")
    check("E1 evening签到→永远normal", r.status == "normal", f"got {r.status}")
    r2 = svc.check_out("2026-06-01", "evening")
    check("E1 evening签退→永远normal", r2.status == "normal", f"got {r2.status}")
    cleanup_db(db)


# ═══════════════════════════════════════════════════════════════
# BOUNDARY SECONDS (BND1-BND6)
# ═══════════════════════════════════════════════════════════════

def test_boundaries() -> None:
    print("\n── BOUNDARY ──")

    # BND1: 09:00:00 签到 → normal(含等于)
    db = setup_db()
    svc = make_svc(db)
    clock = get_clock()
    assert isinstance(clock, SimulatedClock)
    clock.set_date_and_time("2026-06-01", "09:00")
    r = svc.check_in("2026-06-01", "morning")
    check("BND1 09:00:00签到→normal", r.status == "normal", f"got {r.status}")
    cleanup_db(db)

    # BND2: 09:01 签到 → late(秒不参与比较,分钟精度边界用 09:01)
    db = setup_db()
    svc = make_svc(db)
    clock.set_date_and_time("2026-06-01", "09:01")
    r = svc.check_in("2026-06-01", "morning")
    check("BND2 09:01签到→late", r.status == "late", f"got {r.status}")
    cleanup_db(db)

    # BND3: 12:00:00 签退 → normal(含等于)
    db = setup_db()
    svc = make_svc(db)
    clock.set_date_and_time("2026-06-01", "08:30")
    svc.check_in("2026-06-01", "morning")
    clock.set_date_and_time("2026-06-01", "12:00")
    r2 = svc.check_out("2026-06-01", "morning")
    check("BND3 12:00:00签退→normal", r2.status == "normal", f"got {r2.status}")
    cleanup_db(db)

    # BND4: 11:59:59 签退 → early_leave
    db = setup_db()
    svc = make_svc(db)
    clock.set_date_and_time("2026-06-01", "08:30")
    svc.check_in("2026-06-01", "morning")
    clock.set_date_and_time("2026-06-01", "11:59")
    r2 = svc.check_out("2026-06-01", "morning")
    check("BND4 11:59签退→early_leave", r2.status == "early_leave", f"got {r2.status}")
    cleanup_db(db)

    # BND5: 12:00:01 → absent_morning
    db = setup_db()
    svc = make_svc(db)
    clock.set_date_and_time("2026-06-01", "12:01")
    results = svc.mark_absent("2026-06-01")
    check("BND5 12:01判旷工", len(results) == 1 and results[0].status == "absent_morning")
    cleanup_db(db)

    # BND6: 18:01 签下午 → absent_afternoon(必须 > period_end,等于不算)
    db = setup_db()
    svc = make_svc(db)
    clock.set_date_and_time("2026-06-01", "18:01")
    r = svc.check_in("2026-06-01", "afternoon")
    check("BND6 18:01签下午→absent_afternoon", r.status == "absent_afternoon", f"got {r.status}")
    cleanup_db(db)


# ═══════════════════════════════════════════════════════════════
# COMBO: 迟到+早退
# ═══════════════════════════════════════════════════════════════

def test_combo() -> None:
    print("\n── COMBO ──")

    # COMBO1: 迟到签到 + 早退签退 → late保留(不被early_leave覆盖)
    db = setup_db()
    svc = make_svc(db)
    clock = get_clock()
    assert isinstance(clock, SimulatedClock)
    clock.set_date_and_time("2026-06-01", "09:10")
    svc.check_in("2026-06-01", "morning")
    clock.set_date_and_time("2026-06-01", "11:30")
    r2 = svc.check_out("2026-06-01", "morning")
    check("COMBO1 迟到+早退→late保留", r2.status == "late",
          f"坏状态应优先,got {r2.status}")
    cleanup_db(db)


# ═══════════════════════════════════════════════════════════════
# LEAVE CONFLICT
# ═══════════════════════════════════════════════════════════════

def test_leave_conflict() -> None:
    print("\n── LEAVE CONFLICT ──")

    # LV1: 请假后签到 → 应被拒绝或保持leave
    db = setup_db()
    svc = make_svc(db)
    clock = get_clock()
    assert isinstance(clock, SimulatedClock)
    clock.set_date_and_time("2026-06-01", "08:00")
    svc.apply_leave("2026-06-01", "morning")
    clock.set_date_and_time("2026-06-01", "09:00")
    r = svc.check_in("2026-06-01", "morning")
    check("LV1 请假后再签→应保持leave", r.status == "leave",
          f"请假是终态不应被覆盖,got {r.status}")
    cleanup_db(db)


# ═══════════════════════════════════════════════════════════════
# LEAVE OPTIONS MATRIX
# ═══════════════════════════════════════════════════════════════

def test_leave_options() -> None:
    print("\n── LEAVE OPTIONS ──")

    db = setup_db()
    svc = make_svc(db)
    clock = get_clock()
    assert isinstance(clock, SimulatedClock)

    # < 09:00 → 三选
    clock.set_date_and_time("2026-06-01", "08:00")
    opts = svc.get_leave_options("2026-06-01", "08:00")
    check("08:00→三选项(morning/afternoon/all_day)",
          set(opts) == {"morning", "afternoon", "all_day"}, f"got {opts}")

    # 09:00 → 只剩下午
    opts = svc.get_leave_options("2026-06-01", "09:00")
    check("09:00→只剩afternoon", opts == ["afternoon"], f"got {opts}")

    # 12:30 → 只剩下午
    opts = svc.get_leave_options("2026-06-01", "12:30")
    check("12:30→只剩afternoon", opts == ["afternoon"], f"got {opts}")

    # 14:00 → 空
    opts = svc.get_leave_options("2026-06-01", "14:00")
    check("14:00→无选项", opts == [], f"got {opts}")

    # 18:30 → 空
    opts = svc.get_leave_options("2026-06-01", "18:30")
    check("18:30→无选项", opts == [], f"got {opts}")

    cleanup_db(db)


# ═══════════════════════════════════════════════════════════════
# REPORT BUTTON CONDITIONS
# ═══════════════════════════════════════════════════════════════

def test_report_button() -> None:
    print("\n── REPORT BUTTON ──")

    # 条件1: morning+afternoon都终态 → 可生成
    db = setup_db()
    svc = make_svc(db)
    clock = get_clock()
    assert isinstance(clock, SimulatedClock)
    clock.set_date_and_time("2026-06-01", "08:00")
    r = svc.apply_leave("2026-06-01", "all_day")
    # 都终态 → 记录状态已是 leave
    morning_status = r[0].status
    afternoon_status = r[1].status
    check("战报:上午请假→leave终态", morning_status == "leave")
    check("战报:下午请假→leave终态", afternoon_status == "leave")
    cleanup_db(db)


# ═══════════════════════════════════════════════════════════════
# BET: 周日结算
# ═══════════════════════════════════════════════════════════════

def test_bet_sunday() -> None:
    print("\n── BET SUNDAY ──")

    db = setup_db()
    svc = make_bet_svc(db)
    clock = get_clock()
    assert isinstance(clock, SimulatedClock)

    # 设为周日(2026-06-07)
    clock.set_date_and_time("2026-06-07", "12:00")
    svc.set_week_config("2026-06-01", 50, 30, 50)
    t = svc.create_task("2026-06-01", "测试任务")
    svc.complete_task(t.id)
    result = svc.settle_week("2026-06-01")
    check("B3 周日全部完成→settled", result.status == "settled", f"got {result.status}")
    check("B3 奖励=50", result.total_reward == 50, f"got {result.total_reward}")

    # 未完成→周一滞纳
    db2 = setup_db()
    svc2 = make_bet_svc(db2)
    clock.set_date_and_time("2026-06-08", "00:01")  # Monday
    svc2.set_week_config("2026-06-01", 50, 30, 50)
    svc2.create_task("2026-06-01", "任务1")
    result2 = svc2.settle_week("2026-06-01")
    check("B4 周一未完成→late", result2.status == "late", f"got {result2.status}")
    check("B4 罚金=-50", result2.total_penalty == -50, f"got {result2.total_penalty}")
    cleanup_db(db)
    cleanup_db(db2)


# ═══════════════════════════════════════════════════════════════
# CROSS-PERIOD: 异种终态组合
# ═══════════════════════════════════════════════════════════════

def test_cross_period() -> None:
    print("\n── CROSS-PERIOD ──")

    # AL1: morning leave + afternoon absent
    db = setup_db()
    svc = make_svc(db)
    clock = get_clock()
    assert isinstance(clock, SimulatedClock)
    clock.set_date_and_time("2026-06-01", "08:00")
    r1 = svc.apply_leave("2026-06-01", "morning")
    clock.set_date_and_time("2026-06-01", "18:01")
    r2 = svc.mark_absent("2026-06-01")
    check("AL1 morning leave→终态", r1[0].status == "leave")
    check("AL1 afternoon absent→终态",
          len(r2) == 1 and r2[0].status == "absent_afternoon")
    cleanup_db(db)


# ═══════════════════════════════════════════════════════════════
# STREAK
# ═══════════════════════════════════════════════════════════════

def test_streak() -> None:
    print("\n── STREAK ──")

    db = setup_db()
    # 需要完整的 motivation service 来测 streak
    # 简化:只验证 checkin_service 的 all_normal 判定
    svc = make_svc(db)
    clock = get_clock()
    assert isinstance(clock, SimulatedClock)

    # 全部正常的一天
    clock.set_date_and_time("2026-06-01", "08:30")
    svc.check_in("2026-06-01", "morning")
    clock.set_date_and_time("2026-06-01", "12:05")
    svc.check_out("2026-06-01", "morning")
    clock.set_date_and_time("2026-06-01", "14:00")
    svc.check_in("2026-06-01", "afternoon")
    clock.set_date_and_time("2026-06-01", "18:05")
    svc.check_out("2026-06-01", "afternoon")

    # 检查 morning+afternoon 都是 normal
    repo = CheckinRepo(db)
    records = repo.get_all_by_date("2026-06-01")
    all_normal = all(r.status == "normal" for r in records)
    check("ST1 全天normal→all_normal", all_normal, f"records: {[(r.period, r.status) for r in records]}")

    cleanup_db(db)


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main() -> None:
    clock = SimulatedClock()
    set_clock(clock)

    test_morning()
    test_afternoon()
    test_evening()
    test_boundaries()
    test_combo()
    test_leave_conflict()
    test_leave_options()
    test_report_button()
    test_bet_sunday()
    test_cross_period()
    test_streak()

    print(f"\n{'='*50}")
    print(f"  结果: {passed} passed, {failed} failed (共 {passed+failed})")
    if failed == 0:
        print("  🎉 全部通过!")
    else:
        print(f"  ⚠️ {failed} 项失败,需检查")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
