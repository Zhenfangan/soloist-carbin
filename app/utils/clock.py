"""时间抽象层 — 统一时间源，支持生产/测试切换。

所有模块通过 get_clock() 获取当前时间，禁止直接调用 datetime.now()。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta


class Clock(ABC):
    """时间源抽象接口"""

    @abstractmethod
    def now(self) -> datetime:
        """返回当前时间"""
        ...

    @abstractmethod
    def today_str(self) -> str:
        """返回今天日期 YYYY-MM-DD"""
        ...

    @abstractmethod
    def current_time_str(self) -> str:
        """返回当前时间 HH:MM:SS"""
        ...


class SystemClock(Clock):
    """生产环境：封装系统真实时间"""

    def now(self) -> datetime:
        return datetime.now()

    def today_str(self) -> str:
        return self.now().strftime("%Y-%m-%d")

    def current_time_str(self) -> str:
        return self.now().strftime("%H:%M:%S")


RealClock = SystemClock  # 便捷别名，供应用层使用


class SimulatedClock(Clock):
    """测试环境：可手动控制的时间"""

    def __init__(self, start_time: datetime | None = None) -> None:
        self._time = start_time or datetime(2026, 1, 1, 8, 0, 0)
        self._speed: float = 1.0
        self._paused: bool = False

    def now(self) -> datetime:
        return self._time

    def today_str(self) -> str:
        return self._time.strftime("%Y-%m-%d")

    def current_time_str(self) -> str:
        return self._time.strftime("%H:%M:%S")

    def set_time(self, dt: datetime) -> None:
        """设为指定时间"""
        self._time = dt

    def set_date_and_time(self, date_str: str, time_str: str) -> None:
        """快捷设时间 set_date_and_time('2026-06-01', '08:55')"""
        if time_str.count(":") == 1:
            time_str += ":00"
        self._time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")

    def advance(self, **kwargs: int) -> None:
        """快进时间 advance(minutes=30) 或 advance(hours=2, minutes=15)"""
        self._time += timedelta(**kwargs)

    def advance_days(self, days: int) -> None:
        """快进指定天数"""
        self._time += timedelta(days=days)

    def set_speed(self, multiplier: float) -> None:
        """设置时间倍速 60 = 1 分钟过 1 小时"""
        self._speed = multiplier

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def is_paused(self) -> bool:
        return self._paused


# 全局时钟实例
_clock: Clock | None = None


def get_clock() -> Clock:
    """全局时钟获取器。未注入时默认使用 SystemClock。"""
    global _clock
    if _clock is None:
        _clock = SystemClock()
    return _clock


def set_clock(clock: Clock) -> None:
    """注入时钟实例（测试时使用）"""
    global _clock
    _clock = clock
