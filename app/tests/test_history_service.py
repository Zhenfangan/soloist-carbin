"""HistoryService 历史模块测试"""

from __future__ import annotations

from app.models.checkin import Checkin
from app.repositories.checkin_repo import CheckinRepo
from app.repositories.ledger_repo import LedgerRepo
from app.repositories.shooting_repo import ShootingRepo
from app.services.history_service import HistoryService


class TestHistoryService:
    def setup_svc(self, temp_db: str) -> HistoryService:
        return HistoryService(CheckinRepo(temp_db), LedgerRepo(temp_db), ShootingRepo(temp_db))

    def test_empty_week_view(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        view = svc.get_week_view("2026-06-01")
        assert view.week_start == "2026-06-01"
        assert view.week_end == "2026-06-07"
        assert len(view.days) == 7
        assert view.weekly_net == 0.0

    def test_week_view_with_data(self, temp_db: str) -> None:
        checkin_repo = CheckinRepo(temp_db)
        checkin_repo.upsert(Checkin(
            checkin_date="2026-06-01", period="morning",
            checkin_time="09:00:00", checkout_time="12:00:00", status="normal",
        ))

        svc = self.setup_svc(temp_db)
        view = svc.get_week_view("2026-06-01")
        monday = view.days[0]
        assert monday.date == "2026-06-01"
        assert len(monday.periods) == 1
        assert monday.total_hours == 3.0

    def test_month_view_colors(self, temp_db: str) -> None:
        checkin_repo = CheckinRepo(temp_db)
        checkin_repo.upsert(Checkin(
            checkin_date="2026-06-01", period="morning",
            checkin_time="09:00:00", checkout_time="12:00:00", status="normal",
        ))
        checkin_repo.upsert(Checkin(
            checkin_date="2026-06-01", period="afternoon",
            checkin_time="14:00:00", checkout_time="18:00:00", status="normal",
        ))
        checkin_repo.upsert(Checkin(
            checkin_date="2026-06-02", period="morning", status="late",
        ))

        svc = self.setup_svc(temp_db)
        view = svc.get_month_view(2026, 6)
        assert len(view.cells) == 30

        # Day 1 (June 1) should be green (all normal)
        cell1 = view.cells[0]
        assert cell1.color == "green"

        # Day 2 (June 2) should be yellow (late)
        cell2 = view.cells[1]
        assert cell2.color == "yellow"

    def test_year_view(self, temp_db: str) -> None:
        checkin_repo = CheckinRepo(temp_db)
        for month in (1, 3, 5):
            checkin_repo.upsert(Checkin(
                checkin_date=f"2026-{month:02d}-01", period="morning",
                checkin_time="09:00:00", checkout_time="12:00:00", status="normal",
            ))

        svc = self.setup_svc(temp_db)
        view = svc.get_year_view(2026)
        assert len(view.months) == 12

        jan = view.months[0]
        assert jan.month == 1
        assert jan.work_days == 1

        feb = view.months[1]
        assert feb.work_days == 0
