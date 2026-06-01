"""StatusBox — 状态显示框组件。

显示三个时段的实时状态：上午/下午/晚上。
使用功能语义色 (SEMANTIC_COLORS) 渲染不同状态。
"""

from __future__ import annotations

from typing import Any

from kivy.graphics import Color, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

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

PERIOD_LABELS_MAP: dict[str, str] = {
    "morning": "上午",
    "afternoon": "下午",
    "evening": "晚上",
    "night": "晚上",
}


class StatusBox(FloatLayout):  # type: ignore[misc]
    """状态显示框。

    属性:
        day_status: DayStatus 对象 (含 periods 列表)
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.size_hint = (1, None)
        self.height = 120

        # 标题
        self._title_label = Label(
            text="今日状态",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_GRAY),
            size_hint=(1, None),
            height=20,
            pos_hint={"x": 0, "y": 0.75},
            halign="left",
            valign="middle",
        )

        # 三条状态行
        self._status_lines: dict[str, dict[str, Any]] = {}
        self._line_widgets: dict[str, FloatLayout] = {}

        for period in ["morning", "afternoon", "evening"]:
            line = FloatLayout(
                size_hint=(1, None),
                height=24,
                pos_hint={"x": 0, "y": 0},
            )
            period_label_text = PERIOD_LABELS_MAP.get(period, period)

            # 时段标签
            label_w = Label(
                text=f"{period_label_text}：",
                font_size=FONT_SIZE_BODY,
                color=self._to_rgba(TEXT_BROWN),
                size_hint=(None, 1),
                width=50,
                pos_hint={"x": 0, "y": 0},
                halign="right",
                valign="middle",
            )

            # 状态文案
            status_w = Label(
                text="等待签到...",
                font_size=FONT_SIZE_BODY,
                color=self._to_rgba(TEXT_GRAY),
                size_hint=(1, 1),
                pos_hint={"x": 0.15, "y": 0},
                halign="left",
                valign="middle",
                text_size=(0, 24),
            )

            line.add_widget(label_w)
            line.add_widget(status_w)
            self.add_widget(line)
            self._line_widgets[period] = line
            self._status_lines[period] = {"label_w": label_w, "status_w": status_w}

        self.add_widget(self._title_label)
        self.bind(pos=self._redraw, size=self._redraw)

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    def update_status(self, day_status: Any) -> None:
        """根据 DayStatus 更新状态显示。"""
        if day_status is None:
            return

        date = getattr(day_status, "date", "")
        periods = getattr(day_status, "periods", [])
        is_shooting_day = getattr(day_status, "is_shooting_day", False)

        # 更新标题
        if date:
            self._title_label.text = date

        # 时段状态行
        period_map: dict[str, Any] = {}
        for ps in periods:
            period_map[ps.period] = ps

        for period in ["morning", "afternoon", "evening"]:
            ps = period_map.get(period)
            line_info = self._status_lines.get(period)
            if not line_info:
                continue

            status_w = line_info["status_w"]

            if ps is None:
                # 无数据
                status_w.text = "等待签到..."
                status_w.color = self._to_rgba(TEXT_GRAY)
            else:
                text = self._build_status_text(ps, is_shooting_day)
                color_hex = self._get_status_color(ps.status)
                status_w.text = text
                status_w.color = self._to_rgba(color_hex)

        # 更新行位置
        y_start = 0.55
        for i, period in enumerate(["morning", "afternoon", "evening"]):
            line_widget = self._line_widgets.get(period)
            if line_widget:
                line_widget.pos_hint = {"x": 0, "y": y_start - i * 0.18}

    def _build_status_text(self, ps: Any, is_shooting_day: bool) -> str:
        """根据 PeriodStatus 构建状态文案。"""
        status = ps.status
        checkin_time = ps.checkin_time
        checkout_time = ps.checkout_time

        if status == "pending":
            if is_shooting_day:
                return "拍摄中 \U0001f4f8"
            return "等待签到..."
        if status == "normal":
            parts = [f"正常签到 {checkin_time}" if checkin_time else "正常"]
            if checkout_time:
                parts.append(f"签退 {checkout_time}")
            return " / ".join(parts)
        if status == "late":
            return f"迟到 {checkin_time}" if checkin_time else "迟到"
        if status == "early_leave":
            return f"早退 {checkout_time}" if checkout_time else "早退"
        if status == "absent":
            return "旷工"
        if status == "absent_morning":
            return "旷工(上午)"
        if status == "absent_afternoon":
            return "旷工(下午)"
        if status == "leave":
            return "已请假"
        if status == "shooting":
            return "拍摄中 \U0001f4f8"

        # 工作中（已签到未签退）
        if checkin_time and not checkout_time and status != "leave":
            return "工作中..."
        if checkin_time and checkout_time:
            return f"签到 {checkin_time} / 签退 {checkout_time}"

        return "等待签到..."

    def _get_status_color(self, status: str) -> str:
        """根据状态获取对应颜色。"""
        if status in SEMANTIC_COLORS:
            return SEMANTIC_COLORS[status]["icon"]
        if status in ("absent_morning", "absent_afternoon"):
            return SEMANTIC_COLORS["absent"]["icon"]
        return TEXT_GRAY

    def _redraw(self, *args: Any) -> None:
        """重绘状态框像素边框。"""
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        bw = BORDER_WIDTH

        with self.canvas.before:
            # 阴影
            Color(*self._to_rgba(SHADOW_BLACK))
            Rectangle(pos=(x + 2, y - 2), size=(w, h))
            # 背景
            Color(*self._to_rgba(CARD_WHITE))
            Rectangle(pos=(x, y), size=(w, h))
            # 凸起边框
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(x, y + h - bw), size=(w, bw))
            Rectangle(pos=(x, y), size=(bw, h))
            Color(*self._to_rgba("#F0E8D0"))
            Rectangle(pos=(x, y), size=(w, bw))
            Rectangle(pos=(x + w - bw, y), size=(bw, h))
