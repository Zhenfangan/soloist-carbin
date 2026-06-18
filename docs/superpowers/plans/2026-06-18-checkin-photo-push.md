# 打卡推送通知（ntfy.sh）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用户每次签到 / 签退 / 触发旷工时，APP 自动通过 HTTP POST 到 `ntfy.sh/{topic}` 推送一条中文文字通知到 andy 的安卓手机，含状态（正常 / 迟到 / 早退 / 旷工）。离线时入持久化 JSON 队列，下次启动补发。

**Architecture:** 新建 `NtfyPushService`，订阅项目已有 `EventBus` 的 `CHECK_IN_COMPLETED / CHECK_OUT_COMPLETED / ATTENDANCE_JUDGED` 三个事件，EventBus.publish 同步入内存队列，daemon 线程消费内存队列做 HTTP POST。失败落盘 `user_data/push_queue.json`。UI 与业务零侵入；仅在 `app/main.py` 启动时实例化并 `start()`，在 `app/ui/screens/settings_screen.py` 加一个「推送通知」折叠组。

**Tech Stack:** Python 3.12 / Kivy / requests / pytest / 项目已有 EventBus + SettingsService

**Spec:** `docs/superpowers/specs/2026-06-18-checkin-photo-push-design.md`

---

## File Structure

| 文件 | 状态 | 职责 |
|---|---|---|
| `app/services/ntfy_service.py` | 新建 | `NtfyPushService` 类 + 文案常量 + 内存与持久化队列 |
| `app/services/settings_service.py` | 修改 | `DEFAULTS` 加 `ntfy_enabled / ntfy_topic / ntfy_server` |
| `app/main.py` | 修改 | 启动时实例化 `NtfyPushService(settings_svc).start()` |
| `app/ui/screens/settings_screen.py` | 修改 | 新增第 5 个 `CollapsibleGroup`「推送通知」 |
| `app/tests/test_ntfy_format.py` | 新建 | 单测：文案格式化 + 状态映射 |
| `app/tests/test_ntfy_event.py` | 新建 | 单测：订阅、去重、enabled / topic 兜底 |
| `app/tests/test_ntfy_queue.py` | 新建 | 单测：内存→HTTP→落盘、重启 flush、损坏文件、上限 |
| `app/tests/test_ntfy_integration.py` | 新建 | 集成：真实 `get_event_bus().publish(...)` → mock HTTP → 验证 |

---

## Task 1: SettingsService 新增 3 个配置项

**Files:**
- Modify: `app/services/settings_service.py:14-29`（在 `DEFAULTS` 末尾追加 3 行）
- Test: `app/tests/test_settings_ntfy_defaults.py`（新建）

- [ ] **Step 1: 写失败测试**

新建 `app/tests/test_settings_ntfy_defaults.py`：

```python
"""SettingsService 推送相关 DEFAULTS 单测。"""
from app.services.settings_service import SettingsService


def test_ntfy_defaults_present() -> None:
    d = SettingsService.DEFAULTS
    assert d["ntfy_enabled"] == "0"
    assert d["ntfy_topic"] == ""
    assert d["ntfy_server"] == "https://ntfy.sh"
```

- [ ] **Step 2: 跑测试看失败**

```
pytest app/tests/test_settings_ntfy_defaults.py -v
```

Expected: `KeyError: 'ntfy_enabled'`

- [ ] **Step 3: 修改 `DEFAULTS`**

打开 `app/services/settings_service.py`，把 `DEFAULTS` 字典（line 14-29）改为下面这个（仅在最后 `boyfriend_hour_threshold` 之后追加 3 行）：

```python
    DEFAULTS: dict[str, str] = {
        "morning_start": "09:00",
        "morning_end": "12:00",
        "afternoon_start": "14:00",
        "afternoon_end": "18:00",
        "late_penalty": "10",
        "early_leave_penalty": "10",
        "absent_penalty": "50",
        "full_attendance_bonus": "100",
        "bet_base_reward": "50",
        "bet_extra_reward": "30",
        "bet_penalty": "50",
        "work_days": "1,2,3,4,5",
        "shooting_reward": "30",
        "boyfriend_hour_threshold": "8",
        "ntfy_enabled": "0",
        "ntfy_topic": "",
        "ntfy_server": "https://ntfy.sh",
    }
```

- [ ] **Step 4: 跑测试看通过**

```
pytest app/tests/test_settings_ntfy_defaults.py -v
```

Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/settings_service.py app/tests/test_settings_ntfy_defaults.py
git commit -m "feat(settings): 新增 ntfy_enabled / ntfy_topic / ntfy_server 配置项

为打卡推送通知功能预留配置接口，默认禁用。"
```

---

## Task 2: NtfyPushService 文案格式化（纯函数 + 常量）

**Files:**
- Create: `app/services/ntfy_service.py`
- Test: `app/tests/test_ntfy_format.py`

- [ ] **Step 1: 写失败测试**

新建 `app/tests/test_ntfy_format.py`：

```python
"""NtfyPushService 文案格式化单测。"""
from app.services.event_bus import EventType
from app.services.ntfy_service import NtfyPushService
from app.services.settings_service import SettingsService


class _FakeRepo:
    def __init__(self, d: dict[str, str] | None = None) -> None:
        self.d = d or {}
    def get(self, key: str) -> str | None: return self.d.get(key)
    def set(self, key: str, value: str) -> None: self.d[key] = value
    def get_all(self) -> dict[str, str]: return dict(self.d)
    def batch_set(self, items: dict[str, str]) -> None: self.d.update(items)


