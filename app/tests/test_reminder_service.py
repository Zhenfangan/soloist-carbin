"""ReminderService 测试"""

from __future__ import annotations

from app.interfaces.alarm_scheduler import AlarmScheduler
from app.repositories.settings_repo import SettingsRepo
from app.services.reminder_service import ReminderService


class MockAlarmScheduler(AlarmScheduler):
    def __init__(self) -> None:
        self.scheduled: list[tuple[str, str]] = []
        self.cancelled: list[str] = []

    def schedule(self, alarm_time: str, tag: str) -> None:
        self.scheduled.append((tag, alarm_time))

    def cancel(self, tag: str) -> None:
        self.cancelled.append(tag)

    def cancel_all(self) -> None:
        self.cancelled.extend(["morning_checkin_reminder", "morning_checkout_reminder",
                               "afternoon_checkin_reminder", "afternoon_checkout_reminder"])


class TestReminderService:
    def test_schedule_all_schedules_4_reminders(self, temp_db: str) -> None:
        alarm = MockAlarmScheduler()
        svc = ReminderService(SettingsRepo(temp_db), alarm)
        svc.schedule_all()
        assert len(alarm.scheduled) == 4

    def test_sub_5_min(self, temp_db: str) -> None:
        alarm = MockAlarmScheduler()
        svc = ReminderService(SettingsRepo(temp_db), alarm)
        svc.schedule_all()
        morning_tag, morning_time = alarm.scheduled[0]
        assert morning_time == "08:55"  # 09:00 - 5 min

    def test_cancel_all(self, temp_db: str) -> None:
        alarm = MockAlarmScheduler()
        svc = ReminderService(SettingsRepo(temp_db), alarm)
        svc.cancel_all()
        assert len(alarm.cancelled) == 4
