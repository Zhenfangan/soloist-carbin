"""ntfy.sh 推送服务 — 订阅 EventBus 事件，推送中文打卡通知到 ntfy.sh 主题。"""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
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
QUEUE_MAX = 200
HTTP_TIMEOUT = 3.0
BACKOFF_THRESHOLD = 3
BACKOFF_SECONDS = 30.0

_logger = logging.getLogger("NtfyPushService")


class NtfyPushService:
    """打卡推送服务。"""

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
        # 默认用 urllib(stdlib)发送, 避免在安卓上打包 requests; 测试可注入 http_post
        self._http_post = http_post or self._default_http_post
        self._sleep = sleep or time.sleep
        self._memory_queue: "queue.Queue[str]" = queue.Queue()
        self._recent: dict[str, float] = {}
        self._last_topic_warn = 0.0
        self._subscribed = False
        self._subscribed_handlers: list[tuple[EventType, Callable[..., None]]] = []
        self._thread: threading.Thread | None = None
        self._stop_flag = threading.Event()
        self._consecutive_failures = 0

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

    @staticmethod
    def _default_http_post(url: str, data: bytes, timeout: float) -> Any:
        """stdlib urllib 实现, 避免在安卓上打包 requests。"""
        req = urllib.request.Request(url, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return SimpleNamespace(status_code=resp.status)
        except urllib.error.HTTPError as e:
            return SimpleNamespace(status_code=e.code)

    # ── 测试推送（设置页按钮）─────────────

    def send_test(self) -> bool:
        """同步发一条 'soloist 测试通知'，绕开 enabled / 队列。"""
        topic = self._settings.get("ntfy_topic")
        server = self._settings.get("ntfy_server") or "https://ntfy.sh"
        if not topic:
            return False
        return self._send_one(server, topic, "soloist 测试通知")

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
        gc_now = self._monotonic()
        self._recent = {k: t for k, t in self._recent.items() if gc_now - t < DEDUP_TTL_SECONDS}
        if key in self._recent:
            return
        self._recent[key] = self._monotonic()

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
            if status in ("leave", "shooting"):
                t = payload.get("checkin_time", "")
                return f"{period_cn}{label} {t} {emoji}".strip()
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
