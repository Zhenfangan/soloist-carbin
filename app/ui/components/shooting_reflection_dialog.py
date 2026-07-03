"""ShootingReflectionDialog — 拍摄复盘弹窗。

4 个字段：拍了什么 / 在哪拍 / 顺不顺(3 选 1) / 感想。
提交后回调 on_submit(answers)，answers 键与 ShootingService.submit_reflection 对齐：
content / location / smoothness(smooth|normal|rough) / thoughts。
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
from app.ui.scale_util import scale_wrap
from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_PADDING,
    CARD_SHADOW,
    CARD_WHITE,
    COLORS,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    GRID_UNIT,
    SEMANTIC_COLORS,
    TEXT_BROWN,
)

_SMOOTH_COLOR = SEMANTIC_COLORS["shooting"]["border"]  # 选中态：暖橙
_SMOOTHNESS_OPTIONS = [("顺利", "smooth"), ("一般", "normal"), ("糟心", "rough")]


class ShootingReflectionDialog(ModalView):  # type: ignore[misc]
    """拍摄复盘弹窗。"""

    def __init__(
        self,
        on_submit: Callable[[dict[str, str]], Any] | None = None,
        on_cancel: Callable[[], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.background = ""
        self.background_color = (0, 0, 0, 0)
        self.auto_dismiss = True

        self._on_submit = on_submit
        self._on_cancel = on_cancel
        self._smoothness = "normal"
        self._smooth_btns: dict[str, PixelButton] = {}

        root = FloatLayout()
        self.add_widget(root)

        with root.canvas.before:
            Color(0, 0, 0, 0.5)
            self._mask_rect = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_mask, pos=self._update_mask)

        card_w, card_h = 340, 410
        card = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            size=(card_w, card_h),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            padding=[CARD_PADDING, CARD_PADDING],
            spacing=GRID_UNIT,
        )
        with card.canvas.before:
            pass
        card.bind(pos=self._redraw_card, size=self._redraw_card)
        self._card = card

        # 标题
        card.add_widget(Label(
            text="拍摄复盘",
            font_size=FONT_SIZE_TITLE + 2,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=36,
            halign="center",
            valign="middle",
        ))

        # 三个文本字段
        self._content_input = PixelInput(hint_text="拍了什么？", size_hint=(1, None), height=40)
        self._location_input = PixelInput(hint_text="在哪拍的？", size_hint=(1, None), height=40)
        card.add_widget(self._content_input)
        card.add_widget(self._location_input)

        # 顺利度 3 选 1
        card.add_widget(Label(
            text="拍得顺不顺？",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_BROWN, 0.8),
            size_hint=(1, None),
            height=22,
            halign="center",
            valign="middle",
        ))
        smooth_row = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=40,
            spacing=GRID_UNIT,
        )
        for label, value in _SMOOTHNESS_OPTIONS:
            btn = PixelButton(
                text=label,
                color=CARD_SHADOW,
                size_mode="small",
                font_size=FONT_SIZE_BODY,
                size_hint=(1, None),
            )
            btn.bind(on_press=lambda _w, v=value: self._select_smoothness(v))
            self._smooth_btns[value] = btn
            smooth_row.add_widget(btn)
        card.add_widget(smooth_row)
        self._select_smoothness("normal")  # 默认高亮"一般"

        # 感想
        self._thoughts_input = PixelInput(hint_text="有什么感想？", size_hint=(1, None), height=40)
        card.add_widget(self._thoughts_input)

        # 按钮栏
        btn_row = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=48,
            spacing=GRID_UNIT * 2,
        )
        cancel_btn = PixelButton(
            text="取消", color=CARD_SHADOW, size_mode="small",
            font_size=FONT_SIZE_BODY, size_hint=(1, None),
        )
        cancel_btn.bind(on_press=lambda _w: self._handle_cancel())
        submit_btn = PixelButton(
            text="提交复盘", color=COLORS["PRIMARY_YELLOW"], size_mode="small",
            font_size=FONT_SIZE_BODY, size_hint=(1, None),
        )
        submit_btn.bind(on_press=lambda _w: self._handle_submit())
        btn_row.add_widget(cancel_btn)
        btn_row.add_widget(submit_btn)
        card.add_widget(btn_row)

        root.add_widget(scale_wrap(card))

    # ── 交互 ──────────────────────────────────────────────

    def _select_smoothness(self, value: str) -> None:
        """选中某个顺利度选项 — 更新状态并重着色三个按钮。"""
        self._smoothness = value
        for v, btn in self._smooth_btns.items():
            btn.set_color(_SMOOTH_COLOR if v == value else CARD_SHADOW)

    def _handle_submit(self) -> None:
        answers = {
            "content": self._content_input.text,
            "location": self._location_input.text,
            "smoothness": self._smoothness,
            "thoughts": self._thoughts_input.text,
        }
        if self._on_submit:
            self._on_submit(answers)
        self.dismiss()

    def _handle_cancel(self) -> None:
        if self._on_cancel:
            self._on_cancel()
        self.dismiss()

    # ── 绘制 ──────────────────────────────────────────────

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
