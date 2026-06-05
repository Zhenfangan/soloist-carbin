"""PixelStepper — 像素步进器。

[-] [数字] [+] 三段水平排列，按钮为 32×32 小方块。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from app.ui.tokens import (
    BORDER_WIDTH,
    COLORS,
    FONT_SIZE_BODY,
    GRID_UNIT,
    TEXT_BROWN,
)


class PixelStepper(BoxLayout):  # type: ignore[misc]
    """像素步进器。

    属性:
        value: 当前值
        min_value: 最小值 (默认 0)
        max_value: 最大值 (默认 99)
        step: 步长 (默认 1)
        on_change: 值变化回调 (value: int) -> None
    """

    def __init__(
        self,
        value: int = 0,
        min_value: int = 0,
        max_value: int = 99,
        step: int = 1,
        on_change: Callable[[int], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(orientation="horizontal", spacing=GRID_UNIT, **kwargs)
        self.size_hint = (None, None)
        self.height = 32
        self.width = 140

        self._value = value
        self._min = min_value
        self._max = max_value
        self._step = step
        self._on_change = on_change

        # [-] 按钮
        self._minus_btn = Button(
            text="-",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, 1),
            width=32,
        )
        self._minus_btn.bind(on_press=lambda _: self._decrement())

        # 数值标签
        self._value_label = Label(
            text=str(value),
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, 1),
            halign="center",
            valign="middle",
        )

        # [+] 按钮
        self._plus_btn = Button(
            text="+",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
            size_hint=(None, 1),
            width=32,
        )
        self._plus_btn.bind(on_press=lambda _: self._increment())

        self.add_widget(self._minus_btn)
        self.add_widget(self._value_label)
        self.add_widget(self._plus_btn)

        self.bind(pos=self._redraw, size=self._redraw)

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, v: int) -> None:
        self._value = max(self._min, min(self._max, v))
        self._value_label.text = str(self._value)

    @property
    def min_value(self) -> int:
        return self._min

    @property
    def max_value(self) -> int:
        return self._max

    def _increment(self) -> None:
        if self._value < self._max:
            self._value += self._step
            self._value_label.text = str(self._value)
            if self._on_change:
                self._on_change(self._value)

    def _decrement(self) -> None:
        if self._value > self._min:
            self._value -= self._step
            self._value_label.text = str(self._value)
            if self._on_change:
                self._on_change(self._value)

    def _redraw(self, *args: Any) -> None:
        """绘制按钮的像素边框。"""
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        bw = BORDER_WIDTH

        with self.canvas.before:
            # 整体背景
            Color(*self._to_rgba(COLORS["CARD_WHITE"]))
            Rectangle(pos=(x, y), size=(w, h))
            # 内凹边框
            Color(*self._to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(x, y + h - bw), size=(w, bw))
            Rectangle(pos=(x, y), size=(bw, h))
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(x, y), size=(w, bw))
            Rectangle(pos=(x + w - bw, y), size=(bw, h))
