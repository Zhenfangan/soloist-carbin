"""NtfyPushService 持久化队列单测。"""
from __future__ import annotations
import json
from pathlib import Path

import pytest

from app.services.ntfy_service import QUEUE_MAX, NtfyPushService
from app.services.settings_service import SettingsService


class _FakeRepo:
    def __init__(self, d: dict[str, str] | None = None) -> None:
        self.d = d or {}
    def get(self, key: str) -> str | None: return self.d.get(key)
    def set(self, key: str, value: str) -> None: self.d[key] = value
    def get_all(self) -> dict[str, str]: return dict(self.d)
    def batch_set(self, items: dict[str, str]) -> None: self.d.update(items)


def _svc(tmp_path: Path) -> NtfyPushService:
    return NtfyPushService(
        SettingsService(_FakeRepo()),
        queue_path=tmp_path / "push_queue.json",
    )


def test_append_persisted_creates_file(tmp_path: Path) -> None:
    svc = _svc(tmp_path)
    svc._append_persisted(["A", "B"])
    data = json.loads((tmp_path / "push_queue.json").read_text(encoding="utf-8"))
    assert data == ["A", "B"]


def test_append_persisted_extends_existing(tmp_path: Path) -> None:
    qp = tmp_path / "push_queue.json"
    qp.write_text(json.dumps(["X"]), encoding="utf-8")
    svc = _svc(tmp_path)
    svc._append_persisted(["Y"])
    assert json.loads(qp.read_text(encoding="utf-8")) == ["X", "Y"]


def test_append_persisted_caps_at_max(tmp_path: Path) -> None:
    qp = tmp_path / "push_queue.json"
    qp.write_text(json.dumps([f"m{i}" for i in range(QUEUE_MAX)]), encoding="utf-8")
    svc = _svc(tmp_path)
    svc._append_persisted(["new1", "new2"])
    data = json.loads(qp.read_text(encoding="utf-8"))
    assert len(data) == QUEUE_MAX
    assert data[-1] == "new2"
    assert data[0] == "m2"  # 最早两条被丢


def test_load_persisted_into_memory(tmp_path: Path) -> None:
    qp = tmp_path / "push_queue.json"
    qp.write_text(json.dumps(["a", "b", "c"]), encoding="utf-8")
    svc = _svc(tmp_path)
    svc._load_persisted_queue()
    assert svc.queue_size() == 3
    # 文件被清空
    assert json.loads(qp.read_text(encoding="utf-8")) == []


def test_load_persisted_no_file(tmp_path: Path) -> None:
    svc = _svc(tmp_path)
    svc._load_persisted_queue()  # 不抛
    assert svc.queue_size() == 0


def test_load_persisted_corrupt_file(tmp_path: Path) -> None:
    qp = tmp_path / "push_queue.json"
    qp.write_text("{not valid json", encoding="utf-8")
    svc = _svc(tmp_path)
    svc._load_persisted_queue()  # 不抛
    assert svc.queue_size() == 0
    # 损坏文件被清空
    assert qp.read_text(encoding="utf-8") == "[]"


def test_load_persisted_non_list_treated_as_empty(tmp_path: Path) -> None:
    qp = tmp_path / "push_queue.json"
    qp.write_text(json.dumps({"oops": "dict"}), encoding="utf-8")
    svc = _svc(tmp_path)
    svc._load_persisted_queue()
    assert svc.queue_size() == 0
    assert json.loads(qp.read_text(encoding="utf-8")) == []


import threading
from app.services.event_bus import EventBus, EventType, set_event_bus


class _FakeResp:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def test_consume_success_does_not_persist(tmp_path: Path) -> None:
    set_event_bus(EventBus())
    calls: list[tuple[str, bytes]] = []
    def fake_post(url: str, data: bytes = b"", timeout: float = 0) -> _FakeResp:
        calls.append((url, data))
        return _FakeResp(200)

    repo = _FakeRepo({
        "ntfy_enabled": "1",
        "ntfy_topic": "t1",
        "ntfy_server": "https://ntfy.sh",
    })
    svc = NtfyPushService(
        SettingsService(repo),
        queue_path=tmp_path / "push_queue.json",
        http_post=fake_post,
    )
    svc.start()
    svc._memory_queue.put("hello")

    # 等线程处理
    for _ in range(20):
        if calls:
            break
        threading.Event().wait(0.05)

    svc.stop()
    assert len(calls) == 1
    assert calls[0][0] == "https://ntfy.sh/t1"
    assert calls[0][1] == "hello".encode("utf-8")
    # 没失败 → 不该持久化
    qp = tmp_path / "push_queue.json"
    assert (not qp.exists()) or json.loads(qp.read_text(encoding="utf-8")) == []


def test_consume_failure_persists(tmp_path: Path) -> None:
    set_event_bus(EventBus())
    def fake_post(url: str, data: bytes = b"", timeout: float = 0) -> _FakeResp:
        raise OSError("network down")

    repo = _FakeRepo({
        "ntfy_enabled": "1",
        "ntfy_topic": "t1",
        "ntfy_server": "https://ntfy.sh",
    })
    svc = NtfyPushService(
        SettingsService(repo),
        queue_path=tmp_path / "push_queue.json",
        http_post=fake_post,
        sleep=lambda s: None,  # 屏蔽 backoff sleep
    )
    svc.start()
    svc._memory_queue.put("hello")

    for _ in range(20):
        if (tmp_path / "push_queue.json").exists():
            data = json.loads((tmp_path / "push_queue.json").read_text(encoding="utf-8"))
            if data:
                break
        threading.Event().wait(0.05)

    svc.stop()
    data = json.loads((tmp_path / "push_queue.json").read_text(encoding="utf-8"))
    assert "hello" in data


def test_start_loads_persisted_then_consumes(tmp_path: Path) -> None:
    """启动时读 JSON → 入内存 → daemon 消费 → 调用 HTTP。"""
    set_event_bus(EventBus())
    (tmp_path / "push_queue.json").write_text(
        json.dumps(["restart_msg"]), encoding="utf-8"
    )
    calls: list[bytes] = []
    def fake_post(url: str, data: bytes = b"", timeout: float = 0) -> _FakeResp:
        calls.append(data)
        return _FakeResp(200)

    repo = _FakeRepo({
        "ntfy_enabled": "1",
        "ntfy_topic": "t1",
        "ntfy_server": "https://ntfy.sh",
    })
    svc = NtfyPushService(
        SettingsService(repo),
        queue_path=tmp_path / "push_queue.json",
        http_post=fake_post,
    )
    svc.start()
    for _ in range(20):
        if calls:
            break
        threading.Event().wait(0.05)
    svc.stop()
    assert calls == ["restart_msg".encode("utf-8")]
