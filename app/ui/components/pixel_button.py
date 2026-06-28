"""PixelButton — 像素 3D 凸起按钮。

2px 亮面+暗面伪 3D 边框，按下时明暗交换（凹陷效果）。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from kivy.graphics import Color, Rectangle
from kivy.uix.button import Button

from app.ui.tokens import (
    BORDER_WIDTH,
    BTN_HEIGHT,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    PRIMARY_DARK,
    PRIMARY_YELLOW,
    TEXT_BROWN,
)


class PixelButton(Button):  # type: ignore[misc]
    """像素 3D 凸起按钮。

    属性:
        text: 按钮文字
        color: 主色 (hex 字符串，默认明黄)
        on_press: 点击回调
        disabled: 是否禁用
        size_mode: 'normal' (48px) / 'large' (64px) / 'small' (36px)
    """

    def __init__(
        self,
        text: str = "",
        color: str = PRIMARY_YELLOW,
        on_press: Callable[[], Any] | None = None,
        disabled: bool = False,
        size_mode: str = "normal",
        **kwargs: Any,
    ) -> None:
        super().__init__(text=text, **kwargs)
        self._btn_color = color
        self._dark_color = self._compute_dark(color)
        self._light_color = self._compute_light(color)
        self._size_mode = size_mode
        self._is_pressed = False

        # 尺寸
        heights = {"normal": BTN_HEIGHT, "large": 64, "small": 36}
        self.height = heights.get(size_mode, BTN_HEIGHT)
        self.size_hint_y = None

        # 外观
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)  # 透明底，用 canvas 画
        self.color = self._to_rgba(TEXT_BROWN)
        self.disabled_color = self._to_rgba(TEXT_BROWN)
        if size_mode == "large":
            self.font_size = FONT_SIZE_TITLE
        elif size_mode == "small":
            self.font_size = FONT_SIZE_SMALL
        else:
            self.font_size = FONT_SIZE_BODY
        self.disabled = disabled
        self.opacity = 1.0 if not disabled else 0.5

        # 回调
        if on_press:
            self.bind(on_press=lambda _: on_press())

        # 绑定绘制
        self.bind(pos=self._redraw, size=self._redraw)

    def _compute_dark(self, hex_color: str) -> str:
        """根据主色自动计算暗面色 (降低亮度约 15%)。"""
        return PRIMARY_DARK if hex_color == PRIMARY_YELLOW else self._adjust_brightness(hex_color, -40)

    def _compute_light(self, hex_color: str) -> str:
        """根据主色自动计算亮面色 (提高亮度)。"""
        if hex_color == PRIMARY_YELLOW:
            return "#FFF8A0"
        return self._adjust_brightness(hex_color, 40)

    @staticmethod
    def _adjust_brightness(hex_color: str, delta: int) -> str:
        """调整 hex 颜色亮度，delta 加在 RGB 每通道上。"""
        h = hex_color.lstrip("#")
        r = max(0, min(255, int(h[0:2], 16) + delta))
        g = max(0, min(255, int(h[2:4], 16) + delta))
        b = max(0, min(255, int(h[4:6], 16) + delta))
        return f"#{r:02X}{g:02X}{b:02X}"

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    def on_touch_down(self, touch: Any) -> bool:
        if self.disabled:
            return False
        if self.collide_point(*touch.pos):
            self._is_pressed = True
            self._redraw()
        return cast(bool, super().on_touch_down(touch))

    def on_touch_up(self, touch: Any) -> bool:
        if self._is_pressed:
            self._is_pressed = False
            self._redraw()
        return cast(bool, super().on_touch_up(touch))

    def _redraw(self, *args: Any) -> None:
        """重绘像素边框。凸起=亮面 top+left，按下=明暗互换(凹陷)。"""
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        bw = BORDER_WIDTH

        with self.canvas.before:
            if self._is_pressed:
                # 凹陷: 暗面 top+left, 亮面 bottom+right
                light = self._light_color
                dark = self._dark_color
                # 暗面 top
                Color(*self._to_rgba(dark))
                Rectangle(pos=(x, y + h - bw), size=(w, bw))
                # 暗面 left
                Rectangle(pos=(x, y), size=(bw, h))
                # 亮面 bottom
                Color(*self._to_rgba(light))
                Rectangle(pos=(x, y), size=(w, bw))
                # 亮面 right
                Rectangle(pos=(x + w - bw, y), size=(bw, h))
            else:
                # 凸起: 亮面 top+left, 暗面 bottom+right
                light = self._light_color
                dark = self._dark_color
                # 亮面 top
                Color(*self._to_rgba(light))
                Rectangle(pos=(x, y + h - bw), size=(w, bw))
                # 亮面 left
                Rectangle(pos=(x, y), size=(bw, h))
                # 暗面 bottom
                Color(*self._to_rgba(dark))
                Rectangle(pos=(x, y), size=(w, bw))
                # 暗面 right
                Rectangle(pos=(x + w - bw, y), size=(bw, h))

            # 背景填充
            Color(*self._to_rgba(self._btn_color))
            Rectangle(pos=(x + bw, y + bw), size=(w - 2 * bw, h - 2 * bw))

    def set_color(self, color: str) -> None:
        """动态更换按钮颜色。"""
        self._btn_color = color
        self._dark_color = self._compute_dark(color)
        self._light_color = self._compute_light(color)
        self._redraw()
