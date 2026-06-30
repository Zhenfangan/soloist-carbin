"""CheckinService 服务层测试"""

from __future__ import annotations

import pytest

from app.repositories.checkin_repo import CheckinRepo
from app.repositories.settings_repo import SettingsRepo
from app.services.checkin_service import CheckinService
from app.utils.clock import SimulatedClock, get_clock


class TestCheckIn:
    @pytest.fixture
    def svc(self, temp_db: str) -> CheckinService:
        return CheckinService(CheckinRepo(temp_db), SettingsRepo(temp_db))

    def test_normal_checkin(self, svc: CheckinService) -> None:
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "08:55")
        result = svc.check_in("2026-06-01", "morning")
        assert result.status == "normal"
        assert result.status_label == "正常"
        assert result.checkin_time == "08:55:00"

    def test_late_checkin(self, svc: CheckinService) -> None:
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "09:10")
        result = svc.check_in("2026-06-01", "morning")
        assert result.status == "late"
        assert result.status_label == "迟到"

    def test_normal_checkout(self, svc: CheckinService) -> None:
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "08:55")
        svc.check_in("2026-06-01", "morning")
        clock.set_date_and_time("2026-06-01", "12:05")
        result = svc.check_out("2026-06-01", "morning")
        assert result.status == "normal"

    def test_early_leave_checkout(self, svc: CheckinService) -> None:
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "08:55")
        svc.check_in("2026-06-01", "morning")
        clock.set_date_and_time("2026-06-01", "11:30")
        result = svc.check_out("2026-06-01", "morning")
        assert result.status == "early_leave"
        assert result.status_label == "早退"

    def test_evening_checkin_always_normal(self, svc: CheckinService) -> None:
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "19:30")
        result = svc.check_in("2026-06-01", "evening")
        assert result.status == "normal"

    def test_evening_period_in_day_status(self, svc: CheckinService) -> None:
        """evening 记录应出现在 DayStatus.periods 中"""
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "19:30")
        svc.check_in("2026-06-01", "evening")
        status = svc.get_today_status("2026-06-01")
        evening = next((p for p in status.periods if p.period == "evening"), None)
        assert evening is not None
        assert evening.status == "normal"
        assert evening.checkin_time == "19:30:00"

    def test_morning_checkin_after_window_closed_is_absent(self, svc: CheckinService) -> None:
        """18:23 签上午 → 时段窗口(12:00)已关闭 → 应判定为旷工(上午)"""
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-04", "18:23")
        result = svc.check_in("2026-06-04", "morning")
        assert result.status == "absent_morning", (
            f"期望 absent_morning (窗口关闭)，实际 {result.status}"
        )

    def test_morning_checkin_before_start_is_normal(self, svc: CheckinService) -> None:
        """08:30 签上午 → 时段未开始但提前到 → 正常"""
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-04", "08:30")
        result = svc.check_in("2026-06-04", "morning")
        assert result.status == "normal", f"期望 normal，实际 {result.status}"

    def test_morning_checkin_at_1100_is_normal(self, svc: CheckinService) -> None:
        """11:00 签上午 → 时段窗口内 > 09:00 → 迟到"""
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-04", "11:00")
        result = svc.check_in("2026-06-04", "morning")
        assert result.status == "late", f"期望 late，实际 {result.status}"

    def test_checkout_preserves_late_status(self, svc: CheckinService) -> None:
        """迟到签到 → 正常签退 → status 应保留 late"""
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "09:10")
        svc.check_in("2026-06-01", "morning")          # late checkin
        clock.set_date_and_time("2026-06-01", "12:05")
        result = svc.check_out("2026-06-01", "morning")  # normal checkout time
        assert result.status == "late", (
            f"迟到签到不应被正常签退覆盖，期望 late，实际 {result.status}"
        )

    def test_day_status_flags_late_and_early_leave(self, svc: CheckinService) -> None:
        """迟到签到 + 早退签退：status 被压成 late，但 get_today_status 必须
        同时给出 is_late=True 与 is_early_leave=True，供 UI 完整展示两个违规。"""
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "09:10")
        svc.check_in("2026-06-01", "morning")            # 迟到
        clock.set_date_and_time("2026-06-01", "11:30")
        svc.check_out("2026-06-01", "morning")           # 早退
        status = svc.get_today_status("2026-06-01")
        morning = next(p for p in status.periods if p.period == "morning")
        assert morning.status == "late"          # 单值枚举仍是 late
        assert morning.is_late is True
        assert morning.is_early_leave is True    # 早退不再被吞

    def test_day_status_flags_early_leave_only(self, svc: CheckinService) -> None:
        """正常签到 + 早退签退：is_late=False, is_early_leave=True"""
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "08:55")
        svc.check_in("2026-06-01", "morning")
        clock.set_date_and_time("2026-06-01", "11:30")
        svc.check_out("2026-06-01", "morning")
        status = svc.get_today_status("2026-06-01")
        morning = next(p for p in status.periods if p.period == "morning")
        assert morning.is_late is False
        assert morning.is_early_leave is True

    def test_checkout_after_window_closed_normal(self, svc: CheckinService) -> None:
        """签退时间超过下班时间 → 正常（加班）"""
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "08:55")
        svc.check_in("2026-06-01", "morning")
        clock.set_date_and_time("2026-06-01", "18:30")
        result = svc.check_out("2026-06-01", "morning")
        assert result.status == "normal", f"超时签退应正常，实际 {result.status}"

    def test_checkout_without_checkin_rejected(self, svc: CheckinService) -> None:
        """无签到直接签退 → 应抛出异常"""
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "12:05")
        with pytest.raises(ValueError, match="尚未签到"):
            svc.check_out("2026-06-01", "morning")

    def test_evening_checkout_always_normal(self, svc: CheckinService) -> None:
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "20:30")
        svc.check_in("2026-06-01", "evening")
        clock.set_date_and_time("2026-06-01", "22:00")
        result = svc.check_out("2026-06-01", "evening")
        assert result.status == "normal"

    def test_day_finished_event(self, svc: CheckinService) -> None:
        from app.services.event_bus import EventType, get_event_bus

        events: list[str] = []

        def handler(et: EventType, p: object) -> None:
            events.append(et.value)

        bus = get_event_bus()
        bus.subscribe(EventType.DAY_FINISHED, handler)

        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "08:55")
        svc.check_in("2026-06-01", "morning")
        clock.advance(minutes=5)
        svc.check_out("2026-06-01", "morning")
        clock.set_date_and_time("2026-06-01", "13:55")
        svc.check_in("2026-06-01", "afternoon")
        clock.advance(minutes=5)
        svc.check_out("2026-06-01", "afternoon")

        assert "day_finished" in events


