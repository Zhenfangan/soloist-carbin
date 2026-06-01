"""M9 时间抽象层测试"""

from __future__ import annotations

from datetime import datetime

from app.utils.clock import SimulatedClock, SystemClock, get_clock, set_clock


class TestSystemClock:
    def test_now_returns_datetime(self) -> None:
        clock = SystemClock()
        now = clock.now()
        assert isinstance(now, datetime)

    def test_today_str_format(self) -> None:
        clock = SystemClock()
        today = clock.today_str()
        assert len(today) == 10
        assert today[4] == "-"
        assert today[7] == "-"

    def test_current_time_str_format(self) -> None:
        clock = SystemClock()
        time_str = clock.current_time_str()
        parts = time_str.split(":")
        assert len(parts) == 3


class TestSimulatedClock:
    def test_default_start_time(self) -> None:
        clock = SimulatedClock()
        assert clock.now() == datetime(2026, 1, 1, 8, 0, 0)

    def test_set_date_and_time(self) -> None:
        clock = SimulatedClock()
        clock.set_date_and_time("2026-06-01", "08:55")
        assert clock.now() == datetime(2026, 6, 1, 8, 55, 0)

    def test_today_str(self) -> None:
        clock = SimulatedClock()
        clock.set_date_and_time("2026-06-01", "14:30")
        assert clock.today_str() == "2026-06-01"

    def test_current_time_str(self) -> None:
        clock = SimulatedClock()
        clock.set_date_and_time("2026-06-01", "14:30:45")
        assert clock.current_time_str() == "14:30:45"

    def test_advance_minutes(self) -> None:
        clock = SimulatedClock()
        clock.set_date_and_time("2026-06-01", "08:50")
        clock.advance(minutes=30)
        assert clock.current_time_str() == "09:20:00"

    def test_advance_hours(self) -> None:
        clock = SimulatedClock()
        clock.set_date_and_time("2026-06-01", "08:00")
        clock.advance(hours=2)
        assert clock.current_time_str() == "10:00:00"

    def test_advance_mixed(self) -> None:
        clock = SimulatedClock()
        clock.set_date_and_time("2026-06-01", "08:00")
        clock.advance(hours=2, minutes=15)
        assert clock.current_time_str() == "10:15:00"

    def test_advance_days(self) -> None:
        clock = SimulatedClock()
        clock.set_date_and_time("2026-06-01", "08:00")
        clock.advance_days(3)
        assert clock.today_str() == "2026-06-04"

    def test_advance_crosses_midnight(self) -> None:
        clock = SimulatedClock()
        clock.set_date_and_time("2026-06-01", "23:30")
        clock.advance(hours=1)
        assert clock.today_str() == "2026-06-02"

    def test_set_time_directly(self) -> None:
        clock = SimulatedClock()
        clock.set_time(datetime(2026, 12, 25, 10, 30, 0))
        assert clock.now() == datetime(2026, 12, 25, 10, 30, 0)

    def test_speed_setting(self) -> None:
        clock = SimulatedClock()
        clock.set_speed(60.0)
        assert clock._speed == 60.0

    def test_pause_resume(self) -> None:
        clock = SimulatedClock()
        assert not clock.is_paused()
        clock.pause()
        assert clock.is_paused()
        clock.resume()
        assert not clock.is_paused()


class TestClockSingleton:
    def test_get_clock_defaults_to_system(self) -> None:
        import app.utils.clock as mod

        mod._clock = None
        clock = get_clock()
        assert isinstance(clock, SystemClock)

    def test_set_clock_overrides(self) -> None:
        sim = SimulatedClock()
        set_clock(sim)
        assert get_clock() is sim

    def test_set_clock_affects_get(self) -> None:
        sim = SimulatedClock()
        sim.set_date_and_time("2026-07-15", "12:00")
        set_clock(sim)
        clock = get_clock()
        assert clock.today_str() == "2026-07-15"
