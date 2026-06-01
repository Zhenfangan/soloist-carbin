"""激励模块服务层 — 连续出勤天数 + 通知栏卡片"""

from __future__ import annotations

from app.interfaces.notifier import Notifier
from app.repositories.checkin_repo import CheckinRepo
from app.repositories.settings_repo import SettingsRepo
from app.repositories.streak_repo import StreakRepo
from app.services.event_bus import EventType, get_event_bus
from app.utils.config import STATUS_LEAVE, STATUS_SHOOTING


class MotivationService:
    """连续出勤统计 + 通知栏管理"""

    def __init__(
        self,
        checkin_repo: CheckinRepo,
        streak_repo: StreakRepo,
        settings_repo: SettingsRepo,
        notifier: Notifier,
    ) -> None:
        self._checkin_repo = checkin_repo
        self._streak_repo = streak_repo
        self._settings_repo = settings_repo
        self._notifier = notifier

        get_event_bus().subscribe(EventType.DAY_FINISHED, self._on_day_finished)

    def get_current_streak(self) -> int:
        """返回当前连续正常出勤天数"""
        streak = self._streak_repo.get()
        return streak.current_streak

    def update_streak(self, date: str) -> int:
        """每天 DAY_FINISHED 后更新连续天数"""
        records = self._checkin_repo.get_all_by_date(date)

        if not records:
            return self.get_current_streak()

        # 判断是否是工作日
        from datetime import datetime
        dt = datetime.strptime(date, "%Y-%m-%d")
        weekday = dt.isoweekday()  # 1=Monday
        work_days_str = self._get_setting("work_days")
        work_days = [int(x.strip()) for x in work_days_str.split(",") if x.strip()]

        if weekday not in work_days:
            return self.get_current_streak()

        # 检查所有非加班时段
        morning_afternoon = [r for r in records if r.period in ("morning", "afternoon")]

        # 如果全是 shooting → 不变
        if all(r.status == STATUS_SHOOTING for r in morning_afternoon):
            return self.get_current_streak()

        # 如果有 late/early_leave/absent/leave → 归零
        bad_statuses = {"late", "early_leave", "absent_morning", "absent_afternoon", STATUS_LEAVE}
        for r in morning_afternoon:
            if r.status in bad_statuses:
                self._streak_repo.update(0, date)
                return 0

        # 全部 normal → +1
        streak = self._streak_repo.get()
        new_streak = streak.current_streak + 1
        self._streak_repo.update(new_streak, date)
        return new_streak

    def update_notification(self, status: str) -> None:
        """更新 Android 通知栏常驻卡片"""
        notifications = {
            "checked_in": ("Soloist Cabin Pro", "今日已打卡 ✅"),
            "not_checked_in": ("Soloist Cabin Pro", "今日未打卡 ⏳"),
            "shooting": ("Soloist Cabin Pro", "拍摄中 \U0001f4f8"),
        }
        title, content = notifications.get(status, ("Soloist Cabin Pro", ""))
        self._notifier.show_ongoing(title, content)

    def _get_setting(self, key: str) -> str:
        val = self._settings_repo.get(key)
        if val is not None:
            return val
        from app.services.settings_service import SettingsService
        return SettingsService.DEFAULTS.get(key, "")

    def _on_day_finished(self, event_type: EventType, payload: dict[str, object]) -> None:
        date = str(payload.get("date", ""))
        if date:
            self.update_streak(date)
