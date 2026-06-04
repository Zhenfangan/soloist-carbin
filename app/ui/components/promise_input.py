"""PromiseInput — 男友承诺输入弹窗。

像素弹窗: 标题 🐻 "设定今日奖励" + 文字输入 + 数量步进器 + 确定/跳过按钮。
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
from app.ui.components.pixel_stepper import PixelStepper
from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_WHITE,
    COLORS,
    DOPAMINE_COLORS,
    FONT_SIZE_BODY,
    FONT_SIZE_TITLE,
    GRID_UNIT,
    SHADOW_BLACK,
    TEXT_BROWN,
    TEXT_GRAY,
)


class PromiseInput(ModalView):  # type: ignore[misc]
    """男友承诺输入弹窗。

    用法:
        PromiseInput(hours_threshold=8, on_done=lambda promise: ...).open()
    """

    def __init__(
        self,
        hours_threshold: float = 8.0,
        on_done: Callable[[dict[str, Any] | None], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.background = ""
        self.background_color = (0, 0, 0, 0)
        self.auto_dismiss = True

        self._hours_threshold = hours_threshold
        self._on_done = on_done

        # 根布局
        root = FloatLayout()
        self.add_widget(root)

        # 半透明遮罩
        with root.canvas.before:
            Color(0, 0, 0, 0.5)
            self._mask_rect = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_mask, pos=self._update_mask)

        # 弹窗卡片
        card_w = 300
        card_h = 280

        card = FloatLayout(
            size_hint=(None, None),
            size=(card_w, card_h),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )

        # 卡片像素边框
        with card.canvas.before:
            # 阴影
            Color(*self._to_rgba(SHADOW_BLACK))
            Rectangle(pos=(card.x + 2, card.y - 2), size=(card.width, card.height))
            # 背景
            Color(*self._to_rgba(CARD_WHITE))
            Rectangle(pos=(card.x, card.y), size=(card.width, card.height))
            # 凸起边框
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(card.x, card.y + card_h - BORDER_WIDTH), size=(card_w, BORDER_WIDTH))
            Rectangle(pos=(card.x, card.y), size=(BORDER_WIDTH, card_h))
            Color(*self._to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(card.x, card.y), size=(card_w, BORDER_WIDTH))
            Rectangle(pos=(card.x + card_w - BORDER_WIDTH, card.y), size=(BORDER_WIDTH, card_h))

        card.bind(pos=self._redraw_card, size=self._redraw_card)
        self._card = card
        self._card_size = (card_w, card_h)

        # 🐻 标题
        title_label = Label(
            text="设定今日奖励",
            font_size=FONT_SIZE_TITLE,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=36,
            pos_hint={"x": 0.1, "y": 0.78},
            halign="left",
            valign="middle",
        )

        # 门槛提示
        threshold_label = Label(
            text=f"如果今天工作满 {int(hours_threshold)} 小时",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_GRAY),
            size_hint=(1, None),
            height=24,
            pos_hint={"x": 0.1, "y": 0.65},
            halign="left",
            valign="middle",
        )

        # 奖励输入
        self._desc_input = PixelInput(
            hint_text="奖励自己：一杯奶茶",
            size_hint=(0.8, None),
            height=36,
            pos_hint={"center_x": 0.5, "y": 0.42},
        )

        # 数量区域
        qty_layout = BoxLayout(
            orientation="horizontal",
            spacing=GRID_UNIT,
            size_hint=(0.8, None),
            height=32,
            pos_hint={"center_x": 0.5, "y": 0.28},
        )

        qty_label = Label(
            text="数量:",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, 1),
            width=50,
            halign="left",
            valign="middle",
        )

        self._stepper = PixelStepper(
            value=1,
            min_value=1,
            max_value=99,
            step=1,
            size_hint=(None, 1),
            width=120,
        )

        qty_layout.add_widget(qty_label)
        qty_layout.add_widget(self._stepper)

        # 按钮行
        btn_layout = BoxLayout(
            orientation="horizontal",
            spacing=GRID_UNIT * 2,
            size_hint=(0.8, None),
            height=36,
            pos_hint={"center_x": 0.5, "y": 0.05},
        )

        skip_btn = PixelButton(
            text="跳过",
            color=COLORS["CARD_SHADOW"],
            size_mode="small",
            size_hint=(1, None),
        )
        skip_btn.bind(on_press=lambda _: self._handle_skip())

        confirm_btn = PixelButton(
            text="确定",
            color=DOPAMINE_COLORS["mint"]["light"],
            size_mode="small",
            size_hint=(1, None),
        )
        confirm_btn.bind(on_press=lambda _: self._handle_confirm())

        btn_layout.add_widget(skip_btn)
        btn_layout.add_widget(confirm_btn)

        card.add_widget(title_label)
        card.add_widget(threshold_label)
        card.add_widget(self._desc_input)
        card.add_widget(qty_layout)
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

    def _handle_confirm(self) -> None:
        """确定按钮回调。"""
        if self._on_done:
            reward_desc = self._desc_input.text.strip()
            if not reward_desc:
                reward_desc = self._desc_input.hint_text
            self._on_done({
                "reward_desc": reward_desc,
                "reward_qty": self._stepper.value,
            })
        self.dismiss()

    def _handle_skip(self) -> None:
        """跳过按钮回调。"""
        if self._on_done:
            self._on_done(None)
        self.dismiss()
