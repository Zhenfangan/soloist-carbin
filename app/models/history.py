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


@dataclass
class YearViewData:
    """年视图数据"""
    year: int
    months: list[MonthSummary] = field(default_factory=list)
