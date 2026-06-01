"""SettingsService 服务层测试"""

from __future__ import annotations

from typing import Any

import pytest

from app.repositories.settings_repo import SettingsRepo
from app.services.event_bus import EventType, get_event_bus
from app.services.settings_service import SettingsService


class TestSettingsService:
    @pytest.fixture
    def svc(self, temp_db: str) -> SettingsService:
        return SettingsService(SettingsRepo(temp_db))

    def test_get_returns_default_when_not_set(self, svc: SettingsService) -> None:
        assert svc.get("morning_start") == "09:00"

    def test_set_and_get(self, svc: SettingsService) -> None:
        svc.set("morning_start", "08:00")
        assert svc.get("morning_start") == "08:00"

    def test_get_all_merges_defaults_and_saved(self, svc: SettingsService) -> None:
        svc.set("custom_key", "custom_val")
        result = svc.get_all()
        assert result["morning_start"] == "09:00"  # default
        assert result["custom_key"] == "custom_val"  # saved

    def test_batch_set_writes_multiple(self, svc: SettingsService) -> None:
        svc.batch_set({"morning_start": "07:00", "afternoon_start": "13:00"})
        assert svc.get("morning_start") == "07:00"
        assert svc.get("afternoon_start") == "13:00"

    def test_is_first_launch_true_initially(self, svc: SettingsService) -> None:
        assert svc.is_first_launch() is True

    def test_complete_onboarding_marks_first_launch_false(self, svc: SettingsService) -> None:
        svc.complete_onboarding()
        assert svc.is_first_launch() is False

    def test_set_publishes_event(self, svc: SettingsService) -> None:
        events: list[dict[str, Any]] = []

        def handler(et: EventType, payload: dict[str, Any]) -> None:
            events.append(payload)

        get_event_bus().subscribe(EventType.SETTINGS_CHANGED, handler)
        svc.set("late_penalty", "20")
        assert len(events) == 1
        assert events[0]["key"] == "late_penalty"

    def test_get_work_days_defaults(self, svc: SettingsService) -> None:
        assert svc.get_work_days() == [1, 2, 3, 4, 5]

    def test_get_work_days_custom(self, svc: SettingsService) -> None:
        svc.set("work_days", "1,3,5")
        assert svc.get_work_days() == [1, 3, 5]

    def test_is_work_day(self, svc: SettingsService) -> None:
        assert svc.is_work_day(1) is True  # Monday
        assert svc.is_work_day(6) is False  # Saturday

    def test_get_unknown_key_returns_empty_string(self, svc: SettingsService) -> None:
        assert svc.get("nonexistent_key") == ""
