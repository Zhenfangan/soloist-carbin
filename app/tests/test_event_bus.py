"""EventBus 事件总线测试"""

from __future__ import annotations

from typing import Any

from app.services.event_bus import EventBus, EventType, get_event_bus, set_event_bus


class TestEventBus:
    def test_subscribe_and_publish(self) -> None:
        bus = EventBus()
        received: list[dict[str, Any]] = []

        def handler(event_type: EventType, payload: dict[str, Any]) -> None:
            received.append(payload)

        bus.subscribe(EventType.CHECK_IN_COMPLETED, handler)
        bus.publish(EventType.CHECK_IN_COMPLETED, {"date": "2026-06-01"})

        assert len(received) == 1
        assert received[0]["date"] == "2026-06-01"

    def test_multiple_subscribers(self) -> None:
        bus = EventBus()
        results: list[str] = []

        def handler1(event_type: EventType, payload: dict[str, Any]) -> None:
            results.append("h1")

        def handler2(event_type: EventType, payload: dict[str, Any]) -> None:
            results.append("h2")

        bus.subscribe(EventType.DAY_FINISHED, handler1)
        bus.subscribe(EventType.DAY_FINISHED, handler2)
        bus.publish(EventType.DAY_FINISHED)

        assert results == ["h1", "h2"]

    def test_unsubscribe(self) -> None:
        bus = EventBus()
        received: list[dict[str, Any]] = []

        def handler(event_type: EventType, payload: dict[str, Any]) -> None:
            received.append(payload)

        bus.subscribe(EventType.SETTINGS_CHANGED, handler)
        bus.unsubscribe(EventType.SETTINGS_CHANGED, handler)
        bus.publish(EventType.SETTINGS_CHANGED, {})

        assert len(received) == 0

    def test_publish_no_subscribers_does_not_raise(self) -> None:
        bus = EventBus()
        bus.publish(EventType.SHOOTING_DAY_SET, {"date": "2026-06-01"})

    def test_publish_none_payload(self) -> None:
        bus = EventBus()
        received: list[dict[str, Any]] = []

        def handler(event_type: EventType, payload: dict[str, Any]) -> None:
            received.append(payload)

        bus.subscribe(EventType.CHECK_IN_COMPLETED, handler)
        bus.publish(EventType.CHECK_IN_COMPLETED)

        assert received == [{}]

    def test_clear_removes_all(self) -> None:
        bus = EventBus()
        received: list[str] = []

        def handler(event_type: EventType, payload: dict[str, Any]) -> None:
            received.append("x")

        bus.subscribe(EventType.DAY_CLOSED, handler)
        bus.clear()
        bus.publish(EventType.DAY_CLOSED)

        assert len(received) == 0

    def test_duplicate_subscribe_idempotent(self) -> None:
        bus = EventBus()
        count = [0]

        def handler(event_type: EventType, payload: dict[str, Any]) -> None:
            count[0] += 1

        bus.subscribe(EventType.REPORT_GENERATED, handler)
        bus.subscribe(EventType.REPORT_GENERATED, handler)  # duplicate
        bus.publish(EventType.REPORT_GENERATED)

        assert count[0] == 1


class TestEventBusSingleton:
    def test_get_event_bus_returns_singleton(self) -> None:
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2

    def test_set_event_bus_overrides(self) -> None:
        original = get_event_bus()
        new_bus = EventBus()
        set_event_bus(new_bus)
        assert get_event_bus() is new_bus
        set_event_bus(original)  # restore


class TestEventTypeEnum:
    def test_all_event_types_present(self) -> None:
        expected = {
            EventType.CHECK_IN_COMPLETED,
            EventType.CHECK_OUT_COMPLETED,
            EventType.ATTENDANCE_JUDGED,
            EventType.DAY_FINISHED,
            EventType.DAY_CLOSED,
            EventType.WEEK_CLOSED,
            EventType.SHOOTING_DAY_SET,
            EventType.BET_SETTLED,
            EventType.BET_LATE_STARTED,
            EventType.REPORT_GENERATED,
            EventType.SETTINGS_CHANGED,
            EventType.WEEK_SETTLED,
            EventType.PROMISE_SET,
        }
        assert set(EventType) == expected
