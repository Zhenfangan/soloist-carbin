"""CheckinScreen streak_label 空数据时高度归零测试。"""

from __future__ import annotations

from app.ui.screens.checkin_screen import CheckinScreen


def test_streak_label_height_zero_when_text_empty() -> None:
    """text 为空时 height = 0, 不占垂直空间。"""
    screen = CheckinScreen()

    # 默认初始无数据
    assert screen._streak_label.text == "", "默认 text 应为空"
    assert screen._streak_label.height == 0, (
        f"空 text 时 height 应为 0, 实际 {screen._streak_label.height}"
    )


def test_streak_label_height_restored_when_text_set() -> None:
    """设置非空 text 后 height 应恢复到 20。"""
    screen = CheckinScreen()

    screen._streak_label.text = "连续出勤 7 天"
    # 触发 height 更新
    if hasattr(screen, "_update_streak_height"):
        screen._update_streak_height()

    assert screen._streak_label.height == 20, (
        f"非空 text 时 height 应为 20, 实际 {screen._streak_label.height}"
    )
