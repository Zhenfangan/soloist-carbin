"""PixelCheckbox — 像素勾选框。

4×4 像素风格勾选框，选中时显示勾号 ✓。
用于任务列表等场景。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from kivy.graphics import Color, Line
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from app.ui.tokens import (
    BORDER_WIDTH,
    FONT_SIZE_BODY,
    GRID_UNIT,
    TEXT_BROWN,
    TEXT_GRAY,
)


class PixelCheckbox(FloatLayout):  # type: ignore[misc]
    """像素勾选框。

    属性:
        checked: 是否勾选
        label: 勾选框旁的文字
        on_toggle: 状态切换回调 (checked: bool) -> None
    """

    def __init__(
        self,
        checked: bool = False,
        label: str = "",
        on_toggle: Callable[[bool], Any] | None = None,
        on_label_tap: Callable[[], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.size_hint = (1, None)
        self.height = 32

        self._checked = checked
        self._label_text = label
        self._on_toggle = on_toggle
        self._on_label_tap = on_label_tap

        # 勾选框画布区域
        self._box = Widget(
            size_hint=(None, None),
            size=(20, 20),
            pos_hint={"x": 0, "y": 0.5},
        )

        # 文字标签 — markup 支持 [s]...[/s] 删除线
        self._label = Label(
            text=self._format_label_text(),
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_GRAY if checked else TEXT_BROWN),
            size_hint=(1, 1),
            halign="left",
            valign="middle",
            markup=True,
        )

        self.add_widget(self._box)
        self.add_widget(self._label)

        self.bind(pos=self._redraw, size=self._redraw)

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    @property
    def checked(self) -> bool:
        return self._checked

    @checked.setter
    def checked(self, value: bool) -> None:
        self._checked = value
        self._sync_label_style()
        self._redraw()

    def toggle(self) -> None:
        """切换勾选状态。"""
        self._checked = not self._checked
        self._sync_label_style()
        self._redraw()
        if self._on_toggle:
            self._on_toggle(self._checked)

    def _format_label_text(self) -> str:
        """打钩后文字加删除线 (Kivy markup)。"""
        if self._checked and self._label_text:
            return f"[s]{self._label_text}[/s]"
        return self._label_text

    def _sync_label_style(self) -> None:
        """同步标签文本与颜色 — 打钩后变灰 + 删除线。"""
        self._label.text = self._format_label_text()
        self._label.color = self._to_rgba(TEXT_GRAY if self._checked else TEXT_BROWN)

    def on_touch_down(self, touch: Any) -> bool:
        if self.collide_point(*touch.pos):
            if self._on_label_tap:
                # 仅勾选框矩形区域触发 toggle，其余区域打开操作菜单
                box_x = self.x + GRID_UNIT
                box_y = self.y + (self.height - 20) / 2
                if box_x <= touch.x <= box_x + 20 and box_y <= touch.y <= box_y + 20:
                    self.toggle()
                else:
                    self._on_label_tap()
            else:
                self.toggle()
            return True
        return cast(bool, super().on_touch_down(touch))

    def _redraw(self, *args: Any) -> None:
        """绘制像素勾选框 — Kivy canvas 用绝对窗口坐标, 必须加 self.x/self.y 偏移。"""
        self.canvas.before.clear()
        bw = BORDER_WIDTH
        box_size = 20
        box_x = self.x + GRID_UNIT
        box_y = self.y + (self.height - box_size) / 2

        with self.canvas.before:
            Color(*self._to_rgba(TEXT_BROWN))
            Line(rectangle=(box_x, box_y, box_size, box_size), width=bw)

            if self._checked:
                Color(*self._to_rgba("#50E8B0"))
                Line(points=[
                    box_x + 4, box_y + 10,
                    box_x + 8, box_y + 6,
                    box_x + 16, box_y + 14,
                ], width=2)

        # 标签位置同样需要绝对坐标
        self._label.pos = (box_x + box_size + GRID_UNIT, self.y)
        self._label.size = (self.width - (box_x - self.x) - box_size - GRID_UNIT, self.height)
