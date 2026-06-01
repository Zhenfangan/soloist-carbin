"""BetService 对赌任务测试"""

from __future__ import annotations

from app.repositories.bet_repo import BetRepo
from app.repositories.ledger_repo import LedgerRepo
from app.repositories.settings_repo import SettingsRepo
from app.services.bet_service import BetService


class TestBetService:
    def setup_svc(self, temp_db: str) -> BetService:
        return BetService(BetRepo(temp_db), LedgerRepo(temp_db), SettingsRepo(temp_db))

    def test_create_and_complete_task(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        task = svc.create_task("2026-06-01", "写三篇文章")
        assert task.id is not None
        assert task.task_desc == "写三篇文章"

        completed = svc.complete_task(task.id)
        assert completed is not None
        assert completed.is_completed == 1

    def test_settle_week_all_completed(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        svc.set_week_config("2026-06-01", 50, 30, 50)
        t1 = svc.create_task("2026-06-01", "任务1")
        t2 = svc.create_task("2026-06-01", "任务2")
        t3 = svc.create_task("2026-06-01", "任务3")
        assert t1.id is not None
        assert t2.id is not None
        assert t3.id is not None
        svc.complete_task(t1.id)
        svc.complete_task(t2.id)
        svc.complete_task(t3.id)

        result = svc.settle_week("2026-06-01")
        assert result.completed_count == 3
        assert result.total_reward == 50
        assert result.total_penalty == 0

    def test_settle_week_not_completed(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        svc.set_week_config("2026-06-01", 50, 30, 50)
        t1 = svc.create_task("2026-06-01", "任务1")
        assert t1.id is not None
        svc.complete_task(t1.id)
        svc.create_task("2026-06-01", "任务2")
        svc.create_task("2026-06-01", "任务3")

        result = svc.settle_week("2026-06-01")
        assert result.completed_count == 1
        assert result.total_penalty == -50

    def test_settle_week_no_config_uses_defaults(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        t1 = svc.create_task("2026-06-01", "任务1")
        assert t1.id is not None
        svc.complete_task(t1.id)

        result = svc.settle_week("2026-06-01")
        assert result.total_reward == 50

    def test_delete_task(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        t = svc.create_task("2026-06-01", "删除测试")
        assert t.id is not None
        svc.delete_task(t.id)
        tasks = svc.get_week_tasks("2026-06-01")
        assert len(tasks) == 0

    def test_week_summary(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        svc.create_task("2026-06-01", "任务1")
        svc.create_task("2026-06-01", "任务2")
        summary = svc.get_week_summary("2026-06-01")
        assert summary["total_tasks"] == 2
        assert summary["completed"] == 0