class TestLeave:
    @pytest.fixture
    def svc(self, temp_db: str) -> CheckinService:
        return CheckinService(CheckinRepo(temp_db), SettingsRepo(temp_db))

    def test_leave_options_before_morning(self, svc: CheckinService) -> None:
        options = svc.get_leave_options("2026-06-01", "08:00")
        assert "morning" in options
        assert "afternoon" in options
        assert "all_day" in options

    def test_leave_options_afternoon_only(self, svc: CheckinService) -> None:
        options = svc.get_leave_options("2026-06-01", "12:30")
        assert options == ["afternoon"]

    def test_leave_options_none(self, svc: CheckinService) -> None:
        options = svc.get_leave_options("2026-06-01", "15:00")
        assert options == []

    def test_apply_morning_leave(self, svc: CheckinService) -> None:
        results = svc.apply_leave("2026-06-01", "morning")
        assert len(results) == 1
        assert results[0].period == "morning"
        assert results[0].status == "leave"

    def test_apply_all_day_leave(self, svc: CheckinService) -> None:
        results = svc.apply_leave("2026-06-01", "all_day")
        assert len(results) == 2
        assert all(r.status == "leave" for r in results)


class TestAbsent:
    @pytest.fixture
    def svc(self, temp_db: str) -> CheckinService:
        return CheckinService(CheckinRepo(temp_db), SettingsRepo(temp_db))

    def test_mark_morning_absent(self, svc: CheckinService) -> None:
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        # mark_absent 要求 current >= period_end(12:00) 才判定,10:05 还在窗口内
        clock.set_date_and_time("2026-06-01", "12:01")
        results = svc.mark_absent("2026-06-01")
        assert len(results) == 1
        assert results[0].status == "absent_morning"

    def test_no_absent_if_checked_in(self, svc: CheckinService) -> None:
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "08:55")
        svc.check_in("2026-06-01", "morning")
        clock.set_date_and_time("2026-06-01", "10:05")
        results = svc.mark_absent("2026-06-01")
        assert len(results) == 0

    def test_no_absent_if_on_leave(self, svc: CheckinService) -> None:
        svc.apply_leave("2026-06-01", "morning")
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "10:05")
        results = svc.mark_absent("2026-06-01")
        assert len(results) == 0

    def test_not_absent_before_deadline(self, svc: CheckinService) -> None:
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "09:30")  # < 1h
        results = svc.mark_absent("2026-06-01")
        assert len(results) == 0


class TestAutoCheckout:
    @pytest.fixture
    def svc(self, temp_db: str) -> CheckinService:
        return CheckinService(CheckinRepo(temp_db), SettingsRepo(temp_db))

    def test_auto_checkout_unchecked_period(self, svc: CheckinService) -> None:
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "08:55")
        svc.check_in("2026-06-01", "morning")
        # Simulate that user forgot to checkout - run auto_checkout for previous day
        results = svc.auto_checkout("2026-06-01")
        assert len(results) == 1
        assert results[0].checkout_time == "12:00"
        assert results[0].period == "morning"

    def test_auto_checkout_skips_checked_out(self, svc: CheckinService) -> None:
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "08:55")
        svc.check_in("2026-06-01", "morning")
        clock.set_date_and_time("2026-06-01", "12:05")
        svc.check_out("2026-06-01", "morning")
        results = svc.auto_checkout("2026-06-01")
        assert len(results) == 0


class TestDayStatus:
    @pytest.fixture
    def svc(self, temp_db: str) -> CheckinService:
        return CheckinService(CheckinRepo(temp_db), SettingsRepo(temp_db))

    def test_empty_day(self, svc: CheckinService) -> None:
        status = svc.get_today_status("2026-06-01")
        assert status.date == "2026-06-01"
        assert len(status.periods) == 3
        assert all(p.status == "pending" for p in status.periods)

    def test_partial_day(self, svc: CheckinService) -> None:
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "08:55")
        svc.check_in("2026-06-01", "morning")
        status = svc.get_today_status("2026-06-01")
        morning = next(p for p in status.periods if p.period == "morning")
        assert morning.status == "normal"
        afternoon = next(p for p in status.periods if p.period == "afternoon")
        assert afternoon.status == "pending"