def _svc() -> NtfyPushService:
    return NtfyPushService(SettingsService(_FakeRepo({"morning_end": "12:00", "afternoon_end": "18:00"})))


def test_format_check_in_normal() -> None:
    msg = _svc()._format_message(
        EventType.CHECK_IN_COMPLETED,
        {"date": "2026-06-18", "period": "morning", "checkin_time": "09:12", "status": "normal"},
    )
    assert msg == "上午签到 09:12 ✨ 正常"


def test_format_check_in_late() -> None:
    msg = _svc()._format_message(
        EventType.CHECK_IN_COMPLETED,
        {"date": "2026-06-18", "period": "morning", "checkin_time": "09:35", "status": "late"},
    )
    assert msg == "上午签到 09:35 ⚠️ 迟到"


def test_format_check_out_early_leave() -> None:
    msg = _svc()._format_message(
        EventType.CHECK_OUT_COMPLETED,
        {"date": "2026-06-18", "period": "afternoon", "checkout_time": "17:30", "status": "early_leave"},
    )
    assert msg == "下午签退 17:30 ⚠️ 早退"


def test_format_absent_morning() -> None:
    msg = _svc()._format_message(
        EventType.ATTENDANCE_JUDGED,
        {"date": "2026-06-18", "period": "morning", "status": "absent_morning"},
    )
    assert msg == "🚨 上午旷工：到 12:00 仍未签到"


def test_format_absent_afternoon() -> None:
    msg = _svc()._format_message(
        EventType.ATTENDANCE_JUDGED,
        {"date": "2026-06-18", "period": "afternoon", "status": "absent_afternoon"},
    )
    assert msg == "🚨 下午旷工：到 18:00 仍未签到"


def test_format_attendance_judged_non_absent_returns_none() -> None:
    # ATTENDANCE_JUDGED + normal/late/leave/shooting 都不该被独立推（避免和 check_in 重复）
    for status in ("normal", "late", "leave", "shooting"):
        msg = _svc()._format_message(
            EventType.ATTENDANCE_JUDGED,
            {"date": "2026-06-18", "period": "morning", "status": status},
        )
        assert msg is None, f"status={status} 应返回 None"
```

- [ ] **Step 2: 跑测试看失败**

```
pytest app/tests/test_ntfy_format.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.services.ntfy_service'`

- [ ] **Step 3: 写最小实现**

新建 `app/services/ntfy_service.py`：

```python
"""ntfy.sh 推送服务 — 订阅 EventBus 事件，推送中文打卡通知到 ntfy.sh 主题。"""

from __future__ import annotations

from typing import Any

from app.services.event_bus import EventType
from app.services.settings_service import SettingsService


# 状态 → (emoji, 中文标签) 映射
STATUS_LABELS: dict[str, tuple[str, str]] = {
    "normal":           ("✨", "正常"),
    "late":             ("⚠️", "迟到"),
    "early_leave":      ("⚠️", "早退"),
    "absent_morning":   ("🚨", "上午旷工"),
    "absent_afternoon": ("🚨", "下午旷工"),
    "leave":            ("🏠", "请假"),
    "shooting":         ("🎬", "拍摄日"),
}

PERIOD_CN: dict[str, str] = {"morning": "上午", "afternoon": "下午", "evening": "晚上"}


class NtfyPushService:
    """打卡推送服务。"""

    def __init__(self, settings_service: SettingsService) -> None:
        self._settings = settings_service

    def _format_message(self, event_type: EventType, payload: dict[str, Any]) -> str | None:
        status = str(payload.get("status", ""))
        period = str(payload.get("period", ""))
        period_cn = PERIOD_CN.get(period, period)
        emoji, label = STATUS_LABELS.get(status, ("", status))

        if event_type == EventType.CHECK_IN_COMPLETED:
            t = payload.get("checkin_time", "")
            return f"{period_cn}签到 {t} {emoji} {label}".strip()

        if event_type == EventType.CHECK_OUT_COMPLETED:
            t = payload.get("checkout_time", "")
            return f"{period_cn}签退 {t} {emoji} {label}".strip()

        if event_type == EventType.ATTENDANCE_JUDGED:
            if status not in ("absent_morning", "absent_afternoon"):
                return None
            end_key = "morning_end" if status == "absent_morning" else "afternoon_end"
            end_time = self._settings.get(end_key)
            return f"🚨 {period_cn}旷工：到 {end_time} 仍未签到"

        return None
```

- [ ] **Step 4: 跑测试看通过**

```
pytest app/tests/test_ntfy_format.py -v
```

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/ntfy_service.py app/tests/test_ntfy_format.py
git commit -m "feat(ntfy): NtfyPushService 文案格式化与状态映射

