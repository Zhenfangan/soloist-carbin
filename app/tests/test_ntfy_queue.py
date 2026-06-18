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
