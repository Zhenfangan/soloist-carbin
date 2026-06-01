"""提醒服务 — 打卡提醒调度"""

from __future__ import annotations

from app.interfaces.alarm_scheduler import AlarmScheduler
from app.repositories.settings_repo import SettingsRepo


class ReminderService:
    """打卡提醒调度"""

    REMINDER_TAGS = [
        "morning_checkin_reminder",
        "morning_checkout_reminder",
        "afternoon_checkin_reminder",
        "afternoon_checkout_reminder",
    ]

    def __init__(
        self,
        settings_repo: SettingsRepo,
        alarm_scheduler: AlarmScheduler,
    ) -> None:
        self._settings_repo = settings_repo
        self._alarm = alarm_scheduler

    def schedule_all(self) -> None:
        """调度今天的四个提醒时间点"""
        self.cancel_all()

        morning_start = self._get_setting("morning_start")
        morning_end = self._get_setting("morning_end")
        afternoon_start = self._get_setting("afternoon_start")
        afternoon_end = self._get_setting("afternoon_end")

        reminders = [
            ("morning_checkin_reminder", self._sub_5_min(morning_start)),
            ("morning_checkout_reminder", morning_end),
            ("afternoon_checkin_reminder", self._sub_5_min(afternoon_start)),
            ("afternoon_checkout_reminder", afternoon_end),
        ]

        for tag, alarm_time in reminders:
            self._alarm.schedule(alarm_time, tag)

    def cancel_all(self) -> None:
        """取消所有提醒"""
        for tag in self.REMINDER_TAGS:
            self._alarm.cancel(tag)

    def _get_setting(self, key: str) -> str:
        val = self._settings_repo.get(key)
        if val is not None:
            return val
        from app.services.settings_service import SettingsService
        return SettingsService.DEFAULTS.get(key, "")

    @staticmethod
    def _sub_5_min(time_str: str) -> str:
        """时间减 5 分钟"""
        parts = time_str.split(":")
        h = int(parts[0])
        m = int(parts[1]) - 5
        if m < 0:
            m += 60
            h = (h - 1) % 24
        return f"{h:02d}:{m:02d}"
