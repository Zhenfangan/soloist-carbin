"""AddTaskDialog — 添加任务弹窗。

像素弹窗包含: 任务描述 PixelInput + 目标数量 PixelStepper + 确认/取消按钮。
输入验证: 任务描述非空、目标数量 ≥ 1。
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
    CARD_PADDING,
    CARD_WHITE,
    COLORS,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    GRID_UNIT,
    TEXT_BROWN,
    TEXT_GRAY,
)


class AddTaskDialog(ModalView):  # type: ignore[misc]
    """添加任务弹窗 (像素风全屏 ModalView + 中央 320×280 卡片)。

    设计:
    - ModalView 占据整窗 (size_hint=(1, 1)) — 半透明遮罩覆盖背景
    - 中央卡片 FloatLayout (320×280) 用 pos_hint center 居中
    - auto_dismiss=True — 点击卡片外区域 dismiss

    用法:
        dialog = AddTaskDialog(on_add=lambda desc, qty: create_task(desc, qty))
        dialog.open()
    """

    def __init__(
        self,
        on_add: Callable[[str, int], Any] | None = None,
        initial_desc: str = "",
        initial_qty: int = 1,
        title_text: str = "添加任务",
        confirm_text: str = "确认",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.background = ""
        self.background_color = (0, 0, 0, 0)
        self.auto_dismiss = True
        self._on_add = on_add
        self._initial_desc = initial_desc
        self._initial_qty = initial_qty
        self._title_text = title_text
        self._confirm_text = confirm_text

        root = FloatLayout()
        self.add_widget(root)

        # 半透明遮罩
        with root.canvas.before:
            Color(0, 0, 0, 0.5)
            self._mask_rect = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_mask, pos=self._update_mask)

        # 弹窗卡片
        card_w = 320
        card_h = 280

        card = FloatLayout(
            size_hint=(None, None),
            size=(card_w, card_h),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )

        # 卡片边框 + 阴影
        with card.canvas.before:
            Color(*self._to_rgba(COLORS["SHADOW_BLACK"]))
            Rectangle(pos=(card.x + 2, card.y - 2), size=(card.width, card.height))
            Color(*self._to_rgba(CARD_WHITE))
            Rectangle(pos=(card.x, card.y), size=(card.width, card.height))
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(card.x, card.y + card_h - BORDER_WIDTH), size=(card_w, BORDER_WIDTH))
            Rectangle(pos=(card.x, card.y), size=(BORDER_WIDTH, card_h))
            Color(*self._to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(card.x, card.y), size=(card_w, BORDER_WIDTH))
            Rectangle(pos=(card.x + card_w - BORDER_WIDTH, card.y), size=(BORDER_WIDTH, card_h))

        card.bind(pos=self._redraw_card, size=self._redraw_card)
        self._card = card

        # 标题
        title_label = Label(
            text=self._title_text,
            font_size=FONT_SIZE_TITLE,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=40,
            pos_hint={"x": 0, "y": 1 - 0.18},
            halign="center",
            valign="middle",
        )

        # 任务描述输入
        desc_label = Label(
            text="任务描述",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_GRAY),
            size_hint=(1, None),
            height=20,
            pos_hint={"x": 0.05, "y": 0.72},
            halign="left",
            valign="middle",
        )

        self._desc_input = PixelInput(
            hint_text="例如: 写 3 篇文章",
            value=self._initial_desc,
            size_hint=(None, None),
            size=(card_w - CARD_PADDING * 2, 40),
            pos_hint={"center_x": 0.5, "y": 0.58},
        )

        # 目标数量
        qty_label = Label(
            text="目标数量",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_GRAY),
            size_hint=(1, None),
            height=20,
            pos_hint={"x": 0.05, "y": 0.42},
            halign="left",
            valign="middle",
        )

        self._qty_stepper = PixelStepper(
            value=max(1, self._initial_qty),
            min_value=1,
            max_value=99,
            size_hint=(None, None),
            pos_hint={"center_x": 0.5, "y": 0.25},
        )

        # 验证错误提示
        self._error_label = Label(
            text="",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(COLORS["SHADOW_BLACK"]),
            size_hint=(1, None),
            height=20,
            pos_hint={"x": 0.05, "y": 0.12},
            halign="left",
            valign="middle",
        )

        # 按钮
        btn_layout = BoxLayout(
            orientation="horizontal",
            spacing=GRID_UNIT * 2,
            size_hint=(1, None),
            height=40,
            pos_hint={"x": 0, "y": 0.01},
            padding=[CARD_PADDING, 0],
        )

        cancel_btn = PixelButton(
            text="取消",
            color=COLORS["CARD_SHADOW"],
            size_mode="small",
            size_hint=(1, None),
        )
        cancel_btn.bind(on_press=lambda _: self._handle_cancel())

        confirm_btn = PixelButton(
            text=self._confirm_text,
            color=COLORS["PRIMARY_YELLOW"],
            size_mode="small",
            size_hint=(1, None),
        )
        confirm_btn.bind(on_press=lambda _: self._handle_confirm())

        btn_layout.add_widget(cancel_btn)
        btn_layout.add_widget(confirm_btn)

        card.add_widget(title_label)
        card.add_widget(desc_label)
        card.add_widget(self._desc_input)
        card.add_widget(qty_label)
        card.add_widget(self._qty_stepper)
        card.add_widget(self._error_label)
        card.add_widget(btn_layout)
        root.add_widget(card)

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    @property
    def font_size(self) -> Any:
        return self._font_size

    def _update_mask(self, instance: Any, value: Any) -> None:
        self._mask_rect.size = instance.size
        self._mask_rect.pos = instance.pos

    def _redraw_card(self, instance: Any, value: Any) -> None:
        instance.canvas.before.clear()
        bw = BORDER_WIDTH
        x, y = instance.pos
        w, h = instance.size

        with instance.canvas.before:
            Color(*self._to_rgba(COLORS["SHADOW_BLACK"]))
            Rectangle(pos=(x + 2, y - 2), size=(w, h))
            Color(*self._to_rgba(CARD_WHITE))
            Rectangle(pos=(x, y), size=(w, h))
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(x, y + h - bw), size=(w, bw))
            Rectangle(pos=(x, y), size=(bw, h))
            Color(*self._to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(x, y), size=(w, bw))
            Rectangle(pos=(x + w - bw, y), size=(bw, h))

    def _handle_confirm(self) -> None:
        desc = self._desc_input.value.strip()
        qty = self._qty_stepper.value

        # 验证
        if not desc:
            self._error_label.text = "请输入任务描述"
            return
        if qty < 1:
            self._error_label.text = "目标数量不能少于 1"
            return

        if self._on_add:
            self._on_add(desc, qty)
        self.dismiss()

    def _handle_cancel(self) -> None:
        self.dismiss()
