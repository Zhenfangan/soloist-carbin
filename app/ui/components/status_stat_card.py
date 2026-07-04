"""StatusStatCard — 月历"各状态统计"卡片。

一个状态类型一张卡: 玻璃框(与 CycleBar/MonthCard 统一) + 左侧色块与状态
文字(原本独立图例的内容并入卡片) + 中部像素点 bar(按当月天数) + 右侧计数。
当月没出现过的状态由调用方(history_screen)跳过, 本组件不做零值判断。
"""

from __future__ import annotations

from typing import Any

from kivy.graphics import Color, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

from app.ui.components.calendar_cell import CALENDAR_COLORS, CALENDAR_STATUS_LABELS
from app.ui.components.glass_bg import draw_glass_card_bg
from app.ui.components.pixel_dot_bar import calc_dot_geom
from app.ui.tokens import (
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    GRID_UNIT,
    TEXT_BROWN,
)

_DOT_H = 14
_CARD_HEIGHT = 52
_SWATCH_SIZE = 16


class StatusStatCard(FloatLayout):  # type: ignore[misc]
    """单个状态类型的当月天数统计卡 —— 玻璃框 + 图例 + 点 bar + 计数。"""

    def __init__(self, status: str, count: int, **kwargs: Any) -> None:
        super().__init__(
            size_hint=(1, None),
            height=_CARD_HEIGHT,
            **kwargs,
        )
        self._status = status
        self._count = count

        self._label = Label(
            text=CALENDAR_STATUS_LABELS.get(status, status),
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, None),
            size=(70, 24),
            halign="left",
            valign="middle",
        )

        self._count_label = Label(
            text=f"{count} 天",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, None),
            size=(50, 24),
            halign="right",
            valign="middle",
        )

        self.add_widget(self._label)
        self.add_widget(self._count_label)

        self.bind(pos=self._redraw, size=self._redraw)

    def _dot_color(self) -> str:
        return CALENDAR_COLORS.get(self._status, "#CCCCCC")

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0,
                int(h[4:6], 16) / 255.0, alpha)

    def _redraw(self, *args: Any) -> None:
        """绘制玻璃卡片背景 + 色块 + 像素点 bar。"""
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        pad = GRID_UNIT

        draw_glass_card_bg(self, border_light=TEXT_BROWN, border_dark=TEXT_BROWN, inset=2)

        swatch_x = x + pad
        swatch_y = y + (h - _SWATCH_SIZE) / 2
        label_x = swatch_x + _SWATCH_SIZE + 6

        # 点 bar 区域: 图例(色块+文字, 共 70+16+6=~92px)与右侧计数(50px)之间
        bar_x = label_x + 70 + 10
        bar_area_w = w - pad * 2 - (bar_x - x) - 50 - 6
        bar_y = y + (h - _DOT_H) / 2

        with self.canvas.before:
            # 图例色块(原独立图例的内容, 现并入卡片)
            Color(*self._to_rgba(self._dot_color()))
            Rectangle(pos=(swatch_x, swatch_y), size=(_SWATCH_SIZE, _SWATCH_SIZE))

            # 像素点 bar —— count 个点, 颜色即该状态色
            if self._count > 0 and bar_area_w > 10:
                dot_w, dot_h, gap = calc_dot_geom(bar_area_w, self._count)
                dot_y = bar_y + (_DOT_H - dot_h) / 2
                Color(*self._to_rgba(self._dot_color()))
                for i in range(self._count):
                    dx = bar_x + i * (dot_w + gap)
                    Rectangle(pos=(dx, dot_y), size=(dot_w, dot_h))

        self._label.pos = (label_x, y + h / 2 - 12)
        self._count_label.pos = (x + w - pad - 50, y + h / 2 - 12)
