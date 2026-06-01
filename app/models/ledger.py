"""奖惩模块数据模型"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LedgerEntry:
    """账本流水 — 对应 ledger_entries 表"""
    entry_date: str
    type: str
    amount: float
    week_start: str | None = None
    description: str | None = None
    reward_item: str | None = None
    reward_qty: int = 1
    fulfilled: int = 0
    source_id: int | None = None
    id: int | None = None


@dataclass
class BoyfriendPromise:
    """男友承诺 — 对应 boyfriend_promises 表"""
    promise_date: str
    reward_desc: str
    reward_qty: int = 1
    fulfilled: int = 0
    id: int | None = None


@dataclass
class BetTask:
    """对赌任务 — 对应 bet_tasks 表"""
    week_start: str
    task_desc: str
    is_completed: int = 0
    is_extra: int = 0
    id: int | None = None


@dataclass
class BetConfig:
    """对赌配置 — 对应 bet_configs 表"""
    week_start: str
    base_reward: float
    extra_reward: float
    penalty: float
    status: str = "active"
    id: int | None = None


@dataclass
class WeeklySettlementResult:
    """周结算结果"""
    week_start: str
    tasks: list[BetTask]
    completed_count: int
    extra_count: int
    total_reward: float
    total_penalty: float
    net: float
    ledger_entries: list[LedgerEntry]
