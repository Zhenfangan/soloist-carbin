"""PeriodCard completed 状态下隐藏 _action_btn 大黄块。"""

from __future__ import annotations

from app.ui.components.period_card import PeriodCard


def test_completed_state_hides_action_btn() -> None:
    """已签退后 _action_btn 应该 opacity=0 + disabled + height=0。"""
    card = PeriodCard(period_name="evening")
    card._has_checked_in = True
    card._has_checked_out = True
    card._card_state = "completed"

    card._update_display()

    assert card._action_btn.opacity == 0, "已签退后按钮应该不可见 (opacity=0)"
    assert card._action_btn.disabled is True, "已签退后按钮应该 disabled"
    assert card._action_btn.height == 0, "已签退后按钮应该 height=0"


def test_pending_state_shows_action_btn() -> None:
    """未签到状态按钮可见。"""
    card = PeriodCard(period_name="morning", is_current=True)
    card._has_checked_in = False
    card._has_checked_out = False

    card._update_display()

    assert card._action_btn.opacity == 1, "未签到时按钮应可见"
    assert card._action_btn.disabled is False, "当前时段按钮可点击"


def test_checked_in_state_shows_checkout_btn() -> None:
    """已签到未签退状态显示签退按钮。"""
    card = PeriodCard(period_name="morning")
    card._has_checked_in = True
    card._has_checked_out = False

    card._update_display()

    assert card._action_btn.opacity == 1, "已签到时签退按钮可见"
    assert card._action_btn.text == "签退"


def test_state_transition_completed_to_pending_restores_button() -> None:
    """已签退状态后重置回未签到, 按钮应恢复可见。"""
    card = PeriodCard(period_name="morning", is_current=True)

    # 先模拟已签退
    card._has_checked_in = True
    card._has_checked_out = True
    card._update_display()
    assert card._action_btn.opacity == 0
    assert card._action_btn.height == 0

    # 切回未签到
    card._has_checked_in = False
    card._has_checked_out = False
    card._update_display()
    assert card._action_btn.opacity == 1, "重置后按钮应恢复可见"
    assert card._action_btn.height == 64, "重置后按钮高度应恢复"
    assert card._action_btn.disabled is False, "当前时段按钮应可点击"
