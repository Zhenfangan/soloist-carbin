"""CheckinService 拍摄日编排测试 — 同时写两套表示 + 撤销"""

from __future__ import annotations

import pytest

from app.repositories.checkin_repo import CheckinRepo
from app.repositories.settings_repo import SettingsRepo
from app.repositories.shooting_repo import ShootingRepo
from app.services.checkin_service import CheckinService
from app.services.shooting_service import ShootingService
from app.utils.clock import SimulatedClock, get_clock


def _make_svc(temp_db: str) -> CheckinService:
    shooting = ShootingService(ShootingRepo(temp_db))
    return CheckinService(CheckinRepo(temp_db), SettingsRepo(temp_db), shooting)


class TestShootingDayOrchestration:
    def test_set_shooting_day_marks_all_periods(self, temp_db: str) -> None:
        svc = _make_svc(temp_db)
        svc.set_shooting_day("2026-06-01", "一杯奶茶")
        day = svc.get_today_status("2026-06-01")
        assert day.is_shooting_day is True
        assert [p.status for p in day.periods] == ["shooting", "shooting", "shooting"]

    def test_set_shooting_day_writes_shooting_table(self, temp_db: str) -> None:
        shooting = ShootingService(ShootingRepo(temp_db))
        svc = CheckinService(CheckinRepo(temp_db), SettingsRepo(temp_db), shooting)
        svc.set_shooting_day("2026-06-01")
        # 表示 A(shooting_days 表)也要被写入
        assert shooting.is_shooting_day("2026-06-01") is True

    def test_cancel_shooting_day_within_window_reverts(self, temp_db: str) -> None:
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "08:00")  # 上午上班前
        svc = _make_svc(temp_db)
        svc.set_shooting_day("2026-06-01")
        ok = svc.cancel_shooting_day("2026-06-01")
        assert ok is True
        day = svc.get_today_status("2026-06-01")
        assert day.is_shooting_day is False
        assert [p.status for p in day.periods] == ["pending", "pending", "pending"]

    def test_cancel_shooting_day_outside_window_fails(self, temp_db: str) -> None:
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "09:30")  # 已过上午上班时间
        svc = _make_svc(temp_db)
        svc.set_shooting_day("2026-06-01")
        ok = svc.cancel_shooting_day("2026-06-01")
        assert ok is False
        assert svc.get_today_status("2026-06-01").is_shooting_day is True
