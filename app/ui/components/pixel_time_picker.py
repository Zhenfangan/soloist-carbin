"""PixelTimePicker — 像素时间选择器弹窗。

小时/分钟双列步进选择，确认后返回 "HH:MM" 格式字符串。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView

from app.ui.components.pixel_button import PixelButton
from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_PADDING,
    CARD_WHITE,
    COLORS,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    GRID_UNIT,
    SHADOW_BLACK,
    TEXT_BROWN,
    TEXT_GRAY,
)


class PixelTimePicker(ModalView):  # type: ignore[misc]
    """像素时间选择器。

    用法:
        picker = PixelTimePicker(
            initial_time="09:00",
            on_select=lambda t: print(f"选中了 {t}"),
        )
        picker.open()

    布局:
        ┌────────────────────────┐
        │        选择时间          │
        │                        │
        │   [▲] 时  [▲] 分       │
        │    09      30           │
        │   [▼] 时  [▼] 分       │
        │                        │
        │    [确认]    [取消]      │
        └────────────────────────┘
    """

    def __init__(
        self,
        initial_time: str = "09:00",
        on_select: Callable[[str], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._on_select = on_select
        self.background = ""
        self.background_color = (0, 0, 0, 0)
        self.auto_dismiss = True

        # 解析初始时间
        parts = initial_time.split(":")
        self._hour = max(0, min(23, int(parts[0]) if len(parts) > 0 else 9))
        self._minute = max(0, min(59, int(parts[1]) if len(parts) > 1 else 0))

        # 根布局
        root = FloatLayout()
        self.add_widget(root)

        # 半透明遮罩
        with root.canvas.before:
            Color(0, 0, 0, 0.5)
            self._mask_rect = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_mask, pos=self._update_mask)

        # 弹窗卡片
        card_w = 280
        card_h = 280

        card = FloatLayout(
            size_hint=(None, None),
            size=(card_w, card_h),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )
        self._card = card

        # 卡片像素边框 + 阴影
        with card.canvas.before:
            # 阴影
            Color(*self._to_rgba(SHADOW_BLACK))
            Rectangle(pos=(card.x + 2, card.y - 2), size=(card_w, card_h))
            # 卡片背景
            Color(*self._to_rgba(CARD_WHITE))
            Rectangle(pos=(card.x, card.y), size=(card_w, card_h))
            # 凸起边框: 亮面 top+left
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(card.x, card.y + card_h - BORDER_WIDTH), size=(card_w, BORDER_WIDTH))
            Rectangle(pos=(card.x, card.y), size=(BORDER_WIDTH, card_h))
            # 暗面 bottom+right
            Color(*self._to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(card.x, card.y), size=(card_w, BORDER_WIDTH))
            Rectangle(pos=(card.x + card_w - BORDER_WIDTH, card.y), size=(BORDER_WIDTH, card_h))

        card.bind(pos=self._redraw_card, size=self._redraw_card)

        # 标题
        title_label = Label(
            text="选择时间",
            font_size=FONT_SIZE_TITLE,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=40,
            pos_hint={"x": 0, "y": 1 - 0.18},
            halign="center",
            valign="middle",
        )
        card.add_widget(title_label)

        # 时间选择区
        picker_layout = BoxLayout(
            orientation="horizontal",
            spacing=GRID_UNIT * 3,
            size_hint=(1, None),
            height=140,
            pos_hint={"x": 0, "y": 0.3},
            padding=[CARD_PADDING, 0],
        )

        # 小时列
        hour_col = BoxLayout(
            orientation="vertical",
            spacing=4,
            size_hint=(0.5, 1),
        )
        hour_up_btn = PixelButton(
            text="▲",
            size_mode="small",
            size_hint=(1, None),
        )
        hour_up_btn.bind(on_press=lambda _: self._adjust_hour(1))
        self._hour_label = Label(
            text=f"{self._hour:02d}",
            font_size=FONT_SIZE_TITLE,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, 1),
            halign="center",
            valign="middle",
        )
        hour_down_btn = PixelButton(
            text="v",
            size_mode="small",
            size_hint=(1, None),
        )
        hour_down_btn.bind(on_press=lambda _: self._adjust_hour(-1))
        hour_label_unit = Label(
            text="时",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_GRAY),
            size_hint=(1, None),
            height=20,
            halign="center",
            valign="middle",
        )
        hour_col.add_widget(hour_up_btn)
        hour_col.add_widget(self._hour_label)
        hour_col.add_widget(hour_down_btn)
        hour_col.add_widget(hour_label_unit)

        # 分钟列
        min_col = BoxLayout(
            orientation="vertical",
            spacing=4,
            size_hint=(0.5, 1),
        )
        min_up_btn = PixelButton(
            text="▲",
            size_mode="small",
            size_hint=(1, None),
        )
        min_up_btn.bind(on_press=lambda _: self._adjust_minute(1))
        self._min_label = Label(
            text=f"{self._minute:02d}",
            font_size=FONT_SIZE_TITLE,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, 1),
            halign="center",
            valign="middle",
        )
        min_down_btn = PixelButton(
            text="v",
            size_mode="small",
            size_hint=(1, None),
        )
        min_down_btn.bind(on_press=lambda _: self._adjust_minute(-1))
        min_label_unit = Label(
            text="分",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_GRAY),
            size_hint=(1, None),
            height=20,
            halign="center",
            valign="middle",
        )
        min_col.add_widget(min_up_btn)
        min_col.add_widget(self._min_label)
        min_col.add_widget(min_down_btn)
        min_col.add_widget(min_label_unit)

        picker_layout.add_widget(hour_col)
        picker_layout.add_widget(min_col)
        card.add_widget(picker_layout)

        # 按钮栏
        btn_layout = BoxLayout(
            orientation="horizontal",
            spacing=GRID_UNIT * 2,
            size_hint=(1, None),
            height=48,
            pos_hint={"x": 0, "y": 0},
            padding=[CARD_PADDING, GRID_UNIT],
        )

        cancel_btn = PixelButton(
            text="取消",
            color=COLORS["CARD_SHADOW"],
            size_mode="small",
            size_hint=(1, None),
        )
        cancel_btn.bind(on_press=lambda _: self.dismiss())

        confirm_btn = PixelButton(
            text="确认",
            color=COLORS["PRIMARY_YELLOW"],
            size_mode="small",
            size_hint=(1, None),
        )
        confirm_btn.bind(on_press=lambda _: self._handle_confirm())

        btn_layout.add_widget(cancel_btn)
        btn_layout.add_widget(confirm_btn)
        card.add_widget(btn_layout)

        root.add_widget(card)

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    def _update_mask(self, instance: Any, value: Any) -> None:
        self._mask_rect.size = instance.size
        self._mask_rect.pos = instance.pos

    def _redraw_card(self, instance: Any, value: Any) -> None:
        instance.canvas.before.clear()
        bw = BORDER_WIDTH
        x, y = instance.pos
        w, h = instance.size

        with instance.canvas.before:
            Color(*self._to_rgba(SHADOW_BLACK))
            Rectangle(pos=(x + 2, y - 2), size=(w, h))
            Color(*self._to_rgba(CARD_WHITE))
            Rectangle(pos=(x, y), size=(w, h))
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(x, y + h - bw), size=(w, bw))
            Rectangle(pos=(x, y), size=(bw, h))
            Color(*self._to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(x, y), size=(w, bw))
            Rectangle(pos=(x + w - bw, y), size=(w, h))

    def _adjust_hour(self, delta: int) -> None:
        self._hour = (self._hour + delta) % 24
        self._hour_label.text = f"{self._hour:02d}"

    def _adjust_minute(self, delta: int) -> None:
        self._minute = (self._minute + delta) % 60
        self._min_label.text = f"{self._minute:02d}"

    def _handle_confirm(self) -> None:
        if self._on_select:
            time_str = f"{self._hour:02d}:{self._minute:02d}"
            self._on_select(time_str)
        self.dismiss()
