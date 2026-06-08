"""PixelInput 渲染回归测试 — 防止 _redraw 覆盖 TextInput 文字层。"""

from __future__ import annotations

import pytest
from kivy.graphics import Rectangle

from app.ui.components.pixel_input import PixelInput
from app.ui.tokens import CARD_WHITE


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
