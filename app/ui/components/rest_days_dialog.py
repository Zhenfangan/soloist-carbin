"""RestDaysDialog — 对赌周期结算完成后询问"这个周期辛苦啦, 休息几天?"。

确认 → 从今天起自动进入休息期(签到页显示"今日休息" + 小兔动画, 隐藏其余 UI)。
不休息 → 跳过, 照常开始新周期。
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
from app.ui.components.pixel_stepper import PixelStepper
from app.ui.scale_util import scale_wrap
from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_PADDING,
    CARD_WHITE,
    COLORS,
    FONT_SIZE_BODY,
    FONT_SIZE_TITLE,
    GRID_UNIT,
    TEXT_BROWN,
    TEXT_GRAY,
)

DEFAULT_REST_DAYS = 2


class RestDaysDialog(ModalView):  # type: ignore[misc]
    """休息天数弹窗 (像素风全屏 ModalView + 中央卡片)。

    用法:
        dialog = RestDaysDialog(on_confirm=lambda days: ...)  # days=None 表示不休息
        dialog.open()
    """

    def __init__(
        self,
        on_confirm: Callable[[int | None], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.background = ""
        self.background_color = (0, 0, 0, 0)
        self.auto_dismiss = True
        self._on_confirm = on_confirm

        root = FloatLayout()
        self.add_widget(root)

        with root.canvas.before:
            Color(0, 0, 0, 0.5)
            self._mask_rect = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_mask, pos=self._update_mask)

        card_w, card_h = 320, 240
        card = FloatLayout(
            size_hint=(None, None),
            size=(card_w, card_h),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )
        card.bind(pos=self._redraw_card, size=self._redraw_card)
        self._card = card

        title_label = Label(
            text="这个周期辛苦啦！",
            font_size=FONT_SIZE_TITLE + 2,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=36,
            pos_hint={"x": 0, "y": 1 - 0.18},
            halign="center",
            valign="middle",
        )

        subtitle_label = Label(
            text="休息几天?",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_GRAY),
            size_hint=(1, None),
            height=24,
            pos_hint={"x": 0, "y": 1 - 0.38},
            halign="center",
            valign="middle",
        )

        self._days_stepper = PixelStepper(
            value=DEFAULT_REST_DAYS,
            min_value=1,
            max_value=30,
            size_hint=(None, None),
            pos_hint={"center_x": 0.5, "y": 0.4},
        )

        btn_layout = BoxLayout(
            orientation="horizontal",
            spacing=GRID_UNIT * 2,
            size_hint=(1, None),
            height=40,
            pos_hint={"x": 0, "y": 0.08},
            padding=[CARD_PADDING, 0],
        )

        skip_btn = PixelButton(
            text="不休息",
            color=COLORS["CARD_SHADOW"],
            size_mode="small",
            font_size=FONT_SIZE_BODY,
            size_hint=(1, None),
        )
        skip_btn.bind(on_press=lambda _: self._handle_skip())

        confirm_btn = PixelButton(
            text="确认休息",
            color=COLORS["PRIMARY_YELLOW"],
            size_mode="small",
            font_size=FONT_SIZE_BODY,
            size_hint=(1, None),
        )
        confirm_btn.bind(on_press=lambda _: self._handle_confirm())

        btn_layout.add_widget(skip_btn)
        btn_layout.add_widget(confirm_btn)

        card.add_widget(title_label)
        card.add_widget(subtitle_label)
        card.add_widget(self._days_stepper)
        card.add_widget(btn_layout)
        root.add_widget(scale_wrap(card))

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
            Rectangle(pos=(x + w - bw, y), size=(bw, h))

    def _handle_confirm(self) -> None:
        if self._on_confirm:
            self._on_confirm(self._days_stepper.value)
        self.dismiss()

    def _handle_skip(self) -> None:
        if self._on_confirm:
            self._on_confirm(None)
        self.dismiss()
