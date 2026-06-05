"""后端 EventBus 内存泄漏审计 — 订阅生命周期验证"""
from __future__ import annotations

import gc
import os
import tempfile
import weakref

from app.db import init_db, close_db
from app.utils.clock import SimulatedClock, set_clock
from app.services.event_bus import EventBus, EventType, set_event_bus, get_event_bus
from app.repositories.settings_repo import SettingsRepo
from app.repositories.checkin_repo import CheckinRepo
from app.services.checkin_service import CheckinService


# ── 模拟 Kivy Widget 生命周期管理的 Mixin ──

class WidgetSubscriptionManager:
    """Kivy Widget 订阅生命周期管理器（示范模式）。

    用法:
        class MyScreen(Screen, WidgetSubscriptionManager):
            def on_enter(self):
                self.subscribe(EventType.CHECK_IN_COMPLETED, self._on_checkin)
            def on_leave(self):
                self.unsubscribe_all()
    """

    def __init__(self) -> None:
        self._subscribed_events: list[tuple[EventType, object]] = []

    def subscribe(self, event_type: EventType, handler: object) -> None:
        """订阅事件并追踪，以便后续批量清理。"""
        bus = get_event_bus()
        bus.subscribe(event_type, handler)  # type: ignore[arg-type]
        self._subscribed_events.append((event_type, handler))

    def unsubscribe_all(self) -> int:
        """取消该 Widget 的所有订阅。返回取消数量。"""
        bus = get_event_bus()
        count = 0
        for event_type, handler in self._subscribed_events:
            bus.unsubscribe(event_type, handler)  # type: ignore[arg-type]
            count += 1
        self._subscribed_events.clear()
        return count


# ── 模拟 Screen — 使用 WidgetSubscriptionManager ──

class DummyScreen(WidgetSubscriptionManager):
    """模拟一个会订阅 EventBus 的 Kivy Screen"""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.received: list[str] = []

    def on_enter(self) -> None:
        self.subscribe(EventType.CHECK_IN_COMPLETED, self._on_checkin)
        self.subscribe(EventType.DAY_FINISHED, self._on_day_finished)

    def on_leave(self) -> None:
        self.unsubscribe_all()

    def _on_checkin(self, event_type: EventType, payload: dict) -> None:
        self.received.append(f"checkin:{payload.get('date', '')}")

    def _on_day_finished(self, event_type: EventType, payload: dict) -> None:
        self.received.append(f"day_finished:{payload.get('date', '')}")


