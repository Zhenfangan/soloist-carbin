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
