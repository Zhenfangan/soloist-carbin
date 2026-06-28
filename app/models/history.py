"""历史模块数据模型"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.ledger import LedgerEntry


@dataclass
class PeriodSummary:
    """时段摘要"""
    period: str
    status: str
    checkin_time: str | None = None
    checkout_time: str | None = None


@dataclass
class DayCard:
    """日卡片"""
    date: str
    periods: list[PeriodSummary] = field(default_factory=list)
    total_hours: float = 0.0
    daily_ledger: list[LedgerEntry] = field(default_factory=list)
    is_shooting: bool = False


@dataclass
class WeekViewData:
    """周视图数据"""
    week_start: str
    week_end: str
    days: list[DayCard] = field(default_factory=list)
    weekly_net: float = 0.0


@dataclass
class CalendarCell:
    """日历格子"""
    date: str
    color: str  # green / yellow / red / blue / orange / empty
    has_data: bool = False


@dataclass
class MonthViewData:
    """月视图数据"""
    year: int
    month: int
    cells: list[CalendarCell] = field(default_factory=list)
    weekly_summaries: list[dict[str, object]] = field(default_factory=list)


@dataclass
class MonthSummary:
    """月度汇总"""
    month: int
    work_days: int = 0
    late_count: int = 0
    absent_count: int = 0
    total_hours: float = 0.0
    total_ledger: float = 0.0
    bet_cycles: int = 0        # 本月涉及的对赌周期数
    bet_net: float = 0.0       # 本月对赌净额


@dataclass
class YearViewData:
    """年视图数据"""
    year: int
    months: list[MonthSummary] = field(default_factory=list)


@dataclass
class CycleSummary:
    """对赌周期汇总 — 用于周期历史视图"""
    week_start: str        # 周期起点
    week_end: str          # 结算日 (week_start + 6)
    status: str            # "settled" / "late"
    total_tasks: int = 0
    completed_tasks: int = 0
    base_reward: float = 0.0
    extra_reward: float = 0.0
    penalty: float = 0.0
    late_fees: float = 0.0
    late_days: int = 0
    net: float = 0.0
    actual_end_date: str | None = None  # 实际结算日期 (late 时为 late_start_date)
