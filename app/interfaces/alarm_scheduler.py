"""系统闹钟抽象接口"""

from abc import ABC, abstractmethod


class AlarmScheduler(ABC):
    """系统闹钟抽象接口"""

    @abstractmethod
    def schedule(self, alarm_time: str, tag: str) -> None:
        """设定闹钟"""
        ...

    @abstractmethod
    def cancel(self, tag: str) -> None:
        """取消闹钟"""
        ...

    @abstractmethod
    def cancel_all(self) -> None:
        """取消所有闹钟"""
        ...
