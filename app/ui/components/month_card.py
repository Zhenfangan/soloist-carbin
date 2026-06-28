"""MonthCard — 年视图月度汇总卡片。

显示月份、出勤天数、迟到次数、旷工次数、总时长、奖惩金额。
"""

from __future__ import annotations

from typing import Any

from kivy.graphics import Color, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

from app.ui.components.glass_bg import draw_glass_card_bg
from app.models.history import MonthSummary
from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_WHITE,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    SHADOW_BLACK,
    TEXT_BROWN,
    TEXT_GRAY,
)

# 月份中文名
MONTH_NAMES = [
    "", "1月", "2月", "3月", "4月", "5月", "6月",
    "7月", "8月", "9月", "10月", "11月", "12月",
]


class MonthCard(FloatLayout):  # type: ignore[misc]
    """月度汇总卡片。

    属性:
        month_summary: MonthSummary 数据模型实例
    """

    def __init__(
        self,
        month_summary: MonthSummary,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            size_hint=(1, None),
            **kwargs,
        )
        self._month = month_summary
        self.height = 96

        # 月份标题
        month_name = MONTH_NAMES[month_summary.month] if 1 <= month_summary.month <= 12 else f"{month_summary.month}月"
        self._title_label = Label(
            text=month_name,
            font_size=16,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, None),
            size=(100, 28),
            pos_hint={"x": 0.05, "y": 0.65},
            halign="left",
            valign="middle",
        )
        self.add_widget(self._title_label)

        # 出勤信息
        stats_text = (
            f"出勤 {month_summary.work_days}天"
            f"  迟到 {month_summary.late_count}次"
            f"  旷工 {month_summary.absent_count}次"
        )
        self._stats_label = Label(
            text=stats_text,
            font_size=13,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, None),
            size=(400, 24),
            pos_hint={"x": 0.05, "y": 0.40},
            halign="left",
            valign="middle",
        )
        self.add_widget(self._stats_label)

        # 总时长 + 奖惩 + 对赌
        penalty = month_summary.total_ledger
        bet_net = month_summary.bet_net
        bottom_text = (
            f"总时长 {month_summary.total_hours:.1f}h"
            f"  考勤 {penalty:+g}"
        )
        self._bottom_label = Label(
            text=bottom_text,
            font_size=13,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, None),
            size=(400, 24),
            pos_hint={"x": 0.05, "y": 0.15},
            halign="left",
            valign="middle",
        )
        self.add_widget(self._bottom_label)

        # 对赌行
        if month_summary.bet_cycles > 0:
            bet_sign = "+" if bet_net >= 0 else ""
            bet_text = f"对赌 {month_summary.bet_cycles}周期  净额 {bet_sign}{bet_net:.0f}"
            bet_color = "#50E8B0" if bet_net >= 0 else "#FF6B8A"
            self._bet_label = Label(
                text=bet_text,
                font_size=13,
                color=self._to_rgba(bet_color),
                size_hint=(None, None),
                size=(400, 24),
                pos_hint={"x": 0.05, "y": 0.0},
                halign="left",
                valign="middle",
            )
            self.add_widget(self._bet_label)

        self.bind(pos=self._redraw, size=self._redraw)

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (
            int(h[0:2], 16) / 255.0,
            int(h[2:4], 16) / 255.0,
            int(h[4:6], 16) / 255.0,
            alpha,
        )

    def _redraw(self, *args: Any) -> None:
        """绘制玻璃背景 + 2px 茶色边框。"""
        draw_glass_card_bg(self, border_light=TEXT_BROWN, border_dark=TEXT_BROWN, inset=2)
