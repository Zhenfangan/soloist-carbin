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
