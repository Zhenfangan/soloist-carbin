"""AmountPickerRow — 单条金额设置行。

左侧标签 + 右侧金额值按钮，点击弹出数字输入弹窗。
支持 penalty 模式 (自动加负号显示)。
"""

from __future__ import annotations

from typing import Any

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from app.ui.components.pixel_button import PixelButton
from app.ui.components.pixel_number_dialog import PixelNumberDialog
from app.ui.tokens import (
    CARD_PADDING,
    FONT_SIZE_BODY,
    TEXT_BROWN,
)


class AmountPickerRow(BoxLayout):  # type: ignore[misc]
    """单条金额设置行。

    用法:
        row = AmountPickerRow("迟到罚款", "late_penalty", settings_service, is_penalty=True)

    is_penalty=True 时，显示值自动添加负号前缀 (如 "-10")，
    但存储的值保持正数 ("10")。

    布局:
        ┌──────────────────────────┐
        │  迟到罚款       [-10]    │
        └──────────────────────────┘
    """

    def __init__(
        self,
        label: str = "",
        key: str = "",
        settings_service: Any = None,
        is_penalty: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            orientation="horizontal",
            spacing=CARD_PADDING,
            padding=[CARD_PADDING, 4],
            size_hint=(1, None),
            height=44,
            **kwargs,
        )
        self._label_text = label
        self._key = key
        self._settings_service = settings_service
        self._is_penalty = is_penalty

        # 左侧文字标签
        self._label = Label(
            text=label,
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(0.6, 1),
            halign="left",
            valign="middle",
            text_size=(200, None),
        )

        # 右侧金额值按钮
        current_value = self._get_display_value()
        self._value_btn = PixelButton(
            text=current_value,
            size_mode="small",
            size_hint=(None, 1),
            width=100,
        )
        self._value_btn.bind(on_press=lambda _: self._open_dialog())

        self.add_widget(self._label)
        self.add_widget(self._value_btn)

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    def _get_raw_value(self) -> str:
        """从 service 读取原始存储值。"""
        if self._settings_service and self._key:
            return self._settings_service.get(self._key)  # type: ignore[no-any-return]
        return "0"

    def _get_display_value(self) -> str:
        """获取显示用的值（penalty 模式加负号）。"""
        raw = self._get_raw_value()
        if self._is_penalty and raw and raw != "0":
            return f"-{raw}"
        return raw

    def _open_dialog(self) -> None:
        raw = self._get_raw_value()
        dlg = PixelNumberDialog(
            title=self._label_text,
            initial_value=raw,
            on_confirm=self._on_value_confirmed,
        )
        dlg.open()

    def _on_value_confirmed(self, value_str: str) -> None:
        # 去掉可能的负号再存储
        clean = value_str.lstrip("-")
        if clean == "":
            clean = "0"
        if self._settings_service and self._key:
            self._settings_service.set(self._key, clean)
        self._value_btn.text = self._get_display_value()

    def refresh(self) -> None:
        """刷新显示值。"""
        self._value_btn.text = self._get_display_value()