实现 _format_message: CHECK_IN_COMPLETED / CHECK_OUT_COMPLETED /
ATTENDANCE_JUDGED 三类事件的中文文案，含 emoji 与状态标签。
ATTENDANCE_JUDGED 仅在 absent_morning/absent_afternoon 触发，
避免与 CHECK_IN_COMPLETED 重复。"
```

---

## Task 3: 事件订阅 + 去重（无 HTTP）

**Files:**
- Modify: `app/services/ntfy_service.py`
- Test: `app/tests/test_ntfy_event.py`

- [ ] **Step 1: 写失败测试**

新建 `app/tests/test_ntfy_event.py`：

```python
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
```

- [ ] **Step 2: 跑测试看失败**

```
pytest app/tests/test_ntfy_event.py -v
```

Expected: `TypeError: ... got an unexpected keyword argument 'monotonic'` 或 `AttributeError: queue_size`

- [ ] **Step 3: 扩展 `ntfy_service.py`**

把 `app/services/ntfy_service.py` 完整替换为：

```python
"""ntfy.sh 推送服务 — 订阅 EventBus 事件，推送中文打卡通知到 ntfy.sh 主题。"""

from __future__ import annotations

import logging
import queue
import time
from collections.abc import Callable
from typing import Any

from app.services.event_bus import EventType, get_event_bus
from app.services.settings_service import SettingsService


STATUS_LABELS: dict[str, tuple[str, str]] = {
    "normal":           ("✨", "正常"),
    "late":             ("⚠️", "迟到"),
    "early_leave":      ("⚠️", "早退"),
    "absent_morning":   ("🚨", "上午旷工"),
    "absent_afternoon": ("🚨", "下午旷工"),
    "leave":            ("🏠", "请假"),
    "shooting":         ("🎬", "拍摄日"),
}

PERIOD_CN: dict[str, str] = {"morning": "上午", "afternoon": "下午", "evening": "晚上"}

DEDUP_TTL_SECONDS = 5.0
TOPIC_LOG_THROTTLE_SECONDS = 30.0

_logger = logging.getLogger("NtfyPushService")


