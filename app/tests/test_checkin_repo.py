"""CheckinRepo 数据访问层测试"""

from __future__ import annotations

from app.models.checkin import Checkin
from app.repositories.checkin_repo import CheckinRepo


class TestCheckinRepo:
    def test_upsert_creates_new(self, temp_db: str) -> None:
        repo = CheckinRepo(temp_db)
        record = Checkin(checkin_date="2026-06-01", period="morning", checkin_time="08:55")
        saved = repo.upsert(record)
        assert saved.id is not None
        assert saved.checkin_date == "2026-06-01"
        assert saved.checkin_time == "08:55"

    def test_upsert_updates_existing(self, temp_db: str) -> None:
        repo = CheckinRepo(temp_db)
        r1 = repo.upsert(Checkin(checkin_date="2026-06-01", period="morning", checkin_time="08:55"))
        r2 = repo.upsert(Checkin(checkin_date="2026-06-01", period="morning", checkout_time="12:00", status="normal"))
        assert r2.id == r1.id
        assert r2.checkout_time == "12:00"
        assert r2.status == "normal"

    def test_get_by_date_period_found(self, temp_db: str) -> None:
        repo = CheckinRepo(temp_db)
        repo.upsert(Checkin(checkin_date="2026-06-01", period="morning", checkin_time="08:55"))
        result = repo.get_by_date_period("2026-06-01", "morning")
        assert result is not None
        assert result.checkin_time == "08:55"

    def test_get_by_date_period_not_found(self, temp_db: str) -> None:
        repo = CheckinRepo(temp_db)
        assert repo.get_by_date_period("2026-06-01", "morning") is None

    def test_get_all_by_date(self, temp_db: str) -> None:
        repo = CheckinRepo(temp_db)
        repo.upsert(Checkin(checkin_date="2026-06-01", period="morning", checkin_time="09:00"))
        repo.upsert(Checkin(checkin_date="2026-06-01", period="afternoon", checkin_time="14:00"))
        results = repo.get_all_by_date("2026-06-01")
        assert len(results) == 2

    def test_get_all_by_week(self, temp_db: str) -> None:
        repo = CheckinRepo(temp_db)
        repo.upsert(Checkin(checkin_date="2026-06-01", period="morning", checkin_time="09:00"))
        repo.upsert(Checkin(checkin_date="2026-06-03", period="morning", checkin_time="09:00"))
        repo.upsert(Checkin(checkin_date="2026-06-08", period="morning", checkin_time="09:00"))
        results = repo.get_all_by_week("2026-06-01")
        assert len(results) == 2  # only 6/1 and 6/3

    def test_get_all_by_month(self, temp_db: str) -> None:
        repo = CheckinRepo(temp_db)
        repo.upsert(Checkin(checkin_date="2026-06-01", period="morning", checkin_time="09:00"))
        repo.upsert(Checkin(checkin_date="2026-06-15", period="morning", checkin_time="09:00"))
        repo.upsert(Checkin(checkin_date="2026-07-01", period="morning", checkin_time="09:00"))
        results = repo.get_all_by_month(2026, 6)
        assert len(results) == 2

    def test_get_unchecked_out(self, temp_db: str) -> None:
        repo = CheckinRepo(temp_db)
        repo.upsert(Checkin(checkin_date="2026-06-01", period="morning", checkin_time="09:00"))
        repo.upsert(Checkin(checkin_date="2026-06-01", period="afternoon", checkin_time="14:00", checkout_time="18:00"))
        results = repo.get_unchecked_out("2026-06-01")
        assert len(results) == 1
        assert results[0].period == "morning"
