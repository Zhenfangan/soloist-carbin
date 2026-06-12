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


class NoOpNotifier(Notifier):
    """桌面端 / 测试占位实现 — 通知栏只在 Android 上有意义"""

    def show_ongoing(self, title: str, content: str) -> None:
        pass

    def send_reminder(self, title: str, content: str) -> None:
        pass

    def cancel_all(self) -> None:
        pass