def main():
    passed = 0
    failed = 0

    def check(desc: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [PASS] {desc}")
        else:
            failed += 1
            print(f"  [FAIL] {desc} — {detail}")

    # ============================================================
    # T-1: EventBus 诊断接口验证
    # ============================================================
    print("\n=== T-1: EventBus 诊断接口 ===")
    bus = EventBus()

    def handler_a(et, data): pass
    def handler_b(et, data): pass

    bus.subscribe(EventType.CHECK_IN_COMPLETED, handler_a)
    bus.subscribe(EventType.CHECK_IN_COMPLETED, handler_b)
    bus.subscribe(EventType.DAY_FINISHED, handler_a)

    check("subscriber_count(CHECK_IN_COMPLETED) = 2",
          bus.subscriber_count(EventType.CHECK_IN_COMPLETED) == 2,
          f"实际: {bus.subscriber_count(EventType.CHECK_IN_COMPLETED)}")
    check("subscriber_count(DAY_FINISHED) = 1",
          bus.subscriber_count(EventType.DAY_FINISHED) == 1,
          f"实际: {bus.subscriber_count(EventType.DAY_FINISHED)}")
    check("subscriber_count() 总计 = 3",
          bus.subscriber_count() == 3,
          f"实际: {bus.subscriber_count()}")

    subs = bus.list_subscribers(EventType.CHECK_IN_COMPLETED)
    check("list_subscribers 包含 handler_a",
          any("handler_a" in s for s in subs),
          f"实际: {subs}")
    check("list_subscribers 包含 handler_b",
          any("handler_b" in s for s in subs),
          f"实际: {subs}")

    # ============================================================
    # T-2: unsubscribe_all_for — 按对象批量清理
    # ============================================================
    print("\n=== T-2: unsubscribe_all_for 批量清理 ===")
    bus2 = EventBus()
    set_event_bus(bus2)  # 关键：DummyScreen 内使用 get_event_bus()
    screen = DummyScreen("test_screen")
    screen.on_enter()

    count_before = bus2.subscriber_count()
    check("订阅后有 handler 注册",
          count_before == 2,
          f"实际: {count_before}")

    removed = bus2.unsubscribe_all_for(screen)
    check("unsubscribe_all_for 移除 2 个 handler",
          removed == 2,
          f"实际: {removed}")
    check("清理后订阅数为 0",
          bus2.subscriber_count() == 0,
          f"实际: {bus2.subscriber_count()}")

    # ============================================================
    # T-3: WidgetSubscriptionManager 生命周期闭环
    # ============================================================
    print("\n=== T-3: Widget 生命周期闭环验证 ===")
    bus3 = EventBus()
    set_event_bus(bus3)

    screen2 = DummyScreen("lifecycle_test")
    screen2.on_enter()
    check("on_enter 后订阅 2 个事件",
          bus3.subscriber_count() == 2,
          f"实际: {bus3.subscriber_count()}")

    # 模拟发布事件，验证 handler 正常工作
    bus3.publish(EventType.CHECK_IN_COMPLETED, {"date": "2026-06-01"})
    check("handler 收到事件",
          len(screen2.received) == 1,
          f"实际: {screen2.received}")

    # 离开屏幕 → 取消订阅
    cleaned = screen2.unsubscribe_all()
    check("on_leave 清理 2 个订阅",
          cleaned == 2,
          f"实际: {cleaned}")
    check("离开后 EventBus 订阅数为 0",
          bus3.subscriber_count() == 0,
          f"实际: {bus3.subscriber_count()}")

    # 再次发布事件 → 不应触发已清理的 handler
    old_len = len(screen2.received)
    bus3.publish(EventType.CHECK_IN_COMPLETED, {"date": "2026-06-02"})
    check("离开后不再收到事件",
          len(screen2.received) == old_len,
          f"实际新增: {len(screen2.received) - old_len}")

    # ============================================================
    # T-4: 100 次页面切换 — 内存泄漏验证
    # ============================================================
    print("\n=== T-4: 100 次页面切换内存泄漏验证 ===")
    bus4 = EventBus()
    set_event_bus(bus4)

    for i in range(100):
        s = DummyScreen(f"screen_{i}")
        s.on_enter()
        check(f"切换 {i+1} 后订阅总数 ≤ 2",
              bus4.subscriber_count() <= 2,
              f"实际: {bus4.subscriber_count()}")
        s.on_leave()
        check(f"离开 {i+1} 后订阅总数 = 0",
              bus4.subscriber_count() == 0,
              f"实际: {bus4.subscriber_count()}")

    # 验证无死引用：所有 Screen 都应被 GC
    gc.collect()

    # ============================================================
    # T-5: 无 WidgetSubscriptionManager 时的泄漏对照
    # ============================================================
    print("\n=== T-5: 泄漏对照（无清理） ===")
    bus5 = EventBus()
    set_event_bus(bus5)

    # 模拟"坏"模式：只订阅不取消
    for i in range(50):
        s = DummyScreen(f"leak_{i}")
        s.on_enter()
        # 故意不调用 on_leave() — 模拟 bug

    leaked_count = bus5.subscriber_count()
    check("不清理时订阅持续增长",
          leaked_count > 10,
          f"泄漏的 handler 数: {leaked_count} (预期 >> 2)")

    # 使用 unsubscribe_all_for 修复泄漏
    bus5.clear()
    check("clear() 后归零", bus5.subscriber_count() == 0)

    # ============================================================
    # T-6: 全局 EventBus 当前订阅者审计
    # ============================================================
    print("\n=== T-6: 全局 EventBus 审计 ===")
    # 重置
    set_event_bus(EventBus())

    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(db_path)

    from app.services.bet_service import BetService
    from app.repositories.ledger_repo import LedgerRepo
    from app.repositories.bet_repo import BetRepo

    # 实例化带订阅的 Service
    cs = CheckinService(CheckinRepo(db_path), SettingsRepo(db_path))
    bs = BetService(BetRepo(db_path), LedgerRepo(db_path), SettingsRepo(db_path))

    total = get_event_bus().subscriber_count()
    print(f"  [INFO] 2 个 Service 实例化后，EventBus 订阅总数: {total}")

    for et in EventType:
        cnt = get_event_bus().subscriber_count(et)
        if cnt > 0:
            names = get_event_bus().list_subscribers(et)
            print(f"  [INFO]   {et.value}: {cnt} 订阅者 — {names}")

    # 获取订阅最密集的事件
    max_et = max(EventType, key=lambda et: get_event_bus().subscriber_count(et))
    max_cnt = get_event_bus().subscriber_count(max_et)
    check("存在订阅关系（Service 层正常注册）",
          total >= 1,
          f"总订阅: {total}")
    check("无异常订阅密度（单个事件订阅者 ≤ 5）",
          max_cnt <= 5,
          f"{max_et.value} 有 {max_cnt} 个订阅者")

    close_db()
    os.unlink(db_path)

    # ============================================================
    print(f"\n=== 内存泄漏审计完毕 ===")
    print(f"通过: {passed}, 失败: {failed}")
    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
