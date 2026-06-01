"""SyncService 同步服务测试"""

from __future__ import annotations

from app.repositories.sync_repo import SyncRepo
from app.services.sync_service import SyncService


class TestSyncService:
    def setup_svc(self, temp_db: str) -> SyncService:
        return SyncService(SyncRepo(temp_db))

    def test_connect_and_disconnect(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        assert svc.connect() is True
        assert svc.is_connected() is True
        svc.disconnect()
        assert svc.is_connected() is False

    def test_push_event_when_connected(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        svc.connect()
        from app.services.event_bus import EventType
        results: list[object] = []

        svc.set_on_message(lambda msg: results.append(msg))
        svc.push_event(EventType.CHECK_IN_COMPLETED, {"date": "2026-06-01"})
        assert len(results) == 1

    def test_push_event_cached_when_disconnected(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        from app.services.event_bus import EventType
        svc.push_event(EventType.CHECK_IN_COMPLETED, {"date": "2026-06-01"})
        svc.push_event(EventType.CHECK_OUT_COMPLETED, {"date": "2026-06-01"})

        results: list[object] = []
        svc.set_on_message(lambda msg: results.append(msg))
        count = svc.flush_cache()
        assert count == 2
        assert len(results) == 2

    def test_backup_and_restore(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        from app.models.checkin import Checkin
        from app.repositories.checkin_repo import CheckinRepo
        cr = CheckinRepo(temp_db)
        cr.upsert(Checkin(checkin_date="2026-06-01", period="morning", checkin_time="09:00", status="normal"))

        backup = svc.backup_full()
        assert backup["backed_up"] is True
        data = backup.get("data")
        assert isinstance(data, dict)
        assert svc.restore_full(data) is True
