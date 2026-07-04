"""对赌任务服务"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from app.utils.clock import get_clock
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
    LEDGER_TYPE_BET_LATE_FEE,
    LEDGER_TYPE_BET_PENALTY,
    LEDGER_TYPE_BET_REWARD,
    LEDGER_TYPE_SHOOTING_REWARD,
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

    # ── 任务管理 ──

    def create_task(self, week_start: str, task_desc: str, target_qty: int = 1) -> BetTask:
        task = BetTask(week_start=week_start, task_desc=task_desc, target_qty=target_qty)
        return self._bet_repo.create_task(task)

    def complete_task(self, task_id: int) -> BetTask | None:
        return self._bet_repo.complete_task(task_id)

    def update_task_progress(self, task_id: int, delta: int) -> BetTask | None:
        """原子递增/递减任务进度 — delta 是增量 (+N 加, -N 减), 自动维护 is_completed。"""
        return self._bet_repo.update_task_progress(task_id, delta)

    def update_task(
        self, task_id: int, task_desc: str, target_qty: int
    ) -> BetTask | None:
        """编辑任务描述和目标数量。"""
        return self._bet_repo.update_task(task_id, task_desc, target_qty)

    def delete_task(self, task_id: int) -> None:
        self._bet_repo.delete_task(task_id)

    def set_week_config(
        self, week_start: str, base_reward: float, extra_reward: float,
        penalty: float, late_fee_per_day: float = 10.0,
    ) -> BetConfig:
        config = BetConfig(
            week_start=week_start,
            base_reward=base_reward,
            extra_reward=extra_reward,
            penalty=penalty,
            late_fee_per_day=late_fee_per_day,
        )
        return self._bet_repo.upsert_config(config)

    def get_week_tasks(self, week_start: str) -> list[BetTask]:
        return self._bet_repo.get_tasks_by_week(week_start)

    # ── 结算 ──

    def settle_week(self, week_start: str) -> WeeklySettlementResult:
        """周结算：
        active + 全部完成 → 发放奖励 → settled
        active + 有未完成 → 扣除罚金 → late（进入滞纳期）
        late             → 关闭周期 → settled（不再扣罚金/奖励）
        """
        config = self._bet_repo.get_config(week_start)

        # 已结算 → 幂等返回空结果
        if config and config.status == "settled":
            tasks = self._bet_repo.get_tasks_by_week(week_start)
            return WeeklySettlementResult(
                week_start=week_start,
                tasks=tasks,
                completed_count=sum(1 for t in tasks if t.is_completed),
                extra_count=sum(1 for t in tasks if t.is_extra and t.is_completed),
                total_reward=0.0,
                total_penalty=0.0,
                net=0.0,
                ledger_entries=[],
                status="settled",
                late_fee_total=0.0,
            )

        tasks = self._bet_repo.get_tasks_by_week(week_start)
        completed = [t for t in tasks if t.is_completed]
        uncompleted = [t for t in tasks if not t.is_completed]

        # 超额单位数
        extra_units = sum(
            max(0, t.current_qty - t.target_qty) for t in completed
        )

        # 读取配置（带默认值回退）
        base_reward = config.base_reward if config else float(self._get_setting("bet_base_reward"))
        extra_reward = config.extra_reward if config else float(self._get_setting("bet_extra_reward"))
        penalty_amt = config.penalty if config else float(self._get_setting("bet_penalty"))

        entries: list[LedgerEntry] = []
        settlement_date = self._week_end_date(week_start)
        today_str = get_clock().now().date().strftime("%Y-%m-%d")
        today_dt = get_clock().now().date()
        week_end_dt = datetime.strptime(settlement_date, "%Y-%m-%d").date()
        is_past_deadline = today_dt > week_end_dt  # 只有周一之后才算超时
        late_fee_total = 0.0

        if config and config.status == "late":
            # ── 滞纳期结算：关闭周期，不再加罚金/奖励 ──
            self.accrue_late_fees(week_start)
            late_fee_total = self._calc_accrued_late_fees(week_start)
            new_status = "settled"

        elif len(uncompleted) == 0:
            # ── 全部完成 → 基础奖励 + 超额奖励 ──
            entries.append(
                LedgerEntry(
                    entry_date=settlement_date,
                    week_start=week_start,
                    type=LEDGER_TYPE_BET_REWARD,
                    amount=base_reward,
                    description="对赌任务全部完成奖励",
                )
            )
            if extra_units > 0:
                entries.append(
                    LedgerEntry(
                        entry_date=settlement_date,
                        week_start=week_start,
                        type=LEDGER_TYPE_BET_EXTRA,
                        amount=extra_reward * extra_units,
                        description=f"超额任务奖励 ×{extra_units}",
                    )
                )
            new_status = "settled"

        elif is_past_deadline:
            # ── 已超时 + 有未完成 → 罚金 + 进入滞纳期 ──
            entries.append(
                LedgerEntry(
                    entry_date=settlement_date,
                    week_start=week_start,
                    type=LEDGER_TYPE_BET_PENALTY,
                    amount=-penalty_amt,
                    description=f"对赌任务未完成 ({len(uncompleted)}项)",
                )
            )
            new_status = "late"

        else:
            # ── 期限未到（周日当天）→ 拒绝结算，返回未结算提示 ──
            raise ValueError("期限未过，请在完成所有任务后结算，或等周一再进入滞纳期")

        total_reward = sum(e.amount for e in entries if e.amount > 0)
        total_penalty = sum(e.amount for e in entries if e.amount < 0)
        net = total_reward + total_penalty - late_fee_total

        with self._bet_repo.transaction():
            for entry in entries:
                self._ledger_repo.insert(entry)

            if config:
                config.status = new_status
                if new_status == "late":
                    config.late_start_date = today_str
                self._bet_repo.upsert_config(config)
            elif new_status == "settled":
                # 无 config 时自动创建一条 settled 记录
                new_cfg = BetConfig(
                    week_start=week_start,
                    base_reward=base_reward,
                    extra_reward=extra_reward,
                    penalty=penalty_amt,
                    status="settled",
                )
                self._bet_repo.upsert_config(new_cfg)

            # 结算完成 → 自动创建下一周期 (结算后最近的 24:00 为新周期起点)
            if new_status == "settled":
                self._auto_create_next_cycle(base_reward, extra_reward, penalty_amt)

        result = WeeklySettlementResult(
            week_start=week_start,
            tasks=tasks,
            completed_count=len(completed),
            extra_count=extra_units,
            total_reward=total_reward,
            total_penalty=total_penalty,
            net=net,
            ledger_entries=entries,
            status=new_status,
            late_fee_total=late_fee_total,
        )

        get_event_bus().publish(EventType.BET_SETTLED, {"week_start": week_start})
        if new_status == "late":
            get_event_bus().publish(EventType.BET_LATE_STARTED, {"week_start": week_start})
        else:
            get_event_bus().publish(EventType.WEEK_SETTLED, {"week_start": week_start})

        return result

    def get_week_summary(self, week_start: str) -> dict[str, object]:
        tasks = self._bet_repo.get_tasks_by_week(week_start)
        config = self._bet_repo.get_config(week_start)
        completed = sum(1 for t in tasks if t.is_completed)
        total_tasks = len(tasks)

        # 按实际数量计算完成率（如 2/1 → 200%）
        total_target = sum(t.target_qty for t in tasks)
        total_current = sum(t.current_qty for t in tasks)
        completion_rate = (total_current / total_target * 100) if total_target > 0 else 0.0

        # 超额单位数
        extra_units = sum(
            max(0, t.current_qty - t.target_qty) for t in tasks if t.is_completed
        )

        base_reward = config.base_reward if config else float(self._get_setting("bet_base_reward"))
        extra_reward = config.extra_reward if config else float(self._get_setting("bet_extra_reward"))
        penalty_amt = config.penalty if config else float(self._get_setting("bet_penalty"))

        uncompleted = total_tasks - completed
        total_reward_estimate = 0.0
        if config and config.status == "settled":
            total_reward_estimate = 0.0
        elif config and config.status == "late":
            # 滞纳中：显示已累积滞纳金（负值）
            accrued = self._calc_accrued_late_fees(week_start)
            total_reward_estimate = -(penalty_amt + accrued)
        elif uncompleted == 0 and completed > 0:
            total_reward_estimate = base_reward + extra_reward * extra_units
        elif uncompleted > 0:
            total_reward_estimate = -penalty_amt

        result: dict[str, object] = {
            "week_start": week_start,
            "total_tasks": total_tasks,
            "completed": completed,
            "completed_count": completed,
            "extra_count": extra_units,
            "completion_rate": completion_rate,
            "total_reward": total_reward_estimate,
            "config": config,
            "status": config.status if config else "active",
            "late_start_date": config.late_start_date if config else None,
            "late_fee_per_day": config.late_fee_per_day if config else 10.0,
            "accrued_late_fees": self._calc_accrued_late_fees(week_start) if (config and config.status == "late") else 0.0,
        }
        return result

    def get_other_income(self, week_start: str) -> float:
        """本周"其他收入"(如拍摄奖励) —— 独立于赌约任务结算之外的账本收入汇总。"""
        entries = self._ledger_repo.get_by_week(week_start)
        return sum(e.amount for e in entries if e.type == LEDGER_TYPE_SHOOTING_REWARD)

    def _get_setting(self, key: str) -> str:
        val = self._settings_repo.get(key)
        if val is not None:
            return val
        from app.services.settings_service import SettingsService
        return SettingsService.DEFAULTS.get(key, "")

    def _week_end_date(self, week_start: str) -> str:
        dt = datetime.strptime(week_start, "%Y-%m-%d")
        return (dt + timedelta(days=6)).strftime("%Y-%m-%d")

    # ── 滞纳期 ──

    def check_and_enter_late(self, week_start: str) -> bool:
        """检测超时未完成 → 自动进入滞纳期。

        条件: config.status == 'active' 且 今天 >= 周日 且 有未完成任务。
        返回是否发生了状态转换。
        """
        config = self._bet_repo.get_config(week_start)
        if not config or config.status != "active":
            return False

        today_str = get_clock().now().date().strftime("%Y-%m-%d")
        sunday = self._week_end_date(week_start)
        if today_str < sunday:
            return False

        tasks = self._bet_repo.get_tasks_by_week(week_start)
        uncompleted = [t for t in tasks if not t.is_completed]
        if len(uncompleted) == 0:
            return False

        # 有未完成任务且已到/过周日 → 暂不自动进入（等待用户手动触发结算）
        return False

    def accrue_late_fees(self, week_start: str) -> int:
        """对滞纳期周补扣每日滞纳金（去重、幂等）。

        从 late_start_date 到 today，对每一天未扣费的日期
        创建 bet_late_fee 账本流水。

        返回: 本次新增的滞纳金笔数。
        """
        config = self._bet_repo.get_config(week_start)
        if not config or config.status != "late" or not config.late_start_date:
            return 0

        late_fee_per_day = config.late_fee_per_day if config.late_fee_per_day > 0 else float(
            self._get_setting("bet_late_fee_per_day")
        )
        if late_fee_per_day <= 0:
            return 0

        today_str = get_clock().now().date().strftime("%Y-%m-%d")
        already_charged = self._bet_repo.get_late_fee_dates(week_start)
        created = 0

        start_dt = datetime.strptime(config.late_start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(today_str, "%Y-%m-%d")

        with self._bet_repo.transaction():
            current = start_dt
            while current <= end_dt:
                fee_date = current.strftime("%Y-%m-%d")
                if fee_date not in already_charged:
                    self._ledger_repo.insert(
                        LedgerEntry(
                            entry_date=fee_date,
                            week_start=week_start,
                            type=LEDGER_TYPE_BET_LATE_FEE,
                            amount=-late_fee_per_day,
                            description=f"滞纳金 ({fee_date})",
                        )
                    )
                    created += 1
                current += timedelta(days=1)

        return created

    def run_auto_checks(self) -> list[str]:
        """启动时遍历所有未结算周，自动补扣滞纳金。

        注意: 不会自动触发 active→late 转换（由用户手动结算触发）。
        只对已处于 late 状态的周补扣滞纳金。

        返回: 有变更的 week_start 列表。
        """
        changed: list[str] = []
        for cfg in self._bet_repo.get_unsettled_weeks():
            ws = cfg.week_start
            if cfg.status == "late":
                n = self.accrue_late_fees(ws)
                if n > 0:
                    changed.append(ws)
        return changed

    def _auto_create_next_cycle(
        self, base_reward: float, extra_reward: float, penalty_amt: float,
    ) -> None:
        """结算完成后自动创建下一周期配置。

        新周期起点 = 结算日之后最近的 24:00（即明天 00:00）。
        自然周期为一周 7 天，结算日为 week_start + 6 天。
        保留上一周期的赏罚/滞纳金配置。
        """
        tomorrow = (get_clock().now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
        existing = self._bet_repo.get_config(tomorrow)
        if existing:
            return  # 已存在，幂等跳过

        late_fee = float(self._get_setting("bet_late_fee_per_day"))
        new_cfg = BetConfig(
            week_start=tomorrow,
            base_reward=base_reward,
            extra_reward=extra_reward,
            penalty=penalty_amt,
            status="active",
            late_fee_per_day=late_fee,
        )
        self._bet_repo.upsert_config(new_cfg)

    def get_current_cycle_start(self) -> str:
        """获取当前应展示的周期起点。

        优先返回未结算周期 (active/late) 的 week_start；
        若全部已结算，则以上次结算后最近的 24:00 为新周期起点，
        或回退到本周周一。
        """
        unsettled = self._bet_repo.get_unsettled_weeks()
        if unsettled:
            return unsettled[0].week_start

        # 无活跃周期 → 使用今天之后的最近一个周一（兼容首次使用）
        today = get_clock().now().date()
        monday = today - timedelta(days=today.weekday())
        return monday.strftime("%Y-%m-%d")

    def can_start_new_week(self, exclude_week_start: str | None = None) -> bool:
        """检查是否可以开始新一周的对赌。

        存在旧周期未结清（status IN ('active', 'late')）时返回 False。
        exclude_week_start 用于排除当前周自身。
        """
        unsettled = self._bet_repo.get_unsettled_weeks()
        if exclude_week_start:
            unsettled = [c for c in unsettled if c.week_start != exclude_week_start]
        return len(unsettled) == 0

    def _calc_accrued_late_fees(self, week_start: str) -> float:
        """计算某周已累积的滞纳金总额（正值）。"""
        rows = self._bet_repo.conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM ledger_entries"
            " WHERE week_start = ? AND type = ?",
            (week_start, LEDGER_TYPE_BET_LATE_FEE),
        ).fetchone()
        total = rows[0] if rows else 0
        return abs(total)
