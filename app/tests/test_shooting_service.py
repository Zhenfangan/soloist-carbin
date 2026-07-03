"""ShootingService 拍摄日模块测试"""

from __future__ import annotations

from app.repositories.ledger_repo import LedgerRepo
from app.repositories.settings_repo import SettingsRepo
from app.repositories.shooting_repo import ShootingRepo
from app.services.shooting_service import ShootingService
from app.utils.clock import SimulatedClock, get_clock
from app.utils.config import LEDGER_TYPE_SHOOTING_REWARD


class TestShootingService:
    def setup_svc(self, temp_db: str) -> ShootingService:
        return ShootingService(ShootingRepo(temp_db))

    def test_set_shooting_day(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        day = svc.set_shooting_day("2026-06-15", "一杯奶茶")
        assert day.id is not None
        assert svc.is_shooting_day("2026-06-15")

    def test_not_shooting_day(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        assert not svc.is_shooting_day("2026-06-15")

    def test_cancel_before_morning_start(self, temp_db: str) -> None:
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "08:00")

        svc = self.setup_svc(temp_db)
        svc.set_shooting_day("2026-06-01")
        result = svc.cancel_shooting_day("2026-06-01")
        assert result is True
        assert not svc.is_shooting_day("2026-06-01")

    def test_cancel_after_morning_start_fails(self, temp_db: str) -> None:
        clock = get_clock()
        assert isinstance(clock, SimulatedClock)
        clock.set_date_and_time("2026-06-01", "09:30")

        svc = self.setup_svc(temp_db)
        svc.set_shooting_day("2026-06-01")
        result = svc.cancel_shooting_day("2026-06-01")
        assert result is False
        assert svc.is_shooting_day("2026-06-01")

    def test_reflection_questions(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        questions = svc.get_reflection_questions()
        assert len(questions) == 4

    def test_submit_reflection_smooth(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        ref = svc.submit_reflection("2026-06-01", {
            "content": "产品宣传片",
            "location": "创意园",
            "smoothness": "smooth",
            "thoughts": "光线很好很顺利",
        })
        assert ref.id is not None
        assert ref.summary is not None
        assert ("顺利" in ref.summary or "高效" in ref.summary)

    def test_submit_reflection_rough(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        ref = svc.submit_reflection("2026-06-01", {
            "content": "外景视频",
            "location": "海边",
            "smoothness": "rough",
            "thoughts": "风太大拍得很困难",
        })
        assert ref.summary is not None
        assert "挑战" in ref.summary

    def test_submit_reflection_normal(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        ref = svc.submit_reflection("2026-06-01", {
            "content": "采访",
            "location": "咖啡厅",
            "smoothness": "normal",
            "thoughts": "一切顺利",
        })
        assert ref.summary is not None
        assert ref.summary != ""

    def test_submit_reflection_credits_shooting_reward(self, temp_db: str) -> None:
        ledger = LedgerRepo(temp_db)
        svc = ShootingService(ShootingRepo(temp_db), ledger, SettingsRepo(temp_db))
        svc.submit_reflection("2026-06-01", {
            "content": "宣传片",
            "location": "创意园",
            "smoothness": "smooth",
            "thoughts": "光线很好",
        })
        rewards = [
            e for e in ledger.get_by_date("2026-06-01")
            if e.type == LEDGER_TYPE_SHOOTING_REWARD
        ]
        assert len(rewards) == 1
        assert rewards[0].amount == 30  # shooting_reward 默认值

    def test_submit_reflection_no_double_credit(self, temp_db: str) -> None:
        ledger = LedgerRepo(temp_db)
        svc = ShootingService(ShootingRepo(temp_db), ledger, SettingsRepo(temp_db))
        answers = {"content": "x", "location": "y", "smoothness": "normal", "thoughts": "z"}
        svc.submit_reflection("2026-06-01", answers)
        svc.submit_reflection("2026-06-01", answers)  # 再次编辑复盘
        rewards = [
            e for e in ledger.get_by_date("2026-06-01")
            if e.type == LEDGER_TYPE_SHOOTING_REWARD
        ]
        assert len(rewards) == 1  # 仍只入账一次
