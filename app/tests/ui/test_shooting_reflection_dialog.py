"""ShootingReflectionDialog — 4 字段复盘 + 3 选 1 顺利度 的答案收集逻辑。"""

from __future__ import annotations

from app.ui.components.shooting_reflection_dialog import ShootingReflectionDialog


def test_default_smoothness_is_normal() -> None:
    dlg = ShootingReflectionDialog()
    assert dlg._smoothness == "normal"


def test_select_smoothness_updates_state() -> None:
    dlg = ShootingReflectionDialog()
    dlg._select_smoothness("rough")
    assert dlg._smoothness == "rough"
    dlg._select_smoothness("smooth")
    assert dlg._smoothness == "smooth"


def test_submit_collects_all_answers() -> None:
    captured: dict[str, str] = {}
    dlg = ShootingReflectionDialog(on_submit=lambda ans: captured.update(ans))
    dlg._content_input.text = "宣传片"
    dlg._location_input.text = "创意园"
    dlg._thoughts_input.text = "光线很好"
    dlg._select_smoothness("smooth")
    dlg._handle_submit()
    assert captured == {
        "content": "宣传片",
        "location": "创意园",
        "smoothness": "smooth",
        "thoughts": "光线很好",
    }
