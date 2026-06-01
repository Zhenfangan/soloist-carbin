"""Android 通知抽象接口"""

from abc import ABC, abstractmethod


class Notifier(ABC):
    """Android 通知抽象接口"""

    @abstractmethod
    def show_ongoing(self, title: str, content: str) -> None:
        """显示常驻通知（不可划掉）"""
        ...

    @abstractmethod
    def send_reminder(self, title: str, content: str) -> None:
        """发送普通提醒通知"""
        ...

    @abstractmethod
    def cancel_all(self) -> None:
        """取消所有通知"""
        ...
