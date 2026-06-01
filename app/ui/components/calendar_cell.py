"""CalendarCell — 月视图日期格子。

12×12 dp 色块，颜色映射功能语义色:
  绿=全天正常, 黄=有迟到早退, 红=旷工, 蓝=请假, 橙=拍摄日
  非工作日显示团团图标, 未来日期显示 ○
"""

from __future__ import annotations

from typing import Any

from kivy.graphics import Color, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

from app.ui.tokens import (
    BORDER_WIDTH,
    COLORS,
    FONT_SIZE_SMALL,
    TEXT_BROWN,
    TEXT_GRAY,
)

# 日历颜色映射
CALENDAR_COLORS: dict[str, str] = {
    "normal": "#50E8B0",      # 绿 — mint light
    "late": "#FFE030",        # 黄 — primary yellow
    "absent": "#FF5070",      # 红 — watermelon light
    "leave": "#60C8FF",       # 蓝 — sky light
    "shooting": "#FF9040",    # 橙 — warm orange light
    "rest": "#E0E0E0",        # 灰 — 非工作日
    "future": "#F0F0F0",      # 浅灰 — 未来日期
}


class CalendarCell(FloatLayout):  # type: ignore[misc]
    """月视图日期色块格子。

    属性:
        day: 日期号 (1-31)
        status: 状态标识 ('normal'/'late'/'absent'/'leave'/'shooting'/'rest'/'future')
        is_work_day: 是否为工作日
    """

    def __init__(
        self,
        day: int,
        status: str = "future",
        is_work_day: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            size_hint=(None, None),
            **kwargs,
        )
        self._day = day
        self._status = status
        self._is_work_day = is_work_day

        self.size = (36, 36)

        # 日期数字
        display_text = str(day)
        self._label = Label(
            text=display_text,
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, 1),
            halign="center",
            valign="middle",
        )
        self.add_widget(self._label)

        self.bind(pos=self._redraw, size=self._redraw)
        # 立即更新 label 文本
        self._update_label_text()

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (
            int(h[0:2], 16) / 255.0,
            int(h[2:4], 16) / 255.0,
            int(h[4:6], 16) / 255.0,
            alpha,
        )

    def _update_label_text(self) -> None:
        """根据状态更新 label 文本和颜色。"""
        if self._status == "future":
            self._label.text = "○"
            self._label.color = self._to_rgba(TEXT_GRAY)
        elif not self._is_work_day:
            self._label.text = "🐼"
            self._label.color = self._to_rgba(TEXT_BROWN)
        else:
            self._label.text = str(self._day)
            self._label.color = self._to_rgba(TEXT_BROWN)

    def _redraw(self, *args: Any) -> None:
        """绘制色块背景。"""
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        bw = BORDER_WIDTH

        bg_color = self._get_bg_color()

        with self.canvas.before:
            # 背景填充
            Color(*self._to_rgba(bg_color))
            Rectangle(pos=(x, y), size=(w, h))

            # 2px 边框
            Color(*self._to_rgba(TEXT_BROWN))
            # top
            Rectangle(pos=(x, y + h - bw), size=(w, bw))
            # bottom
            Rectangle(pos=(x, y), size=(w, bw))
            # left
            Rectangle(pos=(x, y), size=(bw, h))
            # right
            Rectangle(pos=(x + w - bw, y), size=(bw, h))

    def _get_bg_color(self) -> str:
        """根据状态获取背景色。"""
        return CALENDAR_COLORS.get(self._status, COLORS.get("CARD_WHITE", "#FFFFFF"))
