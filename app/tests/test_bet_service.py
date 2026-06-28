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

    # ── 滞纳期测试 ──

    def test_settle_incomplete_enters_late(self, temp_db: str) -> None:
        """未完成任务结算 → status=late (不再直接 settled)"""
        svc = self.setup_svc(temp_db)
        svc.set_week_config("2026-06-01", 50, 30, 50)
        t = svc.create_task("2026-06-01", "任务1")
        assert t.id is not None
        # 不完成任务直接结算
        result = svc.settle_week("2026-06-01")
        assert result.status == "late"
        assert result.total_penalty == -50
        assert result.total_reward == 0

    def test_settle_from_late_closes_cycle(self, temp_db: str) -> None:
        """从滞纳期结算 → status=settled"""
        svc = self.setup_svc(temp_db)
        svc.set_week_config("2026-06-01", 50, 30, 50, late_fee_per_day=10)
        t = svc.create_task("2026-06-01", "任务1")
        assert t.id is not None
        # 第一次结算 → 进入滞纳期
        result1 = svc.settle_week("2026-06-01")
        assert result1.status == "late"
        # 第二次结算 → 关闭周期
        result2 = svc.settle_week("2026-06-01")
        assert result2.status == "settled"

    def test_late_fee_accrual_idempotent(self, temp_db: str) -> None:
        """滞纳金补扣幂等：同一天多次调用不重复扣费"""
        svc = self.setup_svc(temp_db)
        svc.set_week_config("2026-06-01", 50, 30, 50, late_fee_per_day=10)
        svc.create_task("2026-06-01", "任务1")
        svc.settle_week("2026-06-01")  # → late

        n1 = svc.accrue_late_fees("2026-06-01")
        assert n1 >= 1  # 首次至少创建1条
        n2 = svc.accrue_late_fees("2026-06-01")
        assert n2 == 0  # 第二次调用不新增，幂等

    def test_auto_create_next_cycle(self, temp_db: str) -> None:
        """结算完成后自动创建下一周期"""
        svc = self.setup_svc(temp_db)
        svc.set_week_config("2026-06-01", 50, 30, 50)
        t = svc.create_task("2026-06-01", "任务1")
        assert t.id is not None
        svc.complete_task(t.id)
        svc.settle_week("2026-06-01")  # 全部完成 → settled → 自动创建新周期

        # 验证新周期已创建
        new_start = svc.get_current_cycle_start()
        from datetime import date, timedelta
        expected = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        assert new_start == expected

    def test_can_start_new_week_blocks_unsettled(self, temp_db: str) -> None:
        """未结清周期阻塞新周期"""
        svc = self.setup_svc(temp_db)
        svc.set_week_config("2026-06-01", 50, 30, 50)
        svc.create_task("2026-06-01", "任务1")
        svc.settle_week("2026-06-01")  # → late

        # 当前周自身被排除
        assert svc.can_start_new_week(exclude_week_start="2026-06-01")

    def test_get_current_cycle_prefers_unsettled(self, temp_db: str) -> None:
        """优先返回未结算周期"""
        svc = self.setup_svc(temp_db)
        svc.set_week_config("2026-06-01", 50, 30, 50)
        cycle = svc.get_current_cycle_start()
        assert cycle == "2026-06-01"  # 唯一未结算周期
