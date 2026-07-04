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
from app.ui.components.pixel_dot_bar import calc_dot_geom
from app.ui.tokens import (
    DOPAMINE_COLORS,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    GRID_UNIT,
    TEXT_BROWN,
    TEXT_GRAY,
)

# 周期条配色
_CYCLE_GREEN = DOPAMINE_COLORS["mint"]["light"]   # 正常周期
_CYCLE_GREEN_DARK = DOPAMINE_COLORS["mint"]["dark"]
_CYCLE_RED = DOPAMINE_COLORS["coral"]["light"]     # 滞纳期
_CYCLE_RED_DARK = DOPAMINE_COLORS["coral"]["dark"]
_DOT_H = 14             # 像素点高度(几何计算见 pixel_dot_bar.calc_dot_geom)
_CARD_HEIGHT = 108      # 卡片总高(含底部"其他收入合计"行)


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

        # 金额标签 (右) —— 字号加大, 一眼看清本周期净额
        net = cycle.net
        sign = "+" if net >= 0 else ""
        net_color = DOPAMINE_COLORS["mint"]["light"] if net >= 0 else DOPAMINE_COLORS["coral"]["light"]
        self._net_label = Label(
            text=f"{sign}{net:.0f}",
            font_size=FONT_SIZE_TITLE + 6,
            color=self._to_rgba(net_color),
            size_hint=(None, None),
            size=(110, 30),
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

        # 合计行(底部居中) —— 对赌净额 + 其他收入(如拍摄日奖励), 只在有其他
        # 收入时显示, 避免和 net 数字重复。
        total = cycle.net + cycle.other_income
        total_sign = "+" if total >= 0 else ""
        has_other_income = cycle.other_income != 0
        self._total_label = Label(
            text=f"含其他收入合计: {total_sign}{total:.0f}" if has_other_income else "",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_GRAY),
            size_hint=(None, None),
            size=(220, 18),
            halign="center",
            valign="middle",
            opacity=1 if has_other_income else 0,
        )

        self.add_widget(self._date_label)
        self.add_widget(self._task_label)
        self.add_widget(self._net_label)
        self.add_widget(self._late_label)
        self.add_widget(self._total_label)

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
            bar_area_w = w - pad * 2 - 144 - 120  # 左侧留日期区，右侧留金额区(字号加大后需更宽)
            bar_y = y + (h - _DOT_H) / 2

            # 计算像素方块布局
            late_days = self._cycle.late_days
            total_dots = 7 + late_days  # 总天数

            if total_dots > 0 and bar_area_w > 10:
                dot_w, dot_h, gap = calc_dot_geom(bar_area_w, total_dots)
                dot_y = bar_y + (_DOT_H - dot_h) / 2

                # 不再画整条实心背景条 — 方块间按设计留有间隙(像素点风格),
                # 之前铺一块 _BAR_BG 矩形垫底会从间隙里透出灰色, 点数越多
                # (如滞纳期 12 点)间隙越密集越明显, 看起来像没画完/出错。
                # 去掉背景矩形后间隙直接透出卡片自身的玻璃背景, 更干净。

                # 绘制本周期方块 — 有罚款则用红色, 否则绿色(不能不看 penalty 硬编码绿)
                dot_color, dot_color_dark = self._dot_color(), self._dot_color_dark()
                for i in range(7):
                    dx = bar_x + i * (dot_w + gap)
                    Color(*self._to_rgba(dot_color_dark))
                    Rectangle(pos=(dx + 1, dot_y - 1), size=(dot_w, dot_h))
                    Color(*self._to_rgba(dot_color))
                    Rectangle(pos=(dx, dot_y), size=(dot_w, dot_h))

                # 绘制红色方块（滞纳期）
                for i in range(late_days):
                    dx = bar_x + (7 + i) * (dot_w + gap)
                    Color(*self._to_rgba(_CYCLE_RED_DARK))
                    Rectangle(pos=(dx + 1, dot_y - 1), size=(dot_w, dot_h))
                    Color(*self._to_rgba(_CYCLE_RED))
                    Rectangle(pos=(dx, dot_y), size=(dot_w, dot_h))

        # 定位子组件(卡片加高后分 3 行: 顶行日期/金额, 中部任务/滞纳, 底部合计)
        self._date_label.pos = (x + pad, y + h - 28)
        self._net_label.pos = (x + w - 118, y + h - 32)
        self._task_label.pos = (x + pad, y + 26)
        self._late_label.pos = (x + w - 100, y + 26)
        self._total_label.pos = (x + (w - 220) / 2, y + 4)

    def _dot_color(self) -> str:
        """本周期方块颜色 — 有罚款(penalty>0)显示红, 否则绿。"""
        return _CYCLE_RED if self._cycle.penalty > 0 else _CYCLE_GREEN

    def _dot_color_dark(self) -> str:
        return _CYCLE_RED_DARK if self._cycle.penalty > 0 else _CYCLE_GREEN_DARK

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0,
                int(h[4:6], 16) / 255.0, alpha)
