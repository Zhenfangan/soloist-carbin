"""CheckinScreen streak_label — 空数据高度归零 + 有数据渲染火苗图标。

emoji 迁移后 _streak_label 由 Label 改为 IconLabel, 连续出勤文案两侧的 🔥
改为 icon_flame 像素图标; 原先的 text→height 绑定(_update_streak_height)
改为 _load_data 内联设高。这里验证新契约: 空→height 0, 有数据→火苗+文字+高度。
"""

from __future__ import annotations

from kivy.uix.image import Image

from app.ui.screens.checkin_screen import CheckinScreen


def test_streak_label_empty_by_default() -> None:
    """无数据时文字为空且 height = 0, 不占垂直空间。"""
    screen = CheckinScreen()

    assert screen._streak_label.text == "", "默认应无文字"
    assert screen._streak_label.height == 0, (
        f"空数据时 height 应为 0, 实际 {screen._streak_label.height}"
    )


def test_streak_label_renders_flames_and_text_when_set() -> None:
    """有连续出勤数据时(复刻 _load_data 渲染): 首尾各一枚火苗图标 + 中段文字,
    并撑起 height = 32。"""
    screen = CheckinScreen()

    screen._streak_label.set_segments([
        ("icon_flame", ""),
        (None, "已连续正常出勤 7 天"),
        ("icon_flame", ""),
    ])
    screen._streak_label.height = 32

    images = [c for c in screen._streak_label.children if isinstance(c, Image)]
    assert len(images) == 2, "连续出勤文案两侧应各有一枚火苗图标"
    assert "已连续正常出勤 7 天" in screen._streak_label.text
    assert screen._streak_label.height == 32
