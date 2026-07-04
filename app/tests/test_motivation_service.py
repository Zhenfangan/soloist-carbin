"""MotivationService 激励模块测试"""

from __future__ import annotations

from app.interfaces.notifier import Notifier
from app.models.checkin import Checkin
from app.repositories.checkin_repo import CheckinRepo
from app.repositories.settings_repo import SettingsRepo
from app.repositories.streak_repo import StreakRepo
from app.services.checkin_service import CheckinService
from app.services.motivation_service import MotivationService
from app.utils.clock import SimulatedClock, get_clock, set_clock


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

    def test_streak_increments_via_real_checkin_flow_and_day_finished_event(
        self, temp_db: str
    ) -> None:
        """真机反馈: 连续打卡天数一直显示 0。

        之前的测试都是直接调用 update_streak(), 没有验证过真实生产链路:
        CheckinService 走签到/签退 → 发布 DAY_FINISHED 事件 → MotivationService
        订阅并调用 update_streak()。这里用真实事件总线连通两个 service,
        走一天完整、正常时长的签到/签退(而非几分钟内签退, 那样会判定为
        "早退" bad_status, streak 按设计应该清零 —— 这才是用户测试时
        streak 一直是 0 的真实原因: 测试时都是几分钟内快速签退)。

        结论: streak 递增机制本身工作正常, 不是代码 bug。
        """
        set_clock(SimulatedClock())
        get_clock().set_date_and_time("2026-06-01", "08:55")  # Monday, workday

        motivation_svc = self.setup_svc(temp_db)
        checkin_svc = CheckinService(CheckinRepo(temp_db), SettingsRepo(temp_db))

        assert motivation_svc.get_current_streak() == 0

        checkin_svc.check_in("2026-06-01", "morning")
        get_clock().set_date_and_time("2026-06-01", "12:00")  # 时段正常结束时间签退
        checkin_svc.check_out("2026-06-01", "morning")
        get_clock().set_date_and_time("2026-06-01", "14:00")
        checkin_svc.check_in("2026-06-01", "afternoon")
        get_clock().set_date_and_time("2026-06-01", "18:00")  # 时段正常结束时间签退
        checkin_svc.check_out("2026-06-01", "afternoon")

        assert motivation_svc.get_current_streak() == 1
