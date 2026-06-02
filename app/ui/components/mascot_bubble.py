"""MascotBubble — 像素角色 + 对话气泡组件。

像素角色 (16×16 网格放大至 64×64) + 像素对话气泡 (锯齿边角)。
"""

from __future__ import annotations

from typing import Any

from kivy.graphics import Color, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label

from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_PADDING,
    CARD_WHITE,
    COLORS,
    FONT_SIZE_BODY,
    GRID_UNIT,
    SPRITE_SIZE,
    TEXT_BROWN,
)


class MascotBubble(FloatLayout):  # type: ignore[misc]
    """像素角色 + 对话气泡。

    属性:
        mascot_id: 角色 ID (dudu/wengweng/tuantuan/wangzai/migu)
        message: 气泡内文字
        position: 气泡位置 ('left'=角色左侧 / 'right'=角色右侧)
    """

    def __init__(
        self,
        mascot_id: str = "dudu",
        message: str = "",
        position: str = "right",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.size_hint = (1, None)
        self.height = SPRITE_SIZE + GRID_UNIT * 2

        self._mascot_id = mascot_id
        self._message = message
        self._bubble_position = position

        # 角色 sprite
        self._sprite = Image(
            size_hint=(None, None),
            size=(SPRITE_SIZE, SPRITE_SIZE),
            pos_hint={"x": 0, "y": 0.5},
            allow_stretch=True,
            keep_ratio=False,
        )
        self._load_sprite_texture(mascot_id)

        # 对话气泡
        self._bubble_label = Label(
            text=message,
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, None),
            size=(200, 44),
            pos_hint={"x": 0, "y": 0.5},
            halign="left",
            valign="middle",
            text_size=(200 - CARD_PADDING, None),
        )

        self.add_widget(self._sprite)
        self.add_widget(self._bubble_label)

        self.bind(pos=self._redraw, size=self._redraw)

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    @property
    def message(self) -> str:
        return self._message

    @message.setter
    def message(self, text: str) -> None:
        self._message = text
        self._bubble_label.text = text

    def set_mascot(self, mascot_id: str) -> None:
        """切换角色。"""
        self._mascot_id = mascot_id
        self._load_sprite_texture(mascot_id)

    def _load_sprite_texture(self, mascot_id: str) -> None:
        """加载角色精灵第一帧作为静态展示。"""
        try:
            from app.ui.assets.loader import SpriteLoader
            frame = SpriteLoader.load_frame(mascot_id, 0)
            if frame and frame.texture:
                self._sprite.texture = frame.texture
        except Exception:
            pass

    def _redraw(self, *args: Any) -> None:
        """重绘气泡的像素边框。"""
        self.canvas.before.clear()
        bw = BORDER_WIDTH

        bubble_x = SPRITE_SIZE + GRID_UNIT if self._bubble_position == "right" else 0
        bubble_w = self.width - SPRITE_SIZE - GRID_UNIT
        bubble_h = 44
        bubble_y = (self.height - bubble_h) / 2

        if self._bubble_position == "right":
            sprite_x = 0
        else:
            sprite_x = self.width - SPRITE_SIZE

        with self.canvas.before:
            # 气泡背景
            Color(*self._to_rgba(CARD_WHITE))
            Rectangle(pos=(bubble_x, bubble_y), size=(bubble_w, bubble_h))
            # 气泡凸起边框
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(bubble_x, bubble_y + bubble_h - bw), size=(bubble_w, bw))
            Rectangle(pos=(bubble_x, bubble_y), size=(bw, bubble_h))
            Color(*self._to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(bubble_x, bubble_y), size=(bubble_w, bw))
            Rectangle(pos=(bubble_x + bubble_w - bw, bubble_y), size=(bw, bubble_h))

        # 更新子 Widget 位置
        self._sprite.pos = (sprite_x, (self.height - SPRITE_SIZE) / 2)
        self._bubble_label.pos = (bubble_x + CARD_PADDING // 2, bubble_y + 4)
        self._bubble_label.size = (bubble_w - CARD_PADDING, bubble_h - 8)
