"""ReportPreview — 战报全屏弹层。

Y 轴从底部滑入，包含战报长图预览 + 保存/结算按钮。
"""

from __future__ import annotations

from typing import Any

from kivy.animation import Animation
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView

from app.ui.components.pixel_button import PixelButton
from app.ui.tokens import (
    BG_CREAM,
    CARD_PADDING,
    FONT_SIZE_TITLE,
    GRID_UNIT,
    TEXT_BROWN,
)


def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)


class ReportPreview(ModalView):  # type: ignore[misc]
    """全屏战报预览弹层。

    Args:
        image_path: 战报 PNG 图片路径
        date_str: 日期字符串 (如 "2026.6.1")
        on_save: 保存回调
        on_settle: 结算回调
    """

    def __init__(
        self,
        image_path: str = "",
        date_str: str = "",
        on_save: Any = None,
        on_settle: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.background = ""
        self.background_color = (0, 0, 0, 0)

        root = FloatLayout()

        # 半透明遮罩
        with root.canvas.before:
            Color(0, 0, 0, 0.6)
            self._mask = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_mask, pos=self._update_mask)

        # 弹层主体
        panel = FloatLayout(
            size_hint=(1, 0.9),
            pos_hint={"x": 0, "y": 0},
        )
        with panel.canvas.before:
            Color(*_to_rgba(BG_CREAM))
            Rectangle(pos=panel.pos, size=panel.size)
        panel.bind(pos=lambda w, _: w.canvas.before.clear() or self._draw_panel_bg(w),
                   size=lambda w, _: w.canvas.before.clear() or self._draw_panel_bg(w))

        # 顶部标题
        title = Label(
            text=f"{date_str} 战报" if date_str else "今日战报",
            font_size=FONT_SIZE_TITLE,
            color=_to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=48,
            pos_hint={"x": 0, "y": 0.92},
            halign="center",
            valign="middle",
        )
        panel.add_widget(title)

        # 战报图片预览 (可滚动)
        scroll = ScrollView(
            size_hint=(1, None),
            pos_hint={"x": 0, "y": 0.12},
        )
        # 计算高度: 弹层90% - 标题48 - 底部按钮80
        panel.bind(size=lambda w, v: setattr(scroll, "height", w.height * 0.9 - 48 - 80))

        if image_path:
            img = Image(source=image_path, size_hint=(1, None), height=400)
            scroll.add_widget(img)

        panel.add_widget(scroll)

        # 底部按钮
        btn_area = BoxLayout(
            orientation="horizontal",
            spacing=GRID_UNIT * 2,
            size_hint=(1, None),
            height=56,
            pos_hint={"x": 0, "y": 0.01},
            padding=[CARD_PADDING, 6],
        )

        save_btn = PixelButton(
            text="保存至相册",
            color="#60C8FF",
            size_mode="normal",
            size_hint=(1, None),
        )
        if on_save:
            save_btn.bind(on_press=lambda _: on_save())

        settle_btn = PixelButton(
            text="退出并结算",
            color="#50E8B0",
            size_mode="normal",
            size_hint=(1, None),
        )
        settle_btn.bind(on_press=lambda _: self._handle_settle(on_settle))

        btn_area.add_widget(save_btn)
        btn_area.add_widget(settle_btn)
        panel.add_widget(btn_area)

        root.add_widget(panel)
        self.add_widget(root)

        # 入场动画
        panel.y = -panel.height
        anim = Animation(y=0, duration=0.25, t="out_quad")
        Clock = __import__("kivy.clock", fromlist=["Clock"]).Clock
        Clock.schedule_once(lambda dt: anim.start(panel), 0.05)

    def _update_mask(self, instance: Any, value: Any) -> None:
        self._mask.size = instance.size
        self._mask.pos = instance.pos

    @staticmethod
    def _draw_panel_bg(widget: Any) -> None:
        """绘制面板背景。"""
        with widget.canvas.before:
            Color(*_to_rgba(BG_CREAM))
            Rectangle(pos=widget.pos, size=widget.size)

    def _handle_settle(self, on_settle: Any) -> None:
        if on_settle:
            on_settle()
        self.dismiss()
