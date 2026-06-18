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
    for status in ("normal", "late", "leave", "shooting"):
        msg = _svc()._format_message(
            EventType.ATTENDANCE_JUDGED,
            {"date": "2026-06-18", "period": "morning", "status": status},
        )
        assert msg is None, f"status={status} 应返回 None"
