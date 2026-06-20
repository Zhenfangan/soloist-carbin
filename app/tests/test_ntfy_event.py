"""NtfyPushService 事件订阅与去重单测。"""
from __future__ import annotations
from typing import Any

import pytest

from app.services.event_bus import EventBus, EventType, set_event_bus
from app.services.ntfy_service import NtfyPushService
from app.services.settings_service import SettingsService


class _FakeRepo:
    def __init__(self, d: dict[str, str] | None = None) -> None:
        self.d = d or {}
    def get(self, key: str) -> str | None: return self.d.get(key)
    def set(self, key: str, value: str) -> None: self.d[key] = value
    def get_all(self) -> dict[str, str]: return dict(self.d)
    def batch_set(self, items: dict[str, str]) -> None: self.d.update(items)


@pytest.fixture
def fresh_bus() -> EventBus:
    bus = EventBus()
    set_event_bus(bus)
    return bus


def _make_svc(enabled: str = "1", topic: str = "test_topic", mono: list[float] | None = None) -> NtfyPushService:
    """构造一个 svc，可注入 monotonic 函数。"""
    repo = _FakeRepo({
        "ntfy_enabled": enabled,
        "ntfy_topic": topic,
        "ntfy_server": "https://ntfy.sh",
        "morning_end": "12:00",
        "afternoon_end": "18:00",
    })
    monotonic: Any = (lambda: mono.pop(0)) if mono is not None else None
    return NtfyPushService(SettingsService(repo), monotonic=monotonic)


def test_event_enabled_enqueues(fresh_bus: EventBus) -> None:
    svc = _make_svc()
    svc._subscribe_events()
    fresh_bus.publish(
        EventType.CHECK_IN_COMPLETED,
        {"date": "2026-06-18", "period": "morning", "checkin_time": "09:12", "status": "normal"},
    )
    assert svc.queue_size() == 1
    assert svc.peek_last() == "上午签到 09:12 ✨ 正常"


def test_event_disabled_skips(fresh_bus: EventBus) -> None:
    svc = _make_svc(enabled="0")
    svc._subscribe_events()
    fresh_bus.publish(
        EventType.CHECK_IN_COMPLETED,
        {"date": "2026-06-18", "period": "morning", "checkin_time": "09:12", "status": "normal"},
    )
    assert svc.queue_size() == 0


def test_event_topic_empty_skips(fresh_bus: EventBus) -> None:
    svc = _make_svc(topic="")
    svc._subscribe_events()
    fresh_bus.publish(
        EventType.CHECK_IN_COMPLETED,
        {"date": "2026-06-18", "period": "morning", "checkin_time": "09:12", "status": "normal"},
    )
    assert svc.queue_size() == 0


def test_attendance_judged_normal_not_enqueued(fresh_bus: EventBus) -> None:
    svc = _make_svc()
    svc._subscribe_events()
    fresh_bus.publish(
        EventType.ATTENDANCE_JUDGED,
        {"date": "2026-06-18", "period": "morning", "status": "normal"},
    )
    assert svc.queue_size() == 0


def test_attendance_judged_absent_enqueued(fresh_bus: EventBus) -> None:
    svc = _make_svc()
    svc._subscribe_events()
    fresh_bus.publish(
        EventType.ATTENDANCE_JUDGED,
        {"date": "2026-06-18", "period": "morning", "status": "absent_morning"},
    )
    assert svc.queue_size() == 1
    assert svc.peek_last() == "🚨 上午旷工：到 12:00 仍未签到"


def test_dedup_within_ttl(fresh_bus: EventBus) -> None:
    # monotonic 序列：0.0, 0.5, 0.5  → 两次 publish 都在 5s 内
    svc = _make_svc(mono=[0.0, 0.5, 0.5])
    svc._subscribe_events()
    payload = {"date": "2026-06-18", "period": "morning", "checkin_time": "09:12", "status": "normal"}
    fresh_bus.publish(EventType.CHECK_IN_COMPLETED, payload)
    fresh_bus.publish(EventType.CHECK_IN_COMPLETED, payload)
    assert svc.queue_size() == 1


def test_dedup_outside_ttl(fresh_bus: EventBus) -> None:
    # monotonic 序列：0.0, 0.0, 10.0, 10.0  → 第二次 publish 在 10s 后
    svc = _make_svc(mono=[0.0, 0.0, 10.0, 10.0])
    svc._subscribe_events()
    payload = {"date": "2026-06-18", "period": "morning", "checkin_time": "09:12", "status": "normal"}
    fresh_bus.publish(EventType.CHECK_IN_COMPLETED, payload)
    fresh_bus.publish(EventType.CHECK_IN_COMPLETED, payload)
    assert svc.queue_size() == 2


def test_send_test_success_returns_true(fresh_bus: EventBus) -> None:
    class _Resp:
        status_code = 200
    captured: list[tuple[str, bytes]] = []
    def fake_post(url: str, data: bytes = b"", timeout: float = 0) -> _Resp:
        captured.append((url, data))
        return _Resp()
    repo = _FakeRepo({"ntfy_enabled": "0", "ntfy_topic": "tx", "ntfy_server": "https://ntfy.sh"})
    svc = NtfyPushService(SettingsService(repo), http_post=fake_post)
    assert svc.send_test() is True
    assert captured[0][0] == "https://ntfy.sh/tx"
    assert "测试" in captured[0][1].decode("utf-8")


def test_send_test_topic_empty_returns_false(fresh_bus: EventBus) -> None:
    repo = _FakeRepo({"ntfy_enabled": "1", "ntfy_topic": ""})
    svc = NtfyPushService(SettingsService(repo))
    assert svc.send_test() is False


def test_send_test_exception_returns_false(fresh_bus: EventBus) -> None:
    def fake_post(*a, **kw):
        raise OSError("nope")
    repo = _FakeRepo({"ntfy_enabled": "1", "ntfy_topic": "tx"})
    svc = NtfyPushService(SettingsService(repo), http_post=fake_post)
    assert svc.send_test() is False
