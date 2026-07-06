"""ShootingDayCard — 3 状态卡片(idle/active/done)的状态机 + 主按钮派发。"""

from __future__ import annotations

import pytest
from kivy.clock import Clock
from kivy.core.window import Window

from app.ui.components.shooting_day_card import ShootingDayCard
from app.ui.tokens import CARD_PADDING


def _layout(card: ShootingDayCard) -> None:
    """强制走一遍真实布局, 让 pos/size 解析出来(而非默认 0)。"""
    Window.size = (420, 750)
    card.pos = (16, 400)
    card.width = 388
    for _ in range(3):
        Clock.tick()


def test_idle_state_shows_set_button() -> None:
    card = ShootingDayCard()
    card.set_state("idle")
    assert "设为拍摄日" in card._primary_btn.text
    assert card._cancel_btn.opacity == 0


def test_visible_button_right_edge_aligns_with_card_padding() -> None:
    """真机反馈: "设为拍摄日"/三按钮右边缘和签到按钮对不齐。

    根因: 隐藏的 capture_btn/cancel_btn 只置 width=0, 仍留在 btn_row 里,
    BoxLayout 的 spacing 照样在"隐藏位"上计入间距, 挤占了可见按钮的宽度,
    导致右边缘比 card.right - CARD_PADDING 少了(隐藏个数 × GRID_UNIT)。
    """
    card = ShootingDayCard(size_hint=(1, None))
    _layout(card)
    expected_right = card.right - CARD_PADDING

    card.set_state("idle")
    for _ in range(3):
        Clock.tick()
    assert card._primary_btn.right == pytest.approx(expected_right)

    card.set_state("active", can_cancel=False)
    for _ in range(3):
        Clock.tick()
    assert card._capture_btn.right == pytest.approx(expected_right)

    card.set_state("active", can_cancel=True)
    for _ in range(3):
        Clock.tick()
    assert card._cancel_btn.right == pytest.approx(expected_right)


def test_active_state_shows_complete_and_cancel_within_window() -> None:
    card = ShootingDayCard()
    card.set_state("active", can_cancel=True)
    assert "完成拍摄" in card._primary_btn.text
    assert card._cancel_btn.opacity == 1


def test_active_state_outside_window_hides_cancel() -> None:
    card = ShootingDayCard()
    card.set_state("active", can_cancel=False)
    assert card._cancel_btn.opacity == 0


def test_done_state_shows_encouragement_no_button() -> None:
    """done 态不再有"查看战报"按钮(与底部大按钮重复), 改显一句鼓励语。"""
    card = ShootingDayCard()
    card.set_state("done")
    assert card._encourage_label.opacity == 1.0
    assert card._encourage_label.text != ""
    # 整排按钮在 done 态移出 btn_row
    assert card._primary_btn not in card._btn_row.children


def test_done_encouragement_prefers_user_custom() -> None:
    """"自己设置的"鼓励语: 用户在设置里自定义的优先于内置池。"""
    class FakeSettings:
        def get_user_encouragements(self) -> list[str]:
            return ["宝你今天超棒"]

    card = ShootingDayCard(settings_service=FakeSettings())
    card.set_state("done")
    assert card._encourage_label.text == "宝你今天超棒"


def test_done_encouragement_stable_across_refresh() -> None:
    """重复 set_state("done")(切 tab 刷新)不应每次换一句, 避免抖动。"""
    card = ShootingDayCard()
    card.set_state("done")
    first = card._encourage_label.text
    for _ in range(5):
        card.set_state("done")
    assert card._encourage_label.text == first


def test_primary_button_dispatches_by_state() -> None:
    calls: list[str] = []
    card = ShootingDayCard(
        on_set=lambda: calls.append("set"),
        on_complete=lambda: calls.append("complete"),
    )
    card.set_state("idle")
    card._on_primary()
    card.set_state("active")
    card._on_primary()
    card.set_state("done")
    card._on_primary()  # done 态无主按钮, 不派发
    assert calls == ["set", "complete"]


def test_cancel_button_invokes_callback() -> None:
    calls: list[str] = []
    card = ShootingDayCard(on_cancel=lambda: calls.append("cancel"))
    card.set_state("active", can_cancel=True)
    card._on_cancel_pressed()
    assert calls == ["cancel"]


def test_active_shows_cat_animation_and_capture_button() -> None:
    card = ShootingDayCard()
    base_h = card.height
    card.set_state("active", can_cancel=True)
    assert card._anim.frame_count == 7          # cat 序列
    assert card._anim_wrap.opacity == 1.0        # 动画区可见
    assert card._capture_btn.opacity == 1.0      # 拍张现场可见
    assert card.height > base_h                  # 面板加高容纳动画


def test_cat_animation_speed_matches_report_preview() -> None:
    """真机反馈: active 态小猫动画比战报里的动画明显快。

    仅对齐 fps 数字不够 —— 战报(report_preview.py `_start_frame_anim`)用
    fps=4.0 + bubble_indices={1,3,4}(停留 2 倍时长) + loop_pause=2.0(播完
    一轮暂停 2 秒), 整体节奏比匀速循环慢得多。ShootingDayCard 的
    SequenceSprite 必须传入完全相同的三个参数, 而不只是 fps。
    """
    card = ShootingDayCard()
    assert card._anim._interval == 0.25  # fps=4.0 <=> interval=1/4
    assert card._anim._bubble_indices == {1, 3, 4}
    assert card._anim._loop_pause == 2.0


def test_idle_hides_animation_and_capture() -> None:
    card = ShootingDayCard()
    card.set_state("active")
    active_h = card.height
    card.set_state("idle")
    assert card._anim_wrap.opacity == 0.0
    assert card._capture_btn.opacity == 0.0
    assert card.height < active_h                # 收回加高


def test_done_hides_animation_and_capture() -> None:
    card = ShootingDayCard()
    card.set_state("done")
    assert card._anim_wrap.opacity == 0.0
    assert card._capture_btn.opacity == 0.0


def test_capture_button_dispatches_callback() -> None:
    calls: list[str] = []
    card = ShootingDayCard(on_capture=lambda: calls.append("capture"))
    card.set_state("active")
    card._on_capture_pressed()
    assert calls == ["capture"]
