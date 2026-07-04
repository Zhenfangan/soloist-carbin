"""CalendarCell — 月视图日期格子。

正方形色块，按 CALENDAR_COLORS 映射 8 类当日状态语义色(见该常量注释)。
未来/无数据日期显示 ○，其余状态一律显示日期数字(靠底色+图例区分状态)。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kivy.graphics import Color, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

from app.ui.tokens import (
    BORDER_WIDTH,
    COLORS,
    FONT_SIZE_BODY,
    TEXT_BROWN,
    TEXT_GRAY,
)

# 日历颜色映射 — 语义状态名 → 色值(8 类当日状态, 与图例一一对应)
CALENDAR_COLORS: dict[str, str] = {
    "normal": "#46D6A0",       # 绿 — 全天正常
    "late": "#FFD21F",         # 黄 — 迟到
    "early_leave": "#FF9F40",  # 橙 — 早退
    "absent": "#FF5A78",       # 红 — 旷工
    "leave": "#5AB8FF",        # 蓝 — 请假
    "shooting": "#B87BEA",     # 紫 — 拍摄日
    "rest": "#C4CBD8",         # 灰蓝 — 休息日
    "future": "#EEEEEE",       # 浅灰 — 未来/无数据
    "empty": "#EEEEEE",        # 同 future(历史无数据)
}

# 每种状态的中文名(图例 + 无障碍用)
CALENDAR_STATUS_LABELS: dict[str, str] = {
    "normal": "正常",
    "late": "迟到",
    "early_leave": "早退",
    "absent": "旷工",
    "leave": "请假",
    "shooting": "拍摄",
    "rest": "休息",
    "future": "未来",
}

# 格子边长 —— 按 LOGICAL_WIDTH=420、CARD_PADDING 两侧、7 列 2px 间距反推:
# (420 - 2*8 - 6*2) / 7 = 56，让月历网格正好铺满整行宽度。
CELL_SIZE: int = 56


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
        on_press: Callable[[], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("size_hint", (None, None))
        super().__init__(**kwargs)
        self._day = day
        self._status = status
        self._is_work_day = is_work_day
        self._on_press = on_press

        self.size = (CELL_SIZE, CELL_SIZE)

        # 日期数字
        display_text = str(day)
        self._label = Label(
            text=display_text,
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, 1),
            # 根因修复: FloatLayout 子控件必须带 pos_hint, 否则停在窗口原点(0,0)
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            halign="center",
            valign="middle",
        )
        self._label.bind(size=lambda inst, _v: setattr(inst, "text_size", inst.size))
        self.add_widget(self._label)

        self.bind(pos=self._redraw, size=self._redraw)
        # 立即更新 label 文本
        self._update_label_text()

    def on_touch_down(self, touch: Any) -> bool:
        if self._on_press is not None and self.collide_point(*touch.pos):
            touch.grab(self)
            return True
        return bool(super().on_touch_down(touch))

    def on_touch_up(self, touch: Any) -> bool:
        if touch.grab_current is self:
            touch.ungrab(self)
            if self._on_press is not None and self.collide_point(*touch.pos):
                self._on_press()
            return True
        return bool(super().on_touch_up(touch))

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
        if self._status in ("future", "empty"):
            self._label.text = "○"
            self._label.color = self._to_rgba(TEXT_GRAY)
        else:
            # 彩色块上用深棕数字, 保证可读(rest 等状态靠底色区分, 不再用 "R")
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
