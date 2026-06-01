"""ConfirmDialog — 通用像素边框确认弹窗。

含标题、正文、确认/取消两个 PixelButton，背景半透明黑遮罩。
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
    FONT_SIZE_BODY,
    FONT_SIZE_TITLE,
    GRID_UNIT,
    TEXT_BROWN,
)


class ConfirmDialog(ModalView):  # type: ignore[misc]
    """通用像素边框确认弹窗。

    用法:
        dialog = ConfirmDialog(
            title="确认删除",
            message="确定要删除这条任务吗？",
            on_confirm=lambda: delete_task(),
            on_cancel=lambda: print("cancelled"),
        )
        dialog.open()
    """

    def __init__(
        self,
        title: str = "",
        message: str = "",
        confirm_text: str = "确认",
        cancel_text: str = "取消",
        confirm_color: str = COLORS["PRIMARY_YELLOW"],
        on_confirm: Callable[[], Any] | None = None,
        on_cancel: Callable[[], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.background = ""
        self.background_color = (0, 0, 0, 0)
        self.auto_dismiss = True

        self._on_confirm = on_confirm
        self._on_cancel = on_cancel

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
        card_h = 200

        card = FloatLayout(
            size_hint=(None, None),
            size=(card_w, card_h),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )

        # 卡片像素边框 + 阴影
        with card.canvas.before:
            # 阴影
            Color(*self._to_rgba(COLORS["SHADOW_BLACK"]))
            Rectangle(pos=(card.x + 2, card.y - 2), size=(card.width, card.height))
            # 卡片背景
            Color(*self._to_rgba(CARD_WHITE))
            Rectangle(pos=(card.x, card.y), size=(card.width, card.height))
            # 凸起边框: 亮面 top+left
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(card.x, card.y + card_h - BORDER_WIDTH), size=(card_w, BORDER_WIDTH))
            Rectangle(pos=(card.x, card.y), size=(BORDER_WIDTH, card_h))
            # 暗面 bottom+right
            Color(*self._to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(card.x, card.y), size=(card_w, BORDER_WIDTH))
            Rectangle(pos=(card.x + card_w - BORDER_WIDTH, card.y), size=(BORDER_WIDTH, card_h))

        card.bind(pos=self._redraw_card, size=self._redraw_card)
        self._card = card

        # 标题
        title_label = Label(
            text=title,
            font_size=FONT_SIZE_TITLE,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=40,
            pos_hint={"x": 0, "y": 1 - 0.22},
            halign="center",
            valign="middle",
        )

        # 正文
        msg_label = Label(
            text=message,
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=60,
            pos_hint={"x": 0, "y": 0.22},
            halign="center",
            valign="top",
            text_size=(card_w - 2 * CARD_PADDING, None),
        )

        # 按钮栏
        btn_layout = BoxLayout(
            orientation="horizontal",
            spacing=GRID_UNIT * 2,
            size_hint=(1, None),
            height=48,
            pos_hint={"x": 0, "y": 0},
            padding=[CARD_PADDING, 0],
        )

        cancel_btn = PixelButton(
            text=cancel_text,
            color=COLORS["CARD_SHADOW"],
            size_mode="small",
            size_hint=(1, None),
        )
        cancel_btn.bind(on_press=lambda _: self._handle_cancel())

        confirm_btn = PixelButton(
            text=confirm_text,
            color=confirm_color,
            size_mode="small",
            size_hint=(1, None),
        )
        confirm_btn.bind(on_press=lambda _: self._handle_confirm())

        btn_layout.add_widget(cancel_btn)
        btn_layout.add_widget(confirm_btn)

        card.add_widget(title_label)
        card.add_widget(msg_label)
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
            Color(*self._to_rgba(COLORS["SHADOW_BLACK"]))
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
        if self._on_confirm:
            self._on_confirm()
        self.dismiss()

    def _handle_cancel(self) -> None:
        if self._on_cancel:
            self._on_cancel()
        self.dismiss()
