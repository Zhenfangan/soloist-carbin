"""事件总线 — 模块间松耦合通信。

模块 A 触发模块 B 的行为时，通过 EventBus 发布事件，
模块 B 订阅相关事件类型，不直接跨模块调用 Service。

异常隔离：单个订阅者崩溃不影响后续订阅者，也不会向发布者传播。
环形检测：同一事件链递归深度超过阈值时截断并告警。
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Any

# 最大递归发布深度，防止环形依赖无限循环
MAX_PUBLISH_DEPTH = 5


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
    """轻量级发布-订阅事件总线（带异常隔离与环形检测）"""

    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[EventHandler]] = {
            event_type: [] for event_type in EventType
        }
        self._publish_depth = 0

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """订阅某类事件"""
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """取消订阅"""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    def publish(self, event_type: EventType, payload: dict[str, Any] | None = None) -> None:
        """发布事件，通知所有订阅者。

        每个 handler 包裹在独立 try/except 中。单个订阅者崩溃：
        - 异常被捕获并输出日志
        - 不影响后续订阅者
        - 不向调用者传播
        """
        if self._publish_depth >= MAX_PUBLISH_DEPTH:
            import logging
            logging.getLogger("EventBus").warning(
                "publish(%s) 被深度截断 (depth=%d)，可能存在环形依赖",
                event_type.value,
                self._publish_depth,
            )
            return

        base = payload or {}
        self._publish_depth += 1
        try:
            for handler in self._subscribers[event_type]:
                try:
                    handler(event_type, dict(base))  # 每个 handler 独立拷贝
                except Exception:
                    import logging
                    logging.getLogger("EventBus").exception(
                        "订阅者 %s 处理事件 %s 时崩溃，已隔离",
                        getattr(handler, "__name__", handler),
                        event_type.value,
                    )
        finally:
            self._publish_depth -= 1

    # ── 诊断与生命周期管理 ──

    def subscriber_count(self, event_type: EventType | None = None) -> int:
        """返回指定事件（或全部）的订阅者数量"""
        if event_type is not None:
            return len(self._subscribers[event_type])
        return sum(len(v) for v in self._subscribers.values())

    def list_subscribers(self, event_type: EventType) -> list[str]:
        """列出指定事件的所有订阅者名称（用于审计）"""
        result: list[str] = []
        for h in self._subscribers[event_type]:
            if hasattr(h, "__self__"):
                cls = type(h.__self__).__name__
                result.append(f"{cls}.{getattr(h, '__name__', '?')}")
            else:
                result.append(getattr(h, "__name__", str(h)))
        return result

    def unsubscribe_all_for(self, owner: object) -> int:
        """移除指定对象的所有订阅（用于 Widget/Service 销毁时批量清理）。

        返回移除的 handler 数量。
        """
        removed = 0
        for handlers in self._subscribers.values():
            to_remove = [h for h in handlers
                         if hasattr(h, "__self__") and h.__self__ is owner]
            for h in to_remove:
                handlers.remove(h)
                removed += 1
        return removed

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
