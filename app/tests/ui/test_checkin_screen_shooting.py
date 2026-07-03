"""CheckinScreen 拍摄日集成 — UI 切换(卡片 ⇄ 时段卡) + 回调派发。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from kivy.clock import Clock

from app.ui.screens.checkin_screen import CheckinScreen
from app.utils.clock import get_clock


def _day_status(is_shooting: bool = False) -> SimpleNamespace:
    def _ps(p: str) -> SimpleNamespace:
        return SimpleNamespace(
            period=p, status="shooting" if is_shooting else "pending",
            checkin_time=None, checkout_time=None, checkout_type="manual",
        )
    return SimpleNamespace(
        date="2026-06-07",
        periods=[_ps("morning"), _ps("afternoon"), _ps("evening")],
        is_shooting_day=is_shooting,
        is_work_day=True,
    )


_SETTINGS = {
    "morning_start": "09:00", "afternoon_start": "14:00",
    "morning_end": "12:00", "afternoon_end": "18:00",
}


def _make_screen(is_shooting: bool = False, reflection: object = None):
    checkin = MagicMock()
    checkin.get_today_status.return_value = _day_status(is_shooting)
    checkin.mark_absent.return_value = None
    shooting = MagicMock()
    shooting.is_shooting_day.return_value = is_shooting
    shooting.get_reflection.return_value = reflection
    settings = MagicMock()
    settings.get.side_effect = lambda k: _SETTINGS.get(k, "")
    settings.get_user_nickname.return_value = ""
    motivation = MagicMock()
    motivation.get_current_streak.return_value = 0
    screen = CheckinScreen(
        checkin_service=checkin,
        shooting_service=shooting,
        settings_service=settings,
        motivation_service=motivation,
    )
    Clock.tick()
    return screen, checkin, shooting


class TestShootingScreenIntegration:
    def test_normal_day_before_morning_shows_idle_entry(self) -> None:
        get_clock().set_date_and_time("2026-06-07", "08:00")
        screen, _, _ = _make_screen(is_shooting=False)
        screen._apply_shooting_ui()
        assert screen._shooting_card.opacity == 1.0
        assert screen._shooting_card._state == "idle"
        assert screen._period_cards["morning"].opacity == 1.0

    def test_normal_day_after_morning_hides_entry(self) -> None:
        get_clock().set_date_and_time("2026-06-07", "10:00")
        screen, _, _ = _make_screen(is_shooting=False)
        screen._apply_shooting_ui()
        assert screen._shooting_card.opacity == 0.0
        assert screen._period_cards["morning"].opacity == 1.0

    def test_shooting_day_hides_periods_shows_active(self) -> None:
        get_clock().set_date_and_time("2026-06-07", "10:00")
        screen, _, _ = _make_screen(is_shooting=True, reflection=None)
        screen._apply_shooting_ui()
        assert screen._shooting_card._state == "active"
        assert screen._shooting_card.opacity == 1.0
        assert screen._period_cards["morning"].opacity == 0.0
        assert screen._status_box.opacity == 0.0

    def test_shooting_day_with_reflection_shows_done(self) -> None:
        get_clock().set_date_and_time("2026-06-07", "10:00")
        screen, _, _ = _make_screen(is_shooting=True, reflection=SimpleNamespace(summary="x"))
        screen._apply_shooting_ui()
        assert screen._shooting_card._state == "done"

    def test_on_set_shooting_day_calls_service(self) -> None:
        get_clock().set_date_and_time("2026-06-07", "08:00")
        screen, checkin, _ = _make_screen(is_shooting=False)
        screen._on_set_shooting_day()
        checkin.set_shooting_day.assert_called_once()

    def test_reflection_submit_calls_service(self) -> None:
        get_clock().set_date_and_time("2026-06-07", "10:00")
        screen, _, shooting = _make_screen(is_shooting=True, reflection=None)
        screen._on_reflection_submit(
            {"content": "a", "location": "b", "smoothness": "smooth", "thoughts": "c"}
        )
        shooting.submit_reflection.assert_called_once()

    def _make_reminder_screen(self, yesterday_shooting: bool, yesterday_reflection: object):
        """构造一个 screen: 今天(06-08)非拍摄日, 昨天(06-07)状态可配。"""
        get_clock().set_date_and_time("2026-06-08", "10:00")
        checkin = MagicMock()
        checkin.get_today_status.return_value = _day_status(is_shooting=False)
        checkin.mark_absent.return_value = None
        shooting = MagicMock()
        shooting.is_shooting_day.side_effect = (
            lambda d: d == "2026-06-07" and yesterday_shooting
        )
        shooting.get_reflection.side_effect = (
            lambda d: yesterday_reflection if d == "2026-06-07" else None
        )
        settings = MagicMock()
        settings.get.side_effect = lambda k: _SETTINGS.get(k, "")
        motivation = MagicMock()
        motivation.get_current_streak.return_value = 0
        screen = CheckinScreen(
            checkin_service=checkin, shooting_service=shooting,
            settings_service=settings, motivation_service=motivation,
        )
        Clock.tick()
        return screen

    def test_yesterday_reminder_fires_when_reflection_missing(self, monkeypatch) -> None:
        calls: list[tuple] = []
        import app.ui.components.toast as toast_mod
        monkeypatch.setattr(toast_mod, "show_toast", lambda *a, **k: calls.append(a))
        screen = self._make_reminder_screen(yesterday_shooting=True, yesterday_reflection=None)
        screen._check_yesterday_reflection_reminder()
        assert len(calls) == 1

    def test_yesterday_reminder_silent_when_reflection_done(self, monkeypatch) -> None:
        calls: list[tuple] = []
        import app.ui.components.toast as toast_mod
        monkeypatch.setattr(toast_mod, "show_toast", lambda *a, **k: calls.append(a))
        screen = self._make_reminder_screen(
            yesterday_shooting=True, yesterday_reflection=SimpleNamespace(summary="x")
        )
        screen._check_yesterday_reflection_reminder()
        assert calls == []

    def test_yesterday_reminder_silent_when_not_shooting(self, monkeypatch) -> None:
        calls: list[tuple] = []
        import app.ui.components.toast as toast_mod
        monkeypatch.setattr(toast_mod, "show_toast", lambda *a, **k: calls.append(a))
        screen = self._make_reminder_screen(yesterday_shooting=False, yesterday_reflection=None)
        screen._check_yesterday_reflection_reminder()
        assert calls == []


def test_capture_scene_invokes_camera_with_shooting_period() -> None:
    """拍摄日「拍张现场」→ 调相机 take_photo(period='shooting', action='scene')。"""
    get_clock().set_date_and_time("2026-06-07", "10:00")
    checkin = MagicMock()
    checkin.get_today_status.return_value = _day_status(is_shooting=True)
    checkin.mark_absent.return_value = None
    shooting = MagicMock()
    shooting.is_shooting_day.return_value = True
    shooting.get_reflection.return_value = None
    settings = MagicMock()
    settings.get.side_effect = lambda k: _SETTINGS.get(k, "")
    settings.get_user_nickname.return_value = ""
    motivation = MagicMock()
    motivation.get_current_streak.return_value = 0
    camera = MagicMock()
    screen = CheckinScreen(
        checkin_service=checkin,
        shooting_service=shooting,
        settings_service=settings,
        motivation_service=motivation,
        camera_service=camera,
    )
    Clock.tick()
    screen._on_capture_scene()
    camera.take_photo.assert_called_once()
    _args, kwargs = camera.take_photo.call_args
    assert kwargs.get("period") == "shooting"
    assert kwargs.get("action") == "scene"


def test_shooting_card_wired_with_capture_callback() -> None:
    """拍摄日卡片应接上 on_capture 回调(指向 screen._on_capture_scene)。"""
    get_clock().set_date_and_time("2026-06-07", "08:00")
    screen, _, _ = _make_screen(is_shooting=False)
    assert screen._shooting_card._on_capture == screen._on_capture_scene
