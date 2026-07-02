"""CycleBar — 对赌周期历史条（像素点风格）。

每条周期显示为像素点进度条：绿色方块=正常周，红色方块=滞纳天。
方块间留空隙，像 Claude Code 终端进度条一样的小点点像素风。
右侧显示金额汇总。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from kivy.graphics import Color, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

from app.models.history import CycleSummary
from app.ui.components.glass_bg import draw_glass_card_bg
from app.ui.tokens import (
    DOPAMINE_COLORS,
    FONT_SIZE_BODY,
    GRID_UNIT,
    TEXT_BROWN,
    TEXT_GRAY,
)

# 周期条配色
_CYCLE_GREEN = DOPAMINE_COLORS["mint"]["light"]   # 正常周期
_CYCLE_GREEN_DARK = DOPAMINE_COLORS["mint"]["dark"]
_CYCLE_RED = DOPAMINE_COLORS["coral"]["light"]     # 滞纳期
_CYCLE_RED_DARK = DOPAMINE_COLORS["coral"]["dark"]
_DOT_W = 10             # 像素点宽度
_DOT_H = 14             # 像素点高度
_DOT_GAP = 3            # 点间距
_CARD_HEIGHT = 88       # 卡片总高


class CycleBar(FloatLayout):  # type: ignore[misc]
    """单条周期历史卡片 — 像素点进度条风格。

    布局: [日期范围] | [▪▪▪▪▪▪▪ ◦◦◦] | [金额]
    """

    def __init__(self, cycle: CycleSummary, **kwargs: Any) -> None:
        super().__init__(
            size_hint=(1, None),
            height=_CARD_HEIGHT,
            **kwargs,
        )
        self._cycle = cycle

        # 日期范围标签 (左)
        self._date_label = Label(
            text=self._fmt_date(),
            font_size=13,
            color=self._to_rgba(TEXT_GRAY),
            size_hint=(None, None),
            size=(140, 24),
            halign="left",
            valign="middle",
        )

        # 任务完成标签 (日期下方)
        total = cycle.total_tasks
        done = cycle.completed_tasks
        self._task_label = Label(
            text=f"任务 {done}/{total}" if total > 0 else "无任务",
            font_size=12,
            color=self._to_rgba(TEXT_GRAY),
            size_hint=(None, None),
            size=(140, 22),
            halign="left",
            valign="middle",
        )

        # 金额标签 (右)
        net = cycle.net
        sign = "+" if net >= 0 else ""
        net_color = DOPAMINE_COLORS["mint"]["light"] if net >= 0 else DOPAMINE_COLORS["coral"]["light"]
        self._net_label = Label(
            text=f"{sign}{net:.0f}",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(net_color),
            size_hint=(None, None),
            size=(90, 24),
            halign="right",
            valign="middle",
            bold=True,
        )

        # 滞纳标签 (金额下方)
        if cycle.late_days > 0:
            self._late_label = Label(
                text=f"滞纳 {cycle.late_days}天",
                font_size=12,
                color=self._to_rgba(DOPAMINE_COLORS["coral"]["light"]),
                size_hint=(None, None),
                size=(90, 22),
                halign="right",
                valign="middle",
            )
        else:
            self._late_label = Label(
                text="按时完成",
                font_size=12,
                color=self._to_rgba(DOPAMINE_COLORS["mint"]["light"]),
                size_hint=(None, None),
                size=(90, 22),
                halign="right",
                valign="middle",
            )

        self.add_widget(self._date_label)
        self.add_widget(self._task_label)
        self.add_widget(self._net_label)
        self.add_widget(self._late_label)

        self.bind(pos=self._redraw, size=self._redraw)

    def _fmt_date(self) -> str:
        """格式化日期范围显示。"""
        ws = self._cycle.week_start
        we = self._cycle.week_end
        try:
            sd = datetime.strptime(ws, "%Y-%m-%d")
            ed = datetime.strptime(we, "%Y-%m-%d")
            return f"{sd.month}/{sd.day} ~ {ed.month}/{ed.day}"
        except ValueError:
            return f"{ws} ~ {we}"

    def _redraw(self, *args: Any) -> None:
        """绘制像素点进度条 + 玻璃卡片背景。"""
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size

        pad = GRID_UNIT

        # 玻璃卡片背景（与 DayCard/MonthCard 统一）
        draw_glass_card_bg(self, border_light=TEXT_BROWN, border_dark=TEXT_BROWN, inset=2)

        with self.canvas.before:
            # ── 像素点进度条 ──
            bar_x = x + pad + 144
            bar_area_w = w - pad * 2 - 144 - 100  # 左侧留日期区，右侧留金额区
            bar_y = y + (h - _DOT_H) / 2

            # 计算像素方块布局
            late_days = self._cycle.late_days
            total_dots = 7 + late_days  # 总天数

            if total_dots > 0 and bar_area_w > 10:
                dot_w, dot_h, gap = self._calc_dot_geom(bar_area_w, total_dots)
                dot_y = bar_y + (_DOT_H - dot_h) / 2

                # 不再画整条实心背景条 — 方块间按设计留有间隙(像素点风格),
                # 之前铺一块 _BAR_BG 矩形垫底会从间隙里透出灰色, 点数越多
                # (如滞纳期 12 点)间隙越密集越明显, 看起来像没画完/出错。
                # 去掉背景矩形后间隙直接透出卡片自身的玻璃背景, 更干净。

                # 绘制绿色方块（正常周期）
                for i in range(7):
                    dx = bar_x + i * (dot_w + gap)
                    Color(*self._to_rgba(_CYCLE_GREEN_DARK))
                    Rectangle(pos=(dx + 1, dot_y - 1), size=(dot_w, dot_h))
                    Color(*self._to_rgba(_CYCLE_GREEN))
                    Rectangle(pos=(dx, dot_y), size=(dot_w, dot_h))

                # 绘制红色方块（滞纳期）
                for i in range(late_days):
                    dx = bar_x + (7 + i) * (dot_w + gap)
                    Color(*self._to_rgba(_CYCLE_RED_DARK))
                    Rectangle(pos=(dx + 1, dot_y - 1), size=(dot_w, dot_h))
                    Color(*self._to_rgba(_CYCLE_RED))
                    Rectangle(pos=(dx, dot_y), size=(dot_w, dot_h))

        # 定位子组件
        self._date_label.pos = (x + pad, y + h - 28)
        self._task_label.pos = (x + pad, y + 8)
        self._net_label.pos = (x + w - 100, y + h - 28)
        self._late_label.pos = (x + w - 100, y + 8)

    def _calc_dot_geom(self, bar_w: float, total: int) -> tuple[float, float, float]:
        """根据可用宽度和点数计算点宽、点高、间距。"""
        ideal_w = _DOT_W
        ideal_h = _DOT_H
        ideal_gap = _DOT_GAP
        needed = total * ideal_w + (total - 1) * ideal_gap

        if needed <= bar_w:
            return ideal_w, ideal_h, ideal_gap

        # 空间不够：优先缩间隙，再缩方块
        if total > 1:
            gap = max(2, (bar_w - total * ideal_w) / (total - 1))
            if gap >= 3:
                return ideal_w, ideal_h, gap
        else:
            gap = 2

        # 间隙缩到最小仍不够 → 缩方块宽度
        gap = max(2, (bar_w - total * 6) / (total - 1)) if total > 1 else 2
        dot_w = max(6, (bar_w - (total - 1) * gap) / total)
        return dot_w, ideal_h, gap

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0,
                int(h[4:6], 16) / 255.0, alpha)
