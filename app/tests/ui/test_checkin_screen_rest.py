"""CheckinScreen 休息日集成 — 休息期内隐藏一切、只显示"今日休息"+小兔动画。

休息日优先级高于拍摄日: 休息期内即便 shooting_service 认为是拍摄日,
也不应显示拍摄入口(你已经在休息, 不该同时冒出"设为拍摄日"的按钮)。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from kivy.clock import Clock

from app.ui.screens.checkin_screen import CheckinScreen
from app.utils.clock import get_clock


def _day_status() -> SimpleNamespace:
    def _ps(p: str) -> SimpleNamespace:
        return SimpleNamespace(
            period=p, status="pending", checkin_time=None, checkout_time=None,
            checkout_type="manual",
        )
    return SimpleNamespace(
        date="2026-06-07",
        periods=[_ps("morning"), _ps("afternoon"), _ps("evening")],
        is_shooting_day=False,
        is_work_day=True,
    )


_SETTINGS = {
    "morning_start": "09:00", "afternoon_start": "14:00",
    "morning_end": "12:00", "afternoon_end": "18:00",
}


def _make_screen(is_resting: bool, is_shooting: bool = False):
    checkin = MagicMock()
    checkin.get_today_status.return_value = _day_status()
    checkin.mark_absent.return_value = None
    shooting = MagicMock()
    shooting.is_shooting_day.return_value = is_shooting
    shooting.get_reflection.return_value = None
    settings = MagicMock()
    settings.get.side_effect = lambda k: _SETTINGS.get(k, "")
    settings.get_user_nickname.return_value = ""
    settings.is_rest_day.return_value = is_resting
    motivation = MagicMock()
    motivation.get_current_streak.return_value = 0
    screen = CheckinScreen(
        checkin_service=checkin,
        shooting_service=shooting,
        settings_service=settings,
        motivation_service=motivation,
    )
    Clock.tick()
    return screen, checkin, shooting, settings


class TestRestDayIntegration:
    def test_non_rest_day_shows_normal_periods_and_hides_rest_card(self) -> None:
        get_clock().set_date_and_time("2026-06-07", "10:00")
        screen, _, _, _ = _make_screen(is_resting=False)
        assert screen._rest_card.opacity == 0.0
        assert screen._period_cards["morning"].opacity == 1.0

    def test_rest_day_shows_rest_card_hides_periods(self) -> None:
        get_clock().set_date_and_time("2026-06-07", "10:00")
        screen, _, _, _ = _make_screen(is_resting=True)
        assert screen._rest_card.opacity == 1.0
        assert screen._period_cards["morning"].opacity == 0.0
        assert screen._status_box.opacity == 0.0

    def test_rest_day_takes_priority_over_shooting_day(self) -> None:
        """休息期内即使 shooting_service 认为是拍摄日, 也不显示拍摄入口。"""
        get_clock().set_date_and_time("2026-06-07", "08:00")  # 上午上班前,平时会显示拍摄入口
        screen, _, _, _ = _make_screen(is_resting=True, is_shooting=True)
        assert screen._rest_card.opacity == 1.0
        assert screen._shooting_card.opacity == 0.0

    def test_refresh_status_also_applies_rest_ui(self) -> None:
        """_refresh_status()(签到/签退后调用)同样要应用休息态, 不只是初次加载。"""
        get_clock().set_date_and_time("2026-06-07", "10:00")
        screen, _, _, settings = _make_screen(is_resting=False)
        assert screen._rest_card.opacity == 0.0

        settings.is_rest_day.return_value = True
        screen._refresh_status()
        assert screen._rest_card.opacity == 1.0
        assert screen._period_cards["morning"].opacity == 0.0

    def test_determine_current_period_does_not_expand_cards_during_rest(self) -> None:
        """防御性回归(照拍摄日的坑): 休息期内不应展开任何时段卡内容区,
        避免残留的可点击区域挡住下方(即使当前休息卡没有按钮, 也不该有
        隐藏但仍占用坐标的展开卡片)。"""
        get_clock().set_date_and_time("2026-06-07", "08:00")
        screen, _, _, _ = _make_screen(is_resting=True)
        morning = screen._period_cards["morning"]
        assert morning.height == 0
