"""对赌任务服务"""

from __future__ import annotations

from app.models.ledger import (
    BetConfig,
    BetTask,
    LedgerEntry,
    WeeklySettlementResult,
)
from app.repositories.bet_repo import BetRepo
from app.repositories.ledger_repo import LedgerRepo
from app.repositories.settings_repo import SettingsRepo
from app.services.event_bus import EventType, get_event_bus
from app.utils.config import (
    LEDGER_TYPE_BET_EXTRA,
    LEDGER_TYPE_BET_PENALTY,
    LEDGER_TYPE_BET_REWARD,
)


class BetService:
    """对赌任务 + 结算"""

    def __init__(
        self,
        bet_repo: BetRepo,
        ledger_repo: LedgerRepo,
        settings_repo: SettingsRepo,
    ) -> None:
        self._bet_repo = bet_repo
        self._ledger_repo = ledger_repo
        self._settings_repo = settings_repo

        get_event_bus().subscribe(EventType.WEEK_CLOSED, self._on_week_closed)

    # ── 任务管理 ──

    def create_task(self, week_start: str, task_desc: str, target_qty: int = 1) -> BetTask:
        task = BetTask(week_start=week_start, task_desc=task_desc, target_qty=target_qty)
        return self._bet_repo.create_task(task)

    def complete_task(self, task_id: int) -> BetTask | None:
        return self._bet_repo.complete_task(task_id)

    def update_task_progress(self, task_id: int, current_qty: int) -> BetTask | None:
        """更新任务进度，自动判断是否完成。"""
        return self._bet_repo.update_task_progress(task_id, current_qty)

    def delete_task(self, task_id: int) -> None:
        self._bet_repo.delete_task(task_id)

    def set_week_config(
        self, week_start: str, base_reward: float, extra_reward: float, penalty: float
    ) -> BetConfig:
        config = BetConfig(
            week_start=week_start,
            base_reward=base_reward,
            extra_reward=extra_reward,
            penalty=penalty,
        )
        return self._bet_repo.upsert_config(config)

    def get_week_tasks(self, week_start: str) -> list[BetTask]:
        return self._bet_repo.get_tasks_by_week(week_start)

    # ── 结算 ──

    def settle_week(self, week_start: str) -> WeeklySettlementResult:
        """周结算：完成→奖励 / 超额→额外 / 未完成→惩罚"""
        tasks = self._bet_repo.get_tasks_by_week(week_start)
        config = self._bet_repo.get_config(week_start)

        base_reward = config.base_reward if config else float(self._get_setting("bet_base_reward"))
        extra_reward = config.extra_reward if config else float(self._get_setting("bet_extra_reward"))
        penalty_amt = config.penalty if config else float(self._get_setting("bet_penalty"))

        completed = [t for t in tasks if t.is_completed]
        uncompleted = [t for t in tasks if not t.is_completed]
        extra_tasks = [t for t in tasks if t.is_extra and t.is_completed]

        entries: list[LedgerEntry] = []
        settlement_date = self._week_end_date(week_start)

        if len(uncompleted) == 0:
            # 全部完成 → 基础奖励
            entries.append(
                LedgerEntry(
                    entry_date=settlement_date,
                    week_start=week_start,
                    type=LEDGER_TYPE_BET_REWARD,
                    amount=base_reward,
                    description="对赌任务全部完成奖励",
                )
            )
            # 超额奖励
            if len(extra_tasks) > 0:
                entries.append(
                    LedgerEntry(
                        entry_date=settlement_date,
                        week_start=week_start,
                        type=LEDGER_TYPE_BET_EXTRA,
                        amount=extra_reward * len(extra_tasks),
                        description=f"超额任务奖励 ×{len(extra_tasks)}",
                    )
                )
        else:
            # 有未完成 → 惩罚
            entries.append(
                LedgerEntry(
                    entry_date=settlement_date,
                    week_start=week_start,
                    type=LEDGER_TYPE_BET_PENALTY,
                    amount=-penalty_amt,
                    description=f"对赌任务未完成 ({len(uncompleted)}项)",
                )
            )

        total_reward = sum(e.amount for e in entries if e.amount > 0)
        total_penalty = sum(e.amount for e in entries if e.amount < 0)
        net = total_reward + total_penalty

        for entry in entries:
            self._ledger_repo.insert(entry)

        # Mark config as settled
        if config:
            config.status = "settled"
            self._bet_repo.upsert_config(config)

        result = WeeklySettlementResult(
            week_start=week_start,
            tasks=tasks,
            completed_count=len(completed),
            extra_count=len(extra_tasks),
            total_reward=total_reward,
            total_penalty=total_penalty,
            net=net,
            ledger_entries=entries,
        )

        get_event_bus().publish(EventType.BET_SETTLED, {"week_start": week_start})
        get_event_bus().publish(EventType.WEEK_SETTLED, {"week_start": week_start})

        return result

    def get_week_summary(self, week_start: str) -> dict[str, object]:
        tasks = self._bet_repo.get_tasks_by_week(week_start)
        config = self._bet_repo.get_config(week_start)
        completed = sum(1 for t in tasks if t.is_completed)
        extra_count = sum(1 for t in tasks if t.is_extra and t.is_completed)
        total_tasks = len(tasks)
        completion_rate = (completed / total_tasks * 100) if total_tasks > 0 else 0.0

        base_reward = config.base_reward if config else float(self._get_setting("bet_base_reward"))
        extra_reward = config.extra_reward if config else float(self._get_setting("bet_extra_reward"))
        penalty_amt = config.penalty if config else float(self._get_setting("bet_penalty"))

        uncompleted = total_tasks - completed
        total_reward_estimate = 0.0
        if uncompleted == 0 and completed > 0:
            total_reward_estimate = base_reward + extra_reward * extra_count
        elif uncompleted > 0:
            total_reward_estimate = -penalty_amt

        return {
            "week_start": week_start,
            "total_tasks": total_tasks,
            "completed": completed,
            "completed_count": completed,
            "extra_count": extra_count,
            "completion_rate": completion_rate,
            "total_reward": total_reward_estimate,
            "config": config,
        }

    def _get_setting(self, key: str) -> str:
        val = self._settings_repo.get(key)
        if val is not None:
            return val
        from app.services.settings_service import SettingsService
        return SettingsService.DEFAULTS.get(key, "")

    def _week_end_date(self, week_start: str) -> str:
        from datetime import datetime, timedelta
        dt = datetime.strptime(week_start, "%Y-%m-%d")
        return (dt + timedelta(days=6)).strftime("%Y-%m-%d")

    def _on_week_closed(self, event_type: EventType, payload: dict[str, object]) -> None:
        week_start = str(payload.get("week_start", ""))
        if week_start:
            self.settle_week(week_start)
