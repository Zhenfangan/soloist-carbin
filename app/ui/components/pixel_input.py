"""PixelInput — 像素内凹输入框。

2px 边框、直角、内凹样式 (暗面在顶部+左侧)。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kivy.graphics import Color, Rectangle
from kivy.uix.textinput import TextInput

from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_PADDING,
    CARD_WHITE,
    COLORS,
    FONT_SIZE_BODY,
    TEXT_BROWN,
    TEXT_GRAY,
)


class PixelInput(TextInput):  # type: ignore[misc]
    """像素内凹输入框。

    属性:
        hint_text: 占位提示文字
        value: 当前文本 (与 text 同义)
        password: 是否密码遮蔽
        on_change: 文本变化回调
    """

    def __init__(
        self,
        hint_text: str = "",
        value: str = "",
        password: bool = False,
        on_change: Callable[[str], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(text=value, password=password, **kwargs)
        self.hint_text = hint_text
        self._on_change_cb = on_change

        # 关键修复: 不再把 background_color 置透明
        # 改成让 TextInput 用纯色背景, PixelInput 只在 canvas.before 画边框
        self.background_normal = ""  # 不要图片背景
        self.background_active = ""
        self.background_color = self._to_rgba(CARD_WHITE)  # 用纯色做背景
        self.foreground_color = self._to_rgba(TEXT_BROWN)
        self.hint_text_color = self._to_rgba(TEXT_GRAY)
        self.cursor_color = self._to_rgba(TEXT_BROWN)
        self.font_size = FONT_SIZE_BODY
        self.padding = [CARD_PADDING // 2, CARD_PADDING // 2, CARD_PADDING // 2, CARD_PADDING // 2]
        self.multiline = False

        # 内凹边框色
        self._border_light = CARD_WHITE
        self._border_dark = COLORS["CARD_SHADOW"]

        self.bind(text=self._on_text_change)
        self.bind(pos=self._redraw, size=self._redraw)

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    @property
    def value(self) -> str:
        return self.text

    @value.setter
    def value(self, v: str) -> None:
        self.text = v

    def _on_text_change(self, instance: Any, text: str) -> None:
        if self._on_change_cb:
            self._on_change_cb(text)

    def _redraw(self, *args: Any) -> None:
        """只画 2px 内凹边框, 不画整面背景(避免盖住 TextInput 文字层)。"""
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        bw = BORDER_WIDTH

        with self.canvas.before:
            # 暗面 top
            Color(*self._to_rgba(self._border_dark))
            Rectangle(pos=(x, y + h - bw), size=(w, bw))
            # 暗面 left
            Rectangle(pos=(x, y), size=(bw, h))
            # 亮面 bottom
            Color(*self._to_rgba(self._border_light))
            Rectangle(pos=(x, y), size=(w, bw))
            # 亮面 right
            Rectangle(pos=(x + w - bw, y), size=(bw, h))
