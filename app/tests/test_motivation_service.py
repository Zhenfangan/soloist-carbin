"""MotivationService 激励模块测试"""

from __future__ import annotations

from app.interfaces.notifier import Notifier
from app.models.checkin import Checkin
from app.repositories.checkin_repo import CheckinRepo
from app.repositories.settings_repo import SettingsRepo
from app.repositories.streak_repo import StreakRepo
from app.services.motivation_service import MotivationService


class MockNotifier(Notifier):
    def __init__(self) -> None:
        self.last_title: str = ""
        self.last_content: str = ""

    def show_ongoing(self, title: str, content: str) -> None:
        self.last_title = title
        self.last_content = content

    def send_reminder(self, title: str, content: str) -> None:
        pass

    def cancel_all(self) -> None:
        pass


class TestMotivationService:
    def setup_svc(self, temp_db: str) -> MotivationService:
        return MotivationService(
            CheckinRepo(temp_db), StreakRepo(temp_db),
            SettingsRepo(temp_db), MockNotifier(),
        )

    def test_initial_streak_zero(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        assert svc.get_current_streak() == 0

    def test_streak_increases_on_normal(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        repo = CheckinRepo(temp_db)
        repo.upsert(Checkin(checkin_date="2026-06-01", period="morning", status="normal"))
        repo.upsert(Checkin(checkin_date="2026-06-01", period="afternoon", status="normal"))

        svc.update_streak("2026-06-01")  # 2026-06-01 is a Monday (workday)
        assert svc.get_current_streak() == 1

    def test_streak_resets_on_late(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        repo = CheckinRepo(temp_db)
        repo.upsert(Checkin(checkin_date="2026-06-01", period="morning", status="normal"))
        repo.upsert(Checkin(checkin_date="2026-06-01", period="afternoon", status="normal"))
        svc.update_streak("2026-06-01")

        repo.upsert(Checkin(checkin_date="2026-06-02", period="morning", status="late"))
        repo.upsert(Checkin(checkin_date="2026-06-02", period="afternoon", status="normal"))
        svc.update_streak("2026-06-02")

        assert svc.get_current_streak() == 0

    def test_notification_checked_in(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        svc.update_notification("checked_in")
        notifier = svc._notifier
        assert isinstance(notifier, MockNotifier)
        assert "已打卡" in notifier.last_content

    def test_notification_not_checked_in(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        svc.update_notification("not_checked_in")
        notifier = svc._notifier
        assert isinstance(notifier, MockNotifier)
        assert "未打卡" in notifier.last_content

    def test_notification_shooting(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        svc.update_notification("shooting")
        notifier = svc._notifier
        assert isinstance(notifier, MockNotifier)
        assert "拍摄中" in notifier.last_content
