"""DayCard — 历史页周视图每日摘要卡片。

2px 边框卡片 + 2px 右移纯黑阴影。
显示日期、上下午状态、工作时长、奖惩金额。
拍摄日用橙色背景 + 咪咕图标。
点击可查看明细。
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, cast

from kivy.graphics import Color, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

from app.models.history import DayCard as DayCardModel  # noqa: N813
from app.ui.assets.loader import IconLoader
from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_WHITE,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    SEMANTIC_COLORS,
    SHADOW_BLACK,
    TEXT_BROWN,
    TEXT_GRAY,
)

# 星期名称
WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 状态中文映射
STATUS_LABELS: dict[str, str] = {
    "normal": "正常",
    "late": "迟到",
    "early_leave": "早退",
    "absent": "旷工",
    "absent_morning": "上午旷工",
    "absent_afternoon": "下午旷工",
    "leave": "请假",
    "pending": "未打卡",
}

# 状态颜色映射
STATUS_COLORS: dict[str, str] = {
    "normal": SEMANTIC_COLORS["normal"]["border"],
    "late": SEMANTIC_COLORS["late"]["border"],
    "early_leave": SEMANTIC_COLORS["early_leave"]["border"],
    "absent": SEMANTIC_COLORS["absent"]["border"],
    "absent_morning": SEMANTIC_COLORS["absent"]["border"],
    "absent_afternoon": SEMANTIC_COLORS["absent"]["border"],
    "leave": SEMANTIC_COLORS["leave"]["border"],
    "pending": TEXT_GRAY,
}


class DayCard(FloatLayout):  # type: ignore[misc]
    """每日摘要卡片。

    属性:
        day_summary: DayCard 数据模型实例
        on_click: 点击卡片回调
    """

    def __init__(
        self,
        day_summary: DayCardModel,
        on_click: Callable[[DayCardModel], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            size_hint=(1, None),
            **kwargs,
        )
        self._day = day_summary
        self._on_click = on_click

        # 卡片高度由内容撑起
        self.height = 80

        # 日期标签
        dt = datetime.strptime(day_summary.date, "%Y-%m-%d")
        weekday_name = WEEKDAY_NAMES[dt.weekday()]
        date_text = f"{dt.month}月{dt.day}日 {weekday_name}"
        self._date_label = Label(
            text=date_text,
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, None),
            size=(200, 24),
            pos_hint={"x": 0.05, "y": 0.65},
            halign="left",
            valign="middle",
        )
        self.add_widget(self._date_label)

        # 状态标签 (上午 → 下午 → 晚上，固定顺序)
        _PERIOD_ORDER = {"morning": 0, "afternoon": 1, "evening": 2, "night": 2}
        _PERIOD_CN = {"morning": "上午", "afternoon": "下午", "evening": "晚上", "night": "晚上"}
        sorted_periods = sorted(
            day_summary.periods,
            key=lambda p: _PERIOD_ORDER.get(p.period, 99),
        )
        status_parts: list[str] = []
        for period in sorted_periods:
            period_label_cn = _PERIOD_CN.get(period.period, period.period)
            status_cn = STATUS_LABELS.get(period.status, period.status)
            status_parts.append(f"{period_label_cn}: {status_cn}")
        status_text = "  ".join(status_parts) if status_parts else "暂无打卡记录"

        self._status_label = Label(
            text=status_text,
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_GRAY),
            size_hint=(None, None),
            size=(300, 20),
            pos_hint={"x": 0.05, "y": 0.40},
            halign="left",
            valign="middle",
        )
        self.add_widget(self._status_label)

        # 工作时长 + 奖惩
        penalty = sum(e.amount for e in day_summary.daily_ledger)
        hours_text = f"{day_summary.total_hours:.1f}h"
        penalty_text = f"奖惩: {penalty:+g}" if penalty != 0 else "奖惩: 0"
        bottom_text = f"{hours_text}  {penalty_text}"

        self._hours_label = Label(
            text=bottom_text,
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, None),
            size=(300, 20),
            pos_hint={"x": 0.05, "y": 0.15},
            halign="left",
            valign="middle",
        )
        self.add_widget(self._hours_label)

        # "点击查看复盘" 提示
        self._hint_label = Label(
            text="点击查看复盘 →",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_GRAY),
            size_hint=(None, None),
            size=(150, 20),
            pos_hint={"right": 0.95, "y": 0.15},
            halign="right",
            valign="middle",
        )
        self.add_widget(self._hint_label)

        # 拍摄日用橙色底 + 咪咕图标
        if day_summary.is_shooting:
            try:
                migu = IconLoader.get_icon("check_mark")
                migu.size_hint = (None, None)
                migu.size = (16, 16)
                migu.pos_hint = {"right": 0.95, "y": 0.65}
                self.add_widget(migu)
            except Exception:
                pass

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
        """绘制 2px 边框 + 2px 右移纯黑阴影。"""
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        bw = BORDER_WIDTH
        shadow_offset = 2

        with self.canvas.before:
            # 2px 右移纯黑阴影
            Color(*self._to_rgba(SHADOW_BLACK))
            Rectangle(pos=(x + bw + shadow_offset, y - shadow_offset), size=(w - 2 * bw, h))

            # 背景填充（拍摄日用橙色底）
            if self._day.is_shooting:
                bg_color = SEMANTIC_COLORS["shooting"]["block"]
            else:
                bg_color = CARD_WHITE
            Color(*self._to_rgba(bg_color))
            Rectangle(pos=(x + bw, y + bw), size=(w - 2 * bw, h - 2 * bw))

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

    def on_touch_down(self, touch: Any) -> bool:
        """点击触发回调。"""
        if self.collide_point(*touch.pos):
            if self._on_click:
                self._on_click(self._day)
            return True
        return cast(bool, super().on_touch_down(touch))