class NtfyPushService:
    """打卡推送服务。"""

    def __init__(
        self,
        settings_service: SettingsService,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        self._settings = settings_service
        self._monotonic = monotonic or time.monotonic
        self._memory_queue: "queue.Queue[str]" = queue.Queue()
        self._recent: dict[str, float] = {}
        self._last_topic_warn = 0.0
        self._subscribed = False
        self._subscribed_handlers: list[tuple[EventType, Callable[..., None]]] = []

    # ── 订阅 ─────────────────────────────

    def _subscribe_events(self) -> None:
        if self._subscribed:
            return
        bus = get_event_bus()
        for et in (
            EventType.CHECK_IN_COMPLETED,
            EventType.CHECK_OUT_COMPLETED,
            EventType.ATTENDANCE_JUDGED,
        ):
            bus.subscribe(et, self._on_event)
            self._subscribed_handlers.append((et, self._on_event))
        self._subscribed = True

    def _unsubscribe_events(self) -> None:
        if not self._subscribed:
            return
        bus = get_event_bus()
        for et, handler in self._subscribed_handlers:
            bus.unsubscribe(et, handler)
        self._subscribed_handlers.clear()
        self._subscribed = False

    def _on_event(self, event_type: EventType, payload: dict[str, Any]) -> None:
        if self._settings.get("ntfy_enabled") != "1":
            return
        topic = self._settings.get("ntfy_topic")
        if not topic:
            now = self._monotonic()
            if now - self._last_topic_warn > TOPIC_LOG_THROTTLE_SECONDS:
                _logger.info("ntfy_topic 未配置，跳过推送")
                self._last_topic_warn = now
            return

        msg = self._format_message(event_type, payload)
        if msg is None:
            return

        key = self._dedup_key(event_type, payload)
        now = self._monotonic()
        self._recent = {k: t for k, t in self._recent.items() if now - t < DEDUP_TTL_SECONDS}
        if key in self._recent:
            return
        self._recent[key] = now

        self._memory_queue.put(msg)

    # ── 文案 ─────────────────────────────

    def _format_message(self, event_type: EventType, payload: dict[str, Any]) -> str | None:
        status = str(payload.get("status", ""))
        period = str(payload.get("period", ""))
        period_cn = PERIOD_CN.get(period, period)
        emoji, label = STATUS_LABELS.get(status, ("", status))

        if event_type == EventType.CHECK_IN_COMPLETED:
            t = payload.get("checkin_time", "")
            return f"{period_cn}签到 {t} {emoji} {label}".strip()

        if event_type == EventType.CHECK_OUT_COMPLETED:
            t = payload.get("checkout_time", "")
            return f"{period_cn}签退 {t} {emoji} {label}".strip()

        if event_type == EventType.ATTENDANCE_JUDGED:
            if status not in ("absent_morning", "absent_afternoon"):
                return None
            end_key = "morning_end" if status == "absent_morning" else "afternoon_end"
            end_time = self._settings.get(end_key)
            return f"🚨 {period_cn}旷工：到 {end_time} 仍未签到"

        return None

    @staticmethod
    def _dedup_key(event_type: EventType, payload: dict[str, Any]) -> str:
        return f"{payload.get('date','')}|{payload.get('period','')}|{payload.get('status','')}|{event_type.value}"

    # ── 测试辅助 ─────────────────────────

    def queue_size(self) -> int:
        return self._memory_queue.qsize()

    def peek_last(self) -> str | None:
        """返回当前队列里最后入队的一条（线程不安全，仅测试用）。"""
        items = list(self._memory_queue.queue)
        return items[-1] if items else None
```

- [ ] **Step 4: 跑测试看通过**

```
pytest app/tests/test_ntfy_format.py app/tests/test_ntfy_event.py -v
```

Expected: 13 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/ntfy_service.py app/tests/test_ntfy_event.py
git commit -m "feat(ntfy): 订阅 EventBus 三类事件 + 5s TTL 去重

订阅 CHECK_IN_COMPLETED / CHECK_OUT_COMPLETED / ATTENDANCE_JUDGED。
enabled=0 或 topic 为空时直接 skip；同 (date|period|status|event)
5 秒内重复触发只入队一次，避免 mark_absent 反复触发刷屏。
key 使用 time.monotonic()，不受项目模拟时钟影响。"
```

---

## Task 4: 持久化队列（落盘 / 读取 / 损坏 / 上限）

**Files:**
- Modify: `app/services/ntfy_service.py`
- Test: `app/tests/test_ntfy_queue.py`

- [ ] **Step 1: 写失败测试**

新建 `app/tests/test_ntfy_queue.py`：

```python
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
```

- [ ] **Step 2: 跑测试看失败**

```
pytest app/tests/test_ntfy_queue.py -v
```

Expected: `ImportError: cannot import name 'QUEUE_MAX'` 或 `TypeError: ... unexpected keyword argument 'queue_path'`

- [ ] **Step 3: 加 queue_path + 持久化方法**

打开 `app/services/ntfy_service.py`：

1. 在 imports 区域顶部添加：

```python
import json
from pathlib import Path
```

2. 在文件常量区（`DEDUP_TTL_SECONDS = 5.0` 那一行附近）新增：

```python
QUEUE_MAX = 200
HTTP_TIMEOUT = 3.0
BACKOFF_THRESHOLD = 3
BACKOFF_SECONDS = 30.0
```

3. 把 `__init__` 替换为：

```python
    def __init__(
        self,
        settings_service: SettingsService,
        queue_path: Path | None = None,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        self._settings = settings_service
        self._monotonic = monotonic or time.monotonic
        self._queue_path = queue_path or Path("user_data/push_queue.json")
        self._memory_queue: "queue.Queue[str]" = queue.Queue()
        self._recent: dict[str, float] = {}
        self._last_topic_warn = 0.0
        self._subscribed = False
        self._subscribed_handlers: list[tuple[EventType, Callable[..., None]]] = []
```

4. 在文件末尾、`peek_last` 之后追加：

```python
    # ── 持久化 ───────────────────────────

    def _read_persisted(self) -> list[str]:
        if not self._queue_path.exists():
            return []
        try:
            content = self._queue_path.read_text(encoding="utf-8")
            data = json.loads(content) if content.strip() else []
            if not isinstance(data, list):
                return []
            return [m for m in data if isinstance(m, str)]
        except Exception:
            return []

    def _append_persisted(self, msgs: list[str]) -> None:
        self._queue_path.parent.mkdir(parents=True, exist_ok=True)
        current = self._read_persisted()
        current.extend(msgs)
        if len(current) > QUEUE_MAX:
            dropped = len(current) - QUEUE_MAX
            current = current[-QUEUE_MAX:]
            _logger.warning(f"push_queue 超 {QUEUE_MAX} 条，丢弃最早 {dropped} 条")
        self._queue_path.write_text(
            json.dumps(current, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_persisted_queue(self) -> None:
        if not self._queue_path.exists():
            return
        try:
            content = self._queue_path.read_text(encoding="utf-8")
            data = json.loads(content) if content.strip() else []
            if not isinstance(data, list):
                self._queue_path.write_text("[]", encoding="utf-8")
                return
            for m in data:
                if isinstance(m, str):
                    self._memory_queue.put(m)
            self._queue_path.write_text("[]", encoding="utf-8")
        except Exception as e:
            _logger.warning(f"push_queue.json 解析失败，已清空: {e}")
            try:
                self._queue_path.write_text("[]", encoding="utf-8")
            except Exception:
                pass
```

- [ ] **Step 4: 跑测试看通过**

```
pytest app/tests/test_ntfy_queue.py -v
```

Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/ntfy_service.py app/tests/test_ntfy_queue.py
git commit -m "feat(ntfy): 持久化队列 push_queue.json

新增 _load_persisted_queue / _read_persisted / _append_persisted。
启动时读 JSON → 入内存 → 清空文件；失败/上限 / 损坏 / 非 list
均不抛异常，按 spec §7 处理。"
```

---

## Task 5: 后台 daemon 线程消费 + HTTP POST

**Files:**
- Modify: `app/services/ntfy_service.py`
- Test: `app/tests/test_ntfy_queue.py`（新增 case）

- [ ] **Step 1: 写失败测试**

向 `app/tests/test_ntfy_queue.py` **追加**：

```python
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
```

- [ ] **Step 2: 跑测试看失败**

```
pytest app/tests/test_ntfy_queue.py::test_consume_success_does_not_persist -v
```

Expected: `TypeError: ... unexpected keyword argument 'http_post'`

- [ ] **Step 3: 加 start / stop / 消费循环**

打开 `app/services/ntfy_service.py`，做以下三处改动：

1. 文件顶部 imports 加：

```python
import threading
```

并把 `requests` 也加上（在 `from collections.abc import Callable` 之后）：

```python
import requests
```

2. 把 `__init__` 替换为（新增 `http_post`、`sleep`、`_thread`、`_stop_flag`、`_consecutive_failures`）：

```python
    def __init__(
        self,
        settings_service: SettingsService,
        queue_path: Path | None = None,
        monotonic: Callable[[], float] | None = None,
        http_post: Callable[..., Any] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self._settings = settings_service
        self._monotonic = monotonic or time.monotonic
        self._queue_path = queue_path or Path("user_data/push_queue.json")
        self._http_post = http_post or requests.post
        self._sleep = sleep or time.sleep
        self._memory_queue: "queue.Queue[str]" = queue.Queue()
        self._recent: dict[str, float] = {}
        self._last_topic_warn = 0.0
        self._subscribed = False
        self._subscribed_handlers: list[tuple[EventType, Callable[..., None]]] = []
        self._thread: threading.Thread | None = None
        self._stop_flag = threading.Event()
        self._consecutive_failures = 0
```

3. 在「订阅」区之前（紧挨 `# ── 订阅 ──...` 上方）插入：

```python
    # ── 启停 ──────────────────────────────

    def start(self) -> None:
        """启动 daemon 线程 + 订阅事件 + flush 持久化队列。"""
        if self._thread is not None:
            return
        self._load_persisted_queue()
        self._subscribe_events()
        self._stop_flag.clear()
        self._thread = threading.Thread(
            target=self._consume_loop, daemon=True, name="NtfyConsumer"
        )
        self._thread.start()

    def stop(self) -> None:
        """停止线程并把内存队列 flush 到磁盘（用于优雅退出 / 测试）。"""
        self._stop_flag.set()
        if self._thread is not None:
            self._thread.join(timeout=1.5)
            self._thread = None
        self._unsubscribe_events()
        remaining: list[str] = []
        while True:
            try:
                remaining.append(self._memory_queue.get_nowait())
            except queue.Empty:
                break
        if remaining:
            self._append_persisted(remaining)

    # ── 消费 ─────────────────────────────

    def _consume_loop(self) -> None:
        while not self._stop_flag.is_set():
            try:
                msg = self._memory_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            topic = self._settings.get("ntfy_topic")
            server = self._settings.get("ntfy_server") or "https://ntfy.sh"
            if not topic:
                # 无 topic：丢弃本条，避免无限 backoff
                continue
            if self._send_one(server, topic, msg):
                self._consecutive_failures = 0
            else:
                self._append_persisted([msg])
                self._consecutive_failures += 1
                if self._consecutive_failures >= BACKOFF_THRESHOLD:
                    self._sleep(BACKOFF_SECONDS)
                    self._consecutive_failures = 0

    def _send_one(self, server: str, topic: str, msg: str) -> bool:
        url = f"{server.rstrip('/')}/{topic}"
        try:
            resp = self._http_post(url, data=msg.encode("utf-8"), timeout=HTTP_TIMEOUT)
            return 200 <= getattr(resp, "status_code", 0) < 300
        except Exception:
            return False
```

- [ ] **Step 4: 跑测试看通过**

```
pytest app/tests/test_ntfy_queue.py -v
```

Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/ntfy_service.py app/tests/test_ntfy_queue.py
git commit -m "feat(ntfy): daemon 线程消费内存队列 + HTTP POST + 失败落盘

start/stop 控制线程生命周期；消费循环：成功 → 丢弃；失败 →
追加 push_queue.json；连续 3 次失败触发 30s backoff。stop() 会把
剩余内存队列 flush 到磁盘，下次启动自动从 JSON 补发。"
```

---

## Task 6: send_test（设置页「测试推送」按钮用）

**Files:**
- Modify: `app/services/ntfy_service.py`
- Test: `app/tests/test_ntfy_event.py`（追加）

- [ ] **Step 1: 写失败测试**

向 `app/tests/test_ntfy_event.py` **追加**：

```python
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
```

- [ ] **Step 2: 跑测试看失败**

```
pytest app/tests/test_ntfy_event.py::test_send_test_success_returns_true -v
```

Expected: `AttributeError: 'NtfyPushService' object has no attribute 'send_test'`

- [ ] **Step 3: 加 send_test 方法**

打开 `app/services/ntfy_service.py`，在 `_send_one` 方法后追加：

```python
    # ── 测试推送（设置页按钮）─────────────

    def send_test(self) -> bool:
        """同步发一条 'soloist 测试通知'，绕开 enabled / 队列。"""
        topic = self._settings.get("ntfy_topic")
        server = self._settings.get("ntfy_server") or "https://ntfy.sh"
        if not topic:
            return False
        return self._send_one(server, topic, "soloist 测试通知")
```

- [ ] **Step 4: 跑测试看通过**

```
pytest app/tests/test_ntfy_event.py -v
```

Expected: 10 passed（原 7 + 新 3）

- [ ] **Step 5: Commit**

```bash
git add app/services/ntfy_service.py app/tests/test_ntfy_event.py
git commit -m "feat(ntfy): send_test 同步发测试推送

设置页「测试推送」按钮调用入口；绕开 enabled / 队列，topic 为空
直接 False。HTTP 异常 / 非 2xx 返回 False。"
```

---

## Task 7: 集成测试（真实 EventBus + CheckinService → mock HTTP）

**Files:**
- Create: `app/tests/test_ntfy_integration.py`

- [ ] **Step 1: 写测试**

新建 `app/tests/test_ntfy_integration.py`：

```python
"""NtfyPushService 与 CheckinService + EventBus 的集成测试。"""
from __future__ import annotations
import threading
from pathlib import Path

import pytest

from app.repositories.checkin_repo import CheckinRepo
from app.repositories.settings_repo import SettingsRepo
from app.services.checkin_service import CheckinService
from app.services.event_bus import EventBus, set_event_bus
from app.services.ntfy_service import NtfyPushService
from app.services.settings_service import SettingsService


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    from app.db import init_db
    p = str(tmp_path / "test.db")
    init_db(p)
    return p


class _Resp:
    def __init__(self, code: int = 200) -> None:
        self.status_code = code


def _wait_for(predicate, timeout: float = 2.0) -> None:
    """简单等待 predicate 为真，最长 timeout 秒。"""
    import time as _t
    end = _t.monotonic() + timeout
    while _t.monotonic() < end:
        if predicate():
            return
        _t.sleep(0.05)


def test_check_in_triggers_ntfy(db_path: str, tmp_path: Path) -> None:
    set_event_bus(EventBus())
    posts: list[bytes] = []
    def fake_post(url: str, data: bytes = b"", timeout: float = 0) -> _Resp:
        posts.append(data)
        return _Resp(200)

    settings_repo = SettingsRepo(db_path)
    settings_repo.set("ntfy_enabled", "1")
    settings_repo.set("ntfy_topic", "andy_test")
    settings_repo.set("morning_start", "09:00")
    settings_repo.set("morning_end", "12:00")
    settings_svc = SettingsService(settings_repo)
    checkin_svc = CheckinService(CheckinRepo(db_path), settings_repo)
    ntfy = NtfyPushService(
        settings_svc,
        queue_path=tmp_path / "push_queue.json",
        http_post=fake_post,
    )
    ntfy.start()
    try:
        checkin_svc.check_in("2026-06-18", "morning", None)
        _wait_for(lambda: len(posts) >= 1)
    finally:
        ntfy.stop()

    assert len(posts) >= 1
    decoded = posts[0].decode("utf-8")
    assert "签到" in decoded
    assert "上午" in decoded


def test_mark_absent_triggers_ntfy_once(db_path: str, tmp_path: Path) -> None:
    set_event_bus(EventBus())
    posts: list[bytes] = []
    def fake_post(url: str, data: bytes = b"", timeout: float = 0) -> _Resp:
        posts.append(data)
        return _Resp(200)

    settings_repo = SettingsRepo(db_path)
    settings_repo.set("ntfy_enabled", "1")
    settings_repo.set("ntfy_topic", "andy_test")
    settings_repo.set("morning_start", "09:00")
    settings_repo.set("morning_end", "12:00")
    settings_svc = SettingsService(settings_repo)

    # 模拟当前时间 > morning_end
    from app.utils.clock import SimulatedClock, set_clock
    from datetime import datetime
    set_clock(SimulatedClock(datetime(2026, 6, 18, 13, 0, 0)))

    checkin_svc = CheckinService(CheckinRepo(db_path), settings_repo)
    ntfy = NtfyPushService(
        settings_svc,
        queue_path=tmp_path / "push_queue.json",
        http_post=fake_post,
    )
    ntfy.start()
    try:
        # mark_absent 可能被前端反复调用
        checkin_svc.mark_absent("2026-06-18")
        checkin_svc.mark_absent("2026-06-18")
        _wait_for(lambda: len(posts) >= 1)
        # 给一点点时间，确保第二次 mark_absent 即使触发事件也不会重复入队
        import time as _t
        _t.sleep(0.2)
    finally:
        ntfy.stop()

    assert len(posts) == 1
    assert "旷工" in posts[0].decode("utf-8")
```

- [ ] **Step 2: 跑测试看通过**

```
pytest app/tests/test_ntfy_integration.py -v
```

Expected: 2 passed

- [ ] **Step 3: 跑全部 ntfy 测试**

```
pytest app/tests/test_ntfy_format.py app/tests/test_ntfy_event.py app/tests/test_ntfy_queue.py app/tests/test_ntfy_integration.py app/tests/test_settings_ntfy_defaults.py -v
```

Expected: 全部通过

- [ ] **Step 4: Commit**

```bash
git add app/tests/test_ntfy_integration.py
git commit -m "test(ntfy): 集成测试：CheckinService → EventBus → NtfyPushService

验证真实 check_in / mark_absent 调用链能通过 EventBus 到达
NtfyPushService 并触发 HTTP 调用；mark_absent 反复触发只推一次
（去重生效）。"
```

---

## Task 8: 接入 `app/main.py`

**Files:**
- Modify: `app/main.py:37`（imports 区追加）
- Modify: `app/main.py:94-109`（service 创建区追加实例化与 start）
- Modify: `app/main.py:211-213`（`on_stop` 调用 stop）

- [ ] **Step 1: 加 import**

打开 `app/main.py`，在第 37 行 `from app.services.sync_service import SyncService` 之后追加：

```python
from app.services.ntfy_service import NtfyPushService  # noqa: E402
```

- [ ] **Step 2: 在 build() 里实例化并 start**

定位 `build()` 方法里 `self._motivation_svc = MotivationService(...)` 那段（约 line 107-109），在其**之后**、`# 根布局` 注释之前追加：

```python
        # 打卡推送服务（订阅 EventBus，发到 ntfy.sh）
        self._ntfy_svc = NtfyPushService(settings_svc)
        self._ntfy_svc.start()
```

- [ ] **Step 3: on_stop 里优雅停止线程**

把 `on_stop` 方法（line 211-213）替换为：

```python
    def on_stop(self) -> None:
        """应用退出时清理资源。"""
        if hasattr(self, "_ntfy_svc"):
            self._ntfy_svc.stop()
```

- [ ] **Step 4: 跑全套测试，确保没破坏**

```
pytest -x
```

Expected: 全绿（或与之前一样的预期失败数）

- [ ] **Step 5: Commit**

```bash
git add app/main.py
git commit -m "feat(main): 启动时实例化 NtfyPushService.start()

订阅 EventBus 三类事件；on_stop 时优雅停止 daemon 并 flush
内存队列到磁盘。"
```

---

## Task 9: 设置页「推送通知」分组

**Files:**
- Modify: `app/ui/screens/settings_screen.py`

> 设置页需要拿到 `NtfyPushService` 才能调 `send_test`。为了不打破现有 SettingsScreen 的构造签名（其他地方调用方多），我们用「读 App.get_running_app()._ntfy_svc」的方式按需拿。

- [ ] **Step 1: 加分组构造方法**

打开 `app/ui/screens/settings_screen.py`，在 `_build_other_group` 方法之后追加一个新方法 `_build_ntfy_group`：

```python
    # ------------------------------------------------------------------
    # 推送通知组
    # ------------------------------------------------------------------

    def _build_ntfy_group(self) -> Widget:
        box = self._make_vbox()

        # --- 开关行 ---
        switch_row = BoxLayout(
            orientation="horizontal",
            spacing=CARD_PADDING,
            padding=[CARD_PADDING, 4],
            size_hint=(1, None),
            height=48,
        )
        switch_lbl = Label(
            text="启用推送",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, 1),
            halign="left",
            valign="middle",
            text_size=(None, None),
        )
        switch_row.add_widget(switch_lbl)

        enabled_now = self._read("ntfy_enabled") == "1"
        toggle_btn = PixelButton(
            text="开" if enabled_now else "关",
            size_mode="small",
            size_hint=(None, 1),
            width=80,
            color=MINT_GREEN if enabled_now else COLORS["CARD_SHADOW"],
        )

        def _on_toggle(_btn: Any) -> None:
            new_val = "0" if self._read("ntfy_enabled") == "1" else "1"
            self._write("ntfy_enabled", new_val)
            toggle_btn.text = "开" if new_val == "1" else "关"
            toggle_btn.set_color(MINT_GREEN if new_val == "1" else COLORS["CARD_SHADOW"])

        toggle_btn.bind(on_press=_on_toggle)
        switch_row.add_widget(toggle_btn)
        box.add_widget(switch_row)

        # --- topic 输入 + 随机生成 ---
        topic_row = BoxLayout(
            orientation="horizontal",
            spacing=CARD_PADDING,
            padding=[CARD_PADDING, 4],
            size_hint=(1, None),
            height=48,
        )
        topic_lbl = Label(
            text="主题(topic)",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, 1),
            width=90,
            halign="left",
            valign="middle",
            text_size=(90, None),
        )
        topic_row.add_widget(topic_lbl)

        topic_input = PixelInput(
            hint_text="andy-soloist-xxxxxxx",
            value=self._read("ntfy_topic"),
            password=False,
            size_hint=(1, 1),
        )
        topic_input.bind(text=lambda _i, v: self._write("ntfy_topic", v))
        topic_row.add_widget(topic_input)

        rand_btn = PixelButton(
            text="随机",
            size_mode="small",
            size_hint=(None, 1),
            width=70,
            color=SKY_BLUE,
        )

        def _on_random(_btn: Any) -> None:
            import secrets
            new_topic = f"andy-soloist-{secrets.token_urlsafe(8)}"
            topic_input.text = new_topic
            self._write("ntfy_topic", new_topic)

        rand_btn.bind(on_press=_on_random)
        topic_row.add_widget(rand_btn)
        box.add_widget(topic_row)

        # --- 服务器地址（可选） ---
        server_row = self._build_text_input_row(
            label="服务器",
            key="ntfy_server",
            hint="https://ntfy.sh",
            password=False,
        )
        box.add_widget(server_row)

        # --- 测试推送按钮 ---
        box.add_widget(Widget(size_hint=(1, None), height=GRID_UNIT))
        test_btn = PixelButton(
            text="测试推送",
            color=WARM_ORANGE,
            size_mode="normal",
            size_hint=(1, None),
        )
        test_btn.bind(on_press=lambda _: self._on_ntfy_test())
        box.add_widget(test_btn)

        return box

    def _on_ntfy_test(self) -> None:
        """调当前 App 实例上的 NtfyPushService.send_test。"""
        from kivy.app import App
        app = App.get_running_app()
        svc = getattr(app, "_ntfy_svc", None) if app else None
        if svc is None:
            self.show_toast("推送服务未初始化")
            return
        try:
            ok = svc.send_test()
        except Exception as e:
            Logger.error(f"SettingsScreen: ntfy 测试推送失败 {e}")
            ok = False
        self.show_toast("测试推送已发出，请到 ntfy 客户端查看" if ok else "测试推送失败：请检查 topic / 网络")
```

- [ ] **Step 2: 把新分组注册到 ScrollView 内容里**

在 `__init__` 方法里，定位到 `# --- 4. 其他组 ---` 那段（约 line 134-140）。在 `content.add_widget(group4)` 之后追加：

```python
        # --- 5. 推送通知组 ---
        ntfy_content = self._build_ntfy_group()
        group5 = CollapsibleGroup(
            title="推送通知",
            content=ntfy_content,
            collapsed=True,
        )
        content.add_widget(group5)
```

- [ ] **Step 3: 手动跑 APP 验证（不能用纯 pytest 验证 UI）**

```
python -m app.main
```

操作步骤：

1. 进入设置 → 「推送通知」分组（默认折叠，展开）
2. 点「随机」生成 topic
3. 在浏览器打开 `https://ntfy.sh/<刚生成的 topic>`
4. 点「开」启用，再点「测试推送」
5. 浏览器应在 1 秒内收到 `soloist 测试通知`
6. 点 Toast 反馈应为「测试推送已发出，请到 ntfy 客户端查看」
7. 关掉 APP

Expected: 浏览器收到推送、Toast 提示成功

- [ ] **Step 4: Commit**

```bash
git add app/ui/screens/settings_screen.py
git commit -m "feat(ui/settings): 新增「推送通知」折叠分组

开关 / topic 输入 + 随机生成 / 服务器地址 / 测试推送按钮。
测试按钮调用当前 App 实例 _ntfy_svc.send_test，结果用 Toast 反馈。
默认折叠，避免对现有设置页布局造成视觉冲击。"
```

---

## Task 10: 端到端手动验收

**Files:** （仅手动，不改代码）

- [ ] **Step 1: 准备 ntfy 订阅**

PC 浏览器打开 `https://ntfy.sh/`，在顶部输入框填一个待会要用的 topic（如 `andy-soloist-test1`），点 Subscribe。手机暂时不装也可以先在浏览器验证。

- [ ] **Step 2: 跑桌面端 APP**

```
python -m app.main
```

- [ ] **Step 3: 设置 topic、开启推送**

设置页 → 推送通知 → 填入 `andy-soloist-test1` → 点「开」→ 点「测试推送」。

Expected: 浏览器 1 秒内收到 `soloist 测试通知`

- [ ] **Step 4: 模拟打卡触发推送**

进入「打卡」页 → 点上午签到 → 桌面 Mock 弹窗确认。

Expected: 浏览器收到 `上午签到 HH:MM ✨ 正常`（或 ⚠️ 迟到，视虚拟时钟时间而定）

- [ ] **Step 5: 验证去重**

退出 APP → 重启 APP（虚拟时钟会回到 周日 08:00 因为是硬编码 SimulatedClock）→ 再点上午签到。

Expected: 浏览器再次收到一条；同一时段不会因 `mark_absent` 反复刷屏

- [ ] **Step 6: 验证离线 → 重启补发**

关掉 Wi-Fi（或在 hosts 把 ntfy.sh 指 127.0.0.1）→ 在 APP 里点下午签到 → 等几秒（让 daemon 失败落盘）→ 检查 `user_data/push_queue.json` 应包含 1 条 → 关 APP → 恢复网络 → 重启 APP。

Expected: 浏览器 5 秒内收到补发的下午签到推送；JSON 文件清空

- [ ] **Step 7: 验证关闭开关**

设置页关掉「启用推送」→ 再次点签到/签退。

Expected: 浏览器无新推送

- [ ] **Step 8: 收尾 Commit（可选 — 仅记录验收结论）**

```bash
git commit --allow-empty -m "chore: 打卡推送通知功能端到端验收通过

测试矩阵: 测试推送 / 签到 / 签退 / 旷工去重 / 离线补发 / 开关。
all green."
```

---

## Self-Review

**Spec 覆盖**：

- [x] §1.3 目标 1-5：Task 2-10 覆盖
- [x] §3 组件清单：Task 2-9 全部新建 / 修改
- [x] §4 推送规则：Task 2 文案；Task 3 ATTENDANCE_JUDGED 过滤
- [x] §5 配置项：Task 1
- [x] §6 数据流：Task 5 daemon 线程；Task 7 集成
- [x] §7 错误处理：enabled / topic / 网络异常 / 4xx / JSON 损坏 / 上限 / 去重 / 时钟独立 / send_test，全部测试覆盖（Task 3-6）
- [x] §8 测试计划：Task 2-7
- [x] §10 DoD：Task 10 手动验收

**Placeholder 扫描**：无 TBD / TODO；所有代码段完整可直接 paste。

**类型一致性**：
- `NtfyPushService.__init__` 最终签名（Task 5 定义）：`(settings_service, queue_path=None, monotonic=None, http_post=None, sleep=None)`
- 测试中始终用关键字参数调用，与签名一致。
- `STATUS_LABELS` / `PERIOD_CN` / `QUEUE_MAX` / `HTTP_TIMEOUT` / `BACKOFF_THRESHOLD` / `BACKOFF_SECONDS` 在 Task 2 / 4 定义，后续 task 引用名称一致。
- `_subscribe_events / _unsubscribe_events / _format_message / _on_event / _enqueue (改为直接 put) / _consume_loop / _send_one / _load_persisted_queue / _read_persisted / _append_persisted / start / stop / send_test / queue_size / peek_last` 命名贯穿全 plan。

**已知遗留**：
- 请假 UI 未实现 → 不属于本任务范围（spec §1.4 明确排除）
- `_motivation_svc.NoOpNotifier` 与本任务无关，不动
