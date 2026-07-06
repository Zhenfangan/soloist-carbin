"""StatusBox — 状态显示框组件。

显示三个时段的实时状态：上午/下午/晚上。
使用功能语义色 (SEMANTIC_COLORS) 渲染不同状态。
"""

from __future__ import annotations

from typing import Any

from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from app.ui.components.glass_bg import draw_glass_card_bg
from app.ui.components.icon_label import IconLabel
from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_PADDING,
    CARD_WHITE,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    GRID_UNIT,
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


class StatusBox(BoxLayout):  # type: ignore[misc]
    """状态显示框 — 标题 + 三行状态，垂直柱状排列。

    属性:
        day_status: DayStatus 对象 (含 periods 列表)
    """

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", 120)
        kwargs.setdefault("padding", [CARD_PADDING, GRID_UNIT, CARD_PADDING, GRID_UNIT])
        kwargs.setdefault("spacing", 2)
        super().__init__(**kwargs)

        # 标题 — 大字号显示，单字号高于正文
        self._title_label = IconLabel(
            icon="icon_chart", text="今日状态",
            font_size=FONT_SIZE_TITLE,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=28,
        )
        self.add_widget(self._title_label)

        # 三条状态行
        self._status_widgets: dict[str, IconLabel] = {}
        self._label_widgets: dict[str, Label] = {}
        self._rows: list[dict[str, Any]] = []

        for period in ["morning", "afternoon", "evening"]:
            period_label_text = PERIOD_LABELS_MAP.get(period, period)

            row = BoxLayout(
                orientation="horizontal",
                size_hint=(1, None),
                height=28,
                spacing=4,
            )

            label_w = Label(
                text=f"{period_label_text}：",
                font_size=FONT_SIZE_BODY,
                color=self._to_rgba(TEXT_BROWN),
                size_hint=(None, 1),
                width=50,
                halign="right",
                valign="middle",
            )

            status_w = IconLabel(
                icon="icon_hourglass", text="等待签到...",
                font_size=FONT_SIZE_BODY,
                color=self._to_rgba(TEXT_BROWN),
                size_hint=(1, None),
                height=28,
            )

            row.add_widget(label_w)
            row.add_widget(status_w)
            self.add_widget(row)

            self._label_widgets[period] = label_w
            self._status_widgets[period] = status_w

            self._rows.append({
                "row": row,
                "label_w": label_w,
                "status_w": status_w,
                "period": period,
            })

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

        if date:
            self._title_label.set_status("icon_calendar", date)

        period_map: dict[str, Any] = {}
        for ps in periods:
            period_map[ps.period] = ps

        for period in ["morning", "afternoon", "evening"]:
            ps = period_map.get(period)
            status_w = self._status_widgets.get(period)
            if not status_w:
                continue

            if ps is None:
                status_w.set_status("icon_hourglass", "等待签到...")
                status_w.color = self._to_rgba(TEXT_BROWN)
            else:
                segments = self._build_status_segments(ps, is_shooting_day)
                color_hex = self._get_status_color(ps.status)
                status_w.set_segments(segments)
                status_w.color = self._to_rgba(color_hex)

    def _build_status_segments(
        self, ps: Any, is_shooting_day: bool
    ) -> list[tuple[str | None, str]]:
        """根据 PeriodStatus 构建状态图标+文案片段。

        迟到/早退为可并存的独立事实，由 service 在 is_late/is_early_leave
        标志位中给出，这里按"签到段 / 签退段"分别拼接，二者都违规则都展示。
        """
        status = ps.status
        checkin_time = ps.checkin_time
        checkout_time = ps.checkout_time
        # 优先用 service 给的独立标志位；缺失时回退 status 单值(向后兼容)
        is_late = getattr(ps, "is_late", False) or status == "late"
        is_early_leave = getattr(ps, "is_early_leave", False) or status == "early_leave"

        # 终态 / 非出勤态 — 直接返回
        if status == "pending":
            if is_shooting_day:
                return [("icon_camera", "拍摄中")]
            return [("icon_hourglass", "等待签到...")]
        if status in ("absent", "absent_morning", "absent_afternoon"):
            penalty = getattr(ps, "penalty_amount", None)
            amount_str = f" {int(penalty)}" if penalty is not None else ""
            if status == "absent_morning":
                return [("warning", f"未签到(上午){amount_str}")]
            if status == "absent_afternoon":
                return [("warning", f"未签到(下午){amount_str}")]
            return [("warning", f"未签到{amount_str}")]
        if status == "leave":
            return [("icon_bed", "已请假")]
        if status == "shooting":
            return [("icon_camera", "拍摄中")]

        # 出勤态 — 签到段 + 签退段独立拼接（迟到与早退可并存）
        segments: list[tuple[str | None, str]] = []
        if checkin_time:
            if is_late:
                segments.append(("icon_clock", f"迟到 {checkin_time}"))
            else:
                segments.append(("check_mark", f"正常签到 {checkin_time}"))
        if checkout_time:
            if is_early_leave:
                segments.append(("icon_run", f"早退 {checkout_time}"))
            else:
                segments.append(("icon_moon", f"签退 {checkout_time}"))
        if segments:
            return segments

        return [("icon_hourglass", "等待签到...")]

    def _get_status_color(self, status: str) -> str:
        """根据状态获取对应颜色。"""
        if status in SEMANTIC_COLORS:
            return SEMANTIC_COLORS[status]["icon"]
        if status in ("absent_morning", "absent_afternoon"):
            return SEMANTIC_COLORS["absent"]["icon"]
        return TEXT_BROWN

    @property
    def _period_rows(self) -> list[dict[str, Any]]:
        """暴露 period 行数据供测试使用。"""
        return self._rows

    def _update_status_text_sizes(self) -> None:
        """手动触发 status_w 的 text_size 更新。"""
        for row_info in self._rows:
            w = row_info["status_w"]
            if w.width > 0:
                w.text_size = (w.width, w.height)

    def _redraw(self, *args: Any) -> None:
        """重绘状态框玻璃背景。"""
        draw_glass_card_bg(self)
