"""RestDayCard — 休息日签到页展示卡(今日休息 + 小兔动画, 无其他按钮)。"""
from __future__ import annotations

from app.ui.components.rest_day_card import RestDayCard


def test_shows_rest_hint_and_rabbit_animation() -> None:
    card = RestDayCard()
    assert "休息" in card._hint_label.text
    assert card._anim.frame_count == 7  # rabbit 序列


def test_animation_autoplays() -> None:
    card = RestDayCard()
    assert card._anim.is_playing is True


def test_no_action_buttons() -> None:
    """休息日卡片只做展示, 不应含任何可点击按钮(用户明确要求"其他都不显示")。"""
    from app.ui.components.pixel_button import PixelButton

    def _find(widget: object, cls: type) -> list:
        out: list = []
        if isinstance(widget, cls):
            out.append(widget)
        for child in getattr(widget, "children", []):
            out.extend(_find(child, cls))
        return out

    card = RestDayCard()
    assert _find(card, PixelButton) == []


def test_set_animation_inactive_stops_sprite() -> None:
    """休息卡隐藏时(非休息日)必须暂停精灵, 否则空转 Clock 帧循环耗电+可能
    与其它动画叠加卡顿(真机已复现: 切 tab 回来循环播放小兔)。"""
    card = RestDayCard()
    card.set_animation_active(False)
    assert not card._anim.is_playing


def test_set_animation_active_resumes_sprite() -> None:
    card = RestDayCard()
    card.set_animation_active(False)
    card.set_animation_active(True)
    assert card._anim.is_playing


def test_toggle_is_idempotent() -> None:
    """重复设同一状态不报错、不叠加事件。"""
    card = RestDayCard()
    card.set_animation_active(True)
    card.set_animation_active(True)
    assert card._anim.is_playing
    card.set_animation_active(False)
    card.set_animation_active(False)
    assert not card._anim.is_playing
