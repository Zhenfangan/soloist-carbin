"""PeriodCard disabled 时应放行触摸(而非 Kivy 默认的 disabled+collide 即吞掉)。

背景: PeriodCard 是普通 BoxLayout, 没有像 PixelButton 那样在 disabled 时
主动放行触摸。checkin_screen.py 隐藏时段卡时只改 opacity/height/disabled,
若卡片内部仍有未同步收起的固定高度子控件(_header/_content_area 等),
Kivy 默认 on_touch_down (disabled 且 collide 就直接 return True, 不检查
子节点) 会让这张"已隐藏"的卡片吞掉本该穿透给下方 ShootingDayCard 按钮的
触摸。给 PeriodCard 补上和 PixelButton 一致的 disabled 放行语义, 从组件
层面根治, 而不是逐个修内部子控件的几何。
"""

from __future__ import annotations

from kivy.core.window import Window
from kivy.tests.common import UnitTestTouch

from app.ui.components.period_card import PeriodCard


def _touch_at(x: float, y: float) -> UnitTestTouch:
    touch = UnitTestTouch(x, y)
    touch.scale_for_screen(*Window.size)
    touch.eventloop = None
    return touch


def test_disabled_card_passes_touch_through() -> None:
    card = PeriodCard(period_name="morning")
    card.pos = (0, 0)
    card.size = (300, 180)
    card.disabled = True

    touch = _touch_at(*card.center)
    result = card.dispatch("on_touch_down", touch)

    assert not result, "disabled 的 PeriodCard 不应吞掉触摸(应放行给下方控件)"


def test_enabled_card_still_handles_action_button_touch() -> None:
    """放行修复不能破坏正常(未 disabled)时签到按钮本身的点击。"""
    calls: list[str] = []
    card = PeriodCard(period_name="morning", is_current=True, on_checkin=calls.append)
    card.pos = (0, 0)
    card.size = (300, card._EXPANDED_HEIGHT)
    card.card_state = "expanded"

    btn = card._action_btn
    touch = _touch_at(*btn.to_window(*btn.center))
    card.dispatch("on_touch_down", touch)
    card.dispatch("on_touch_up", touch)

    assert calls == ["morning"]
