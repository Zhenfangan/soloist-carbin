"""RestDaysDialog — 对赌周期结算完成后询问"休息几天"的弹窗。"""
from __future__ import annotations

from app.ui.components.rest_days_dialog import RestDaysDialog


def test_create_dialog_prefills_default_days() -> None:
    dialog = RestDaysDialog()
    assert dialog is not None
    assert dialog._days_stepper.value >= 1


def test_stepper_min_value_is_one() -> None:
    """休息天数不能低于 1(至少休一天)。"""
    dialog = RestDaysDialog()
    stepper = dialog._days_stepper
    for _ in range(10):
        stepper._decrement()
    assert stepper.value >= 1


def test_confirm_invokes_callback_with_days() -> None:
    results: list[int] = []
    dialog = RestDaysDialog(on_confirm=lambda days: results.append(days))
    dialog._days_stepper.value = 3
    dialog._handle_confirm()
    assert results == [3]


def test_skip_invokes_callback_with_none() -> None:
    """点"不休息"跳过 —— 回调收到 None, 不进入休息期。"""
    results: list[int | None] = []
    dialog = RestDaysDialog(on_confirm=lambda days: results.append(days))
    dialog._handle_skip()
    assert results == [None]
