"""PenaltyService 奖惩服务测试"""

from __future__ import annotations

from app.models.checkin import Checkin
from app.repositories.checkin_repo import CheckinRepo
from app.repositories.ledger_repo import LedgerRepo
from app.repositories.settings_repo import SettingsRepo
from app.services.penalty_service import PenaltyService


class TestPenaltyService:
    def setup_svc(self, temp_db: str) -> PenaltyService:
        return PenaltyService(
            CheckinRepo(temp_db), LedgerRepo(temp_db), SettingsRepo(temp_db)
        )

    def test_late_penalty(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        repo = CheckinRepo(temp_db)
        repo.upsert(Checkin(checkin_date="2026-06-01", period="morning", status="late"))

        entries = svc.calculate_daily("2026-06-01")
        assert len(entries) == 1
        assert entries[0].type == "late"
        assert entries[0].amount == -10

    def test_early_leave_penalty(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        repo = CheckinRepo(temp_db)
        repo.upsert(Checkin(checkin_date="2026-06-01", period="afternoon", status="early_leave"))

        entries = svc.calculate_daily("2026-06-01")
        assert len(entries) == 1
        assert entries[0].type == "early_leave"
        assert entries[0].amount == -10

    def test_absent_penalty(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        repo = CheckinRepo(temp_db)
        repo.upsert(Checkin(checkin_date="2026-06-01", period="morning", status="absent_morning"))

        entries = svc.calculate_daily("2026-06-01")
        assert len(entries) == 1
        assert entries[0].type == "absent"
        assert entries[0].amount == -50

    def test_multiple_penalties(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        repo = CheckinRepo(temp_db)
        repo.upsert(Checkin(checkin_date="2026-06-01", period="morning", status="late"))
        repo.upsert(Checkin(checkin_date="2026-06-01", period="afternoon", status="early_leave"))

        entries = svc.calculate_daily("2026-06-01")
        assert len(entries) == 2

    def test_full_attendance_bonus(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        repo = CheckinRepo(temp_db)
        for i in range(7):
            date = f"2026-06-0{i+1}"
            repo.upsert(Checkin(checkin_date=date, period="morning", status="normal"))
            repo.upsert(Checkin(checkin_date=date, period="afternoon", status="normal"))

        bonus = svc.calculate_weekly_full_attendance("2026-06-01")
        assert bonus is not None
        assert bonus.type == "full_attendance_bonus"
        assert bonus.amount == 100

    def test_no_bonus_if_late(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        repo = CheckinRepo(temp_db)
        repo.upsert(Checkin(checkin_date="2026-06-01", period="morning", status="normal"))
        repo.upsert(Checkin(checkin_date="2026-06-01", period="afternoon", status="normal"))
        repo.upsert(Checkin(checkin_date="2026-06-02", period="morning", status="late"))
        repo.upsert(Checkin(checkin_date="2026-06-02", period="afternoon", status="normal"))

        bonus = svc.calculate_weekly_full_attendance("2026-06-01")
        assert bonus is None
