"""PixelNumberDialog — 像素数字输入弹窗。

含标题提示 + PixelInput(纯数字) + 确认/取消按钮。
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
from app.ui.components.pixel_input import PixelInput
from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_PADDING,
    CARD_WHITE,
    COLORS,
    FONT_SIZE_TITLE,
    GRID_UNIT,
    SHADOW_BLACK,
    TEXT_BROWN,
)


class PixelNumberDialog(ModalView):  # type: ignore[misc]
    """像素数字输入弹窗。

    用法:
        dlg = PixelNumberDialog(
            title="迟到罚款",
            initial_value="10",
            on_confirm=lambda v: print(f"设置值为 {v}"),
        )
        dlg.open()

    布局:
        ┌────────────────────────┐
        │       迟到罚款          │
        │                        │
        │   ┌────────────────┐   │
        │   │  输入金额        │   │
        │   └────────────────┘   │
        │                        │
        │    [确认]    [取消]      │
        └────────────────────────┘
    """

    def __init__(
        self,
        title: str = "",
        initial_value: str = "0",
        on_confirm: Callable[[str], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._on_confirm = on_confirm
        self.background = ""
        self.background_color = (0, 0, 0, 0)
        self.auto_dismiss = True

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
        card_h = 220

        card = FloatLayout(
            size_hint=(None, None),
            size=(card_w, card_h),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )
        self._card = card

        # 卡片像素边框 + 阴影
        with card.canvas.before:
            Color(*self._to_rgba(SHADOW_BLACK))
            Rectangle(pos=(card.x + 2, card.y - 2), size=(card_w, card_h))
            Color(*self._to_rgba(CARD_WHITE))
            Rectangle(pos=(card.x, card.y), size=(card_w, card_h))
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(card.x, card.y + card_h - BORDER_WIDTH), size=(card_w, BORDER_WIDTH))
            Rectangle(pos=(card.x, card.y), size=(BORDER_WIDTH, card_h))
            Color(*self._to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(card.x, card.y), size=(card_w, BORDER_WIDTH))
            Rectangle(pos=(card.x + card_w - BORDER_WIDTH, card.y), size=(BORDER_WIDTH, card_h))

        card.bind(pos=self._redraw_card, size=self._redraw_card)

        # 标题
        title_label = Label(
            text=title,
            font_size=FONT_SIZE_TITLE,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=40,
            pos_hint={"x": 0, "y": 1 - 0.25},
            halign="center",
            valign="middle",
        )
        card.add_widget(title_label)

        # 输入框
        input_layout = FloatLayout(
            size_hint=(1, None),
            height=60,
            pos_hint={"x": 0, "y": 0.3},
        )
        self._input = PixelInput(
            value=initial_value,
            size_hint=(None, None),
            size=(card_w - CARD_PADDING * 2, 48),
            pos_hint={"center_x": 0.5, "y": 0},
        )
        # 过滤非数字字符
        self._input.bind(text=self._filter_numeric)
        input_layout.add_widget(self._input)
        card.add_widget(input_layout)

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

    def _filter_numeric(self, instance: Any, text: str) -> None:
        """过滤非数字字符（允许空字符串和负号）。"""
        filtered = "".join(c for c in text if c.isdigit() or (c == "-" and text.index(c) == 0))
        if filtered != text:
            self._input.text = filtered

    def _handle_confirm(self) -> None:
        if self._on_confirm:
            self._on_confirm(self._input.text)
        self.dismiss()
