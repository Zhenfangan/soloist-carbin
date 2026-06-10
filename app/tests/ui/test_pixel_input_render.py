"""PixelInput 渲染回归测试 — 防止 _redraw 覆盖 TextInput 文字层。

设计意图: 不操作 canvas.before, 保留 Kivy TextInput 自身的背景/文字渲染管线;
边框画到 canvas.after 叠加在文字层之上 (仅 2px 边框, 不遮挡文字区)。
"""

from __future__ import annotations

import pytest
from kivy.graphics import Rectangle

from app.ui.components.pixel_input import PixelInput


@pytest.fixture
def pi() -> PixelInput:
    p = PixelInput(hint_text="测试 hint")
    p.size = (200, 40)
    p.pos = (0, 0)
    p._redraw()
    return p


def test_canvas_before_has_no_full_fill_rect(pi: PixelInput) -> None:
    """canvas.before 不应该画一个覆盖整面的填充矩形(那会盖住 TextInput 文字)。"""
    full_fills = [
        c for c in pi.canvas.before.children
        if isinstance(c, Rectangle)
        and c.size == (200, 40)
        and c.pos == (0, 0)
    ]
    assert len(full_fills) == 0, (
        f"canvas.before 仍有 {len(full_fills)} 个整面填充矩形, "
        "会覆盖 TextInput 文字层"
    )


def test_text_property_reflects_input(pi: PixelInput) -> None:
    """输入文本应该正确写入 .text 与 .value。"""
    pi.text = "hello"
    assert pi.text == "hello"
    assert pi.value == "hello"


def test_hint_text_is_set(pi: PixelInput) -> None:
    """hint_text 应该正确赋值给 TextInput 的 hint_text。"""
    assert pi.hint_text == "测试 hint"


def test_canvas_after_has_4_border_rectangles(pi: PixelInput) -> None:
    """canvas.after 应有 4 个边框 Rectangle (top/left 暗面 + bottom/right 亮面)。

    边框走 canvas.after 是为了不破坏 TextInput 默认背景/文字渲染管线 —
    文字仍由 Kivy 自身 pipeline 绘制在 canvas.before 与 canvas 中间层,
    canvas.after 仅叠加 2px 边框, 不会遮挡文字。
    """
    rects = [c for c in pi.canvas.after.children if isinstance(c, Rectangle)]
    assert len(rects) == 4, (
        f"canvas.after 应有 4 个边框 Rectangle, 实际找到 {len(rects)} 个"
    )


def test_textinput_default_background_preserved(pi: PixelInput) -> None:
    """不清空 canvas.before — 保留 Kivy TextInput 的默认 BorderImage 背景。"""
    # 新方案使用默认 background_color 而非透明; background_normal 不应被置空
    # 否则 TextInput 内部 cursor/text layout 坐标会出错
    assert pi.background_color == [1, 1, 1, 1] or pi.background_color == (1, 1, 1, 1)
    # canvas.before 至少有 Kivy 默认指令 (BorderImage 或 Color), 不为空
    assert len(pi.canvas.before.children) > 0, (
        "canvas.before 应保留 Kivy TextInput 默认渲染指令, 不能被清空"
    )
