"""打卡记录数据模型"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Checkin:
    """打卡记录 — 对应 checkins 表"""

    checkin_date: str
    period: str  # morning / afternoon / night
    checkin_time: str | None = None
    checkout_time: str | None = None
    checkout_type: str = "manual"  # manual / auto
    status: str = "pending"
    is_shooting: int = 0
    photo_path: str | None = None
    id: int | None = None


@dataclass
class CheckinResult:
    """打卡操作的结果"""

    date: str
    period: str
    checkin_time: str | None = None
    checkout_time: str | None = None
    checkout_type: str = "manual"
    status: str = "pending"
    status_label: str = "待判定"


@dataclass
class DayStatus:
    """单日出勤状态快照"""

    date: str
    periods: list[PeriodStatus] = field(default_factory=list)
    is_shooting_day: bool = False


@dataclass
class PeriodStatus:
    """单个时段的出勤状态"""

    period: str
    status: str  # pending / normal / late / early_leave / absent / leave / shooting
    checkin_time: str | None = None
    checkout_time: str | None = None
    checkout_type: str = "manual"
    penalty_amount: float | None = None
