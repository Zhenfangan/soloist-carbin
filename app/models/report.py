"""战报模块数据模型"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PeriodDetail:
    """单个时段的战报详情"""
    period: str
    checkin_time: str | None = None
    checkout_time: str | None = None
    status: str = "pending"
    status_label: str = "待判定"


@dataclass
class PromiseDetail:
    """男友承诺详情"""
    reward_desc: str
    reward_qty: int = 1
    fulfilled: bool = False


@dataclass
class ReportData:
    """每日战报完整数据"""
    date: str
    is_shooting_day: bool = False
    periods: list[PeriodDetail] = field(default_factory=list)
    penalty_total: float = 0.0
    reward_total: float = 0.0
    net_amount: float = 0.0
    total_work_hours: float = 0.0
    overtime_hours: float = 0.0
    promise: PromiseDetail | None = None
    completed_tasks: list[str] = field(default_factory=list)
    encouragement: str = ""
    threshold_hours: float = 8.0
    # 拍摄日复盘（仅拍摄日填充）
    shooting_content: str = ""
    shooting_location: str = ""
    shooting_reflection: str = ""
