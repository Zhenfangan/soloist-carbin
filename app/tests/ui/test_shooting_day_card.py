"""ShootingDayCard — 3 状态卡片(idle/active/done)的状态机 + 主按钮派发。"""

from __future__ import annotations

from app.ui.components.shooting_day_card import ShootingDayCard


def test_idle_state_shows_set_button() -> None:
    card = ShootingDayCard()
    card.set_state("idle")
    assert "设为拍摄日" in card._primary_btn.text
    assert card._cancel_btn.opacity == 0


def test_active_state_shows_complete_and_cancel_within_window() -> None:
    card = ShootingDayCard()
    card.set_state("active", can_cancel=True)
    assert "完成拍摄" in card._primary_btn.text
    assert card._cancel_btn.opacity == 1


def test_active_state_outside_window_hides_cancel() -> None:
    card = ShootingDayCard()
    card.set_state("active", can_cancel=False)
    assert card._cancel_btn.opacity == 0


def test_done_state_shows_view_report() -> None:
    card = ShootingDayCard()
    card.set_state("done")
    assert "战报" in card._primary_btn.text


def test_primary_button_dispatches_by_state() -> None:
    calls: list[str] = []
    card = ShootingDayCard(
        on_set=lambda: calls.append("set"),
        on_complete=lambda: calls.append("complete"),
        on_view_report=lambda: calls.append("report"),
    )
    card.set_state("idle")
    card._on_primary()
    card.set_state("active")
    card._on_primary()
    card.set_state("done")
    card._on_primary()
    assert calls == ["set", "complete", "report"]


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
