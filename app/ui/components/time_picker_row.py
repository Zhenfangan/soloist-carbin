"""TimePickerRow — 单条时间设置行。

左侧标签 + 右侧时间值按钮，点击弹出时间选择器。
"""

from __future__ import annotations

from typing import Any

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from app.ui.components.pixel_button import PixelButton
from app.ui.components.pixel_time_picker import PixelTimePicker
from app.ui.tokens import (
    CARD_PADDING,
    FONT_SIZE_BODY,
    TEXT_BROWN,
)


class TimePickerRow(BoxLayout):  # type: ignore[misc]
    """单条时间设置行。

    用法:
        row = TimePickerRow("上午上班", "morning_start", settings_service)
        row.bind(height=...)  # 高度自动计算

    布局:
        ┌──────────────────────────┐
        │  上午上班      [09:00]    │
        └──────────────────────────┘
    """

    def __init__(
        self,
        label: str = "",
        key: str = "",
        settings_service: Any = None,
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

        # 右侧时间值按钮
        current_value = self._get_current_value()
        self._value_btn = PixelButton(
            text=current_value,
            size_mode="small",
            size_hint=(None, 1),
            width=100,
        )
        self._value_btn.bind(on_press=lambda _: self._open_picker())

        self.add_widget(self._label)
        self.add_widget(self._value_btn)

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    def _get_current_value(self) -> str:
        if self._settings_service and self._key:
            return self._settings_service.get(self._key)  # type: ignore[no-any-return]
        return "09:00"

    def _open_picker(self) -> None:
        current = self._get_current_value()
        picker = PixelTimePicker(
            initial_time=current,
            on_select=self._on_time_selected,
        )
        picker.open()

    def _on_time_selected(self, time_str: str) -> None:
        self._value_btn.text = time_str
        if self._settings_service and self._key:
            self._settings_service.set(self._key, time_str)

    def refresh(self) -> None:
        """刷新显示值（当外部修改时调用）。"""
        self._value_btn.text = self._get_current_value()
