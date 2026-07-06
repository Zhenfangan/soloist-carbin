"""RestDayCard — 休息日展示卡。

在签到页替代三个时段卡的位置, 休息期内(对赌结算后手动指定天数)展示:
"今日休息" + 小兔动画, 不含任何按钮 —— 休息日不需要做任何操作, 期满自动恢复。
"""

from __future__ import annotations

from typing import Any

from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from app.ui.components.glass_bg import draw_glass_card_bg
from app.ui.components.sequence_sprite import SequenceSprite
from app.ui.tokens import (
    CARD_PADDING,
    FONT_SIZE_BODY,
    FONT_SIZE_TITLE,
    GRID_UNIT,
    TEXT_BROWN,
    TEXT_GRAY,
)

_ANIM_SIZE = 96
_CARD_HEIGHT = 160


class RestDayCard(BoxLayout):  # type: ignore[misc]
    """休息日卡片 — 垂直 BoxLayout: 提示文字 + 小兔动画, 无按钮。"""

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", _CARD_HEIGHT)
        kwargs.setdefault("padding", [CARD_PADDING, GRID_UNIT])
        kwargs.setdefault("spacing", GRID_UNIT // 2)
        super().__init__(**kwargs)

        self._hint_label = Label(
            text="今日休息",
            font_size=FONT_SIZE_TITLE,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=32,
            halign="center",
            valign="middle",
            bold=True,
        )
        self.add_widget(self._hint_label)

        self._sub_label = Label(
            text="好好休息，攒足元气再出发～",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_GRAY),
            size_hint=(1, None),
            height=24,
            halign="center",
            valign="middle",
        )
        self.add_widget(self._sub_label)

        anim_wrap = AnchorLayout(
            size_hint=(1, None),
            height=_ANIM_SIZE,
            anchor_x="center",
            anchor_y="center",
        )
        self._anim = SequenceSprite(
            "rabbit",
            fps=4.0,
            autoplay=True,
            size_hint=(None, None),
            size=(_ANIM_SIZE, _ANIM_SIZE),
        )
        anim_wrap.add_widget(self._anim)
        self.add_widget(anim_wrap)

        self.bind(pos=self._redraw_bg, size=self._redraw_bg)

    @property
    def natural_height(self) -> int:
        """卡片应有的高度(供外部显隐时设置，避免硬编码覆盖)。"""
        return _CARD_HEIGHT

    def set_animation_active(self, active: bool) -> None:
        """控制精灵动画播放/暂停。卡片隐藏时(非休息日)应暂停避免空转 Clock。"""
        if active and not self._anim.is_playing:
            self._anim.play()
        elif not active and self._anim.is_playing:
            self._anim.stop()

    def _redraw_bg(self, *_args: Any) -> None:
        draw_glass_card_bg(self, border_light="#FFFFFF", border_dark="#C8D8E0")

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)
