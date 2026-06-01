"""BoyfriendPromiseService 男友承诺测试"""

from __future__ import annotations

from app.repositories.ledger_repo import LedgerRepo
from app.repositories.settings_repo import SettingsRepo
from app.services.boyfriend_promise_service import BoyfriendPromiseService


class TestBoyfriendPromiseService:
    def setup_svc(self, temp_db: str) -> BoyfriendPromiseService:
        return BoyfriendPromiseService(LedgerRepo(temp_db), SettingsRepo(temp_db))

    def test_set_promise(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        promise = svc.set_promise("2026-06-01", "一杯奶茶")
        assert promise.id is not None
        assert promise.reward_desc == "一杯奶茶"

    def test_check_fulfill_meets_threshold(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        svc.set_promise("2026-06-01", "一杯奶茶")
        result = svc.check_fulfill("2026-06-01", 8.5)
        assert result is True

    def test_check_fulfill_below_threshold(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        svc.set_promise("2026-06-01", "一杯奶茶")
        result = svc.check_fulfill("2026-06-01", 6.0)
        assert result is False

    def test_check_fulfill_no_promise(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        result = svc.check_fulfill("2026-06-01", 10.0)
        assert result is False

    def test_get_today_promise(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        svc.set_promise("2026-06-01", "一顿火锅", 1)
        p = svc.get_today_promise("2026-06-01")
        assert p is not None
        assert p.reward_desc == "一顿火锅"
