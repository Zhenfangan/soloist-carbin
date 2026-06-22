"""ReportService 战报服务测试"""

from __future__ import annotations

from app.models.checkin import Checkin
from app.repositories.checkin_repo import CheckinRepo
from app.repositories.ledger_repo import LedgerRepo
from app.repositories.shooting_repo import ShootingRepo
from app.services.report_service import ReportService


class TestReportService:
    def setup_svc(self, temp_db: str) -> ReportService:
        return ReportService(CheckinRepo(temp_db), LedgerRepo(temp_db), ShootingRepo(temp_db))

    def test_collect_data_empty_day(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        data = svc.collect_data("2026-06-01")
        assert data.date == "2026-06-01"
        assert data.total_work_hours == 0.0
        assert data.net_amount == 0.0

    def test_collect_data_with_checkins(self, temp_db: str) -> None:
        # Setup checkins
        checkin_repo = CheckinRepo(temp_db)
        checkin_repo.upsert(Checkin(
            checkin_date="2026-06-01", period="morning",
            checkin_time="09:00:00", checkout_time="12:00:00", status="normal",
        ))
        checkin_repo.upsert(Checkin(
            checkin_date="2026-06-01", period="afternoon",
            checkin_time="14:00:00", checkout_time="18:00:00", status="normal",
        ))

        svc = self.setup_svc(temp_db)
        data = svc.collect_data("2026-06-01")
        assert data.total_work_hours == 7.0  # 3 + 4 hours

    def test_generate_html_office_day(self, temp_db: str) -> None:
        checkin_repo = CheckinRepo(temp_db)
        checkin_repo.upsert(Checkin(
            checkin_date="2026-06-01", period="morning",
            checkin_time="09:00:00", checkout_time="12:00:00", status="normal",
        ))

        svc = self.setup_svc(temp_db)
        data = svc.collect_data("2026-06-01")
        html = svc.generate_html(data)
        assert "2026-06-01" in html
        assert "办公日" in html

    def test_generate_html_shooting_day(self, temp_db: str) -> None:
        shooting_repo = ShootingRepo(temp_db)
        from app.models.shooting import ShootingDay
        shooting_repo.set_shooting_day(ShootingDay(shoot_date="2026-06-15"))

        checkin_repo = CheckinRepo(temp_db)
        checkin_repo.upsert(Checkin(
            checkin_date="2026-06-15", period="morning",
            checkin_time="09:00:00", checkout_time="18:00:00",
            status="shooting", is_shooting=1,
        ))

        svc = self.setup_svc(temp_db)
        data = svc.collect_data("2026-06-15")
        html = svc.generate_html(data)
        assert "拍摄日" in html

    def test_over_8_hours_shows_overtime(self, temp_db: str) -> None:
        checkin_repo = CheckinRepo(temp_db)
        checkin_repo.upsert(Checkin(
            checkin_date="2026-06-01", period="morning",
            checkin_time="08:00:00", checkout_time="12:00:00", status="normal",
        ))
        checkin_repo.upsert(Checkin(
            checkin_date="2026-06-01", period="afternoon",
            checkin_time="13:00:00", checkout_time="18:00:00", status="normal",
        ))

        svc = self.setup_svc(temp_db)
        data = svc.collect_data("2026-06-01")
        assert data.total_work_hours == 9.0
        html = svc.generate_html(data)
        assert "超过 8 小时" in html

    def test_encouragement_in_html(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        data = svc.collect_data("2026-06-01")
        html = svc.generate_html(data)
        assert data.encouragement in html

    def test_pick_encouragement_uses_user_list_when_present(self, temp_db: str) -> None:
        from app.repositories.settings_repo import SettingsRepo

        settings_repo = SettingsRepo(temp_db)
        settings_repo.set("encouragements_user", '["only one"]')
        svc = ReportService(
            CheckinRepo(temp_db),
            LedgerRepo(temp_db),
            ShootingRepo(temp_db),
            settings_repo,
        )
        for _ in range(100):
            assert svc._pick_encouragement("2026-06-01") == "only one"

    def test_pick_encouragement_falls_back_to_builtin_when_user_empty(
        self, temp_db: str
    ) -> None:
        from app.repositories.settings_repo import SettingsRepo
        from app.services.report_service import ENCOURAGEMENTS

        svc = ReportService(
            CheckinRepo(temp_db),
            LedgerRepo(temp_db),
            ShootingRepo(temp_db),
            SettingsRepo(temp_db),
        )
        results = {svc._pick_encouragement("2026-06-01") for _ in range(100)}
        assert results.issubset(set(ENCOURAGEMENTS))
        assert len(results) >= 1
