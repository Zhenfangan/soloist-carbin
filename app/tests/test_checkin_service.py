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

    def test_night_checkin_always_normal(self, svc: CheckinService) -> None:
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "19:30")
        result = svc.check_in("2026-06-01", "night")
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
        clock.set_date_and_time("2026-06-01", "10:05")  # 1h+ after 09:00
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
