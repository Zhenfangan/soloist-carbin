"""事件总线 — 模块间松耦合通信。

模块 A 触发模块 B 的行为时，通过 EventBus 发布事件，
模块 B 订阅相关事件类型，不直接跨模块调用 Service。
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Any


class EventType(Enum):
    """事件类型枚举"""

    CHECK_IN_COMPLETED = "check_in_completed"
    CHECK_OUT_COMPLETED = "check_out_completed"
    ATTENDANCE_JUDGED = "attendance_judged"
    DAY_FINISHED = "day_finished"
    DAY_CLOSED = "day_closed"
    WEEK_CLOSED = "week_closed"
    SHOOTING_DAY_SET = "shooting_day_set"
    BET_SETTLED = "bet_settled"
    REPORT_GENERATED = "report_generated"
    SETTINGS_CHANGED = "settings_changed"
    WEEK_SETTLED = "week_settled"
    PROMISE_SET = "promise_set"


# 回调类型：接收事件类型和 payload
EventHandler = Callable[[EventType, dict[str, Any]], None]


class EventBus:
    """轻量级发布-订阅事件总线"""

    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[EventHandler]] = {
            event_type: [] for event_type in EventType
        }

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """订阅某类事件"""
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """取消订阅"""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    def publish(self, event_type: EventType, payload: dict[str, Any] | None = None) -> None:
        """发布事件，通知所有订阅者"""
        data = payload or {}
        for handler in self._subscribers[event_type]:
            handler(event_type, data)

    def clear(self) -> None:
        """清除所有订阅（测试用）"""
        for event_type in EventType:
            self._subscribers[event_type].clear()


# 全局单例
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """获取全局 EventBus 单例"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def set_event_bus(bus: EventBus) -> None:
    """注入 EventBus 实例（测试用）"""
    global _event_bus
    _event_bus = bus
