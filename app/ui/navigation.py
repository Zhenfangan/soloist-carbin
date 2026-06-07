"""全局导航系统 — BottomTabBar + AppScreenManager。

底部导航栏 4 个 Tab，像素图标 + 小字标签，选中明黄高亮。
"""

from __future__ import annotations

from typing import Any

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager

from app.ui.assets.loader import IconLoader
from app.ui.tokens import (
    FONT_SIZE_SMALL,
    NAV_HEIGHT,
    PRIMARY_YELLOW,
    TEXT_GRAY,
)


def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)


class TabButton(Button):  # type: ignore[misc]
    """单个 Tab 按钮 — 像素图标 + 小字标签。"""

    def __init__(self, icon_name: str, text: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.size_hint = (1, 1)

        # 图标
        self._icon = KivyImage(
            source=str(IconLoader.get_icon_path(icon_name)),
            size_hint=(None, None),
            size=(32, 32),
            pos_hint={"center_x": 0.5, "y": 0.35},
        )
        self._icon.allow_stretch = True
        self._icon.keep_ratio = True

        # 标签
        self._tab_label = Label(
            text=text,
            font_size=FONT_SIZE_SMALL,
            color=_to_rgba(TEXT_GRAY),
            size_hint=(1, None),
            height=20,
            pos_hint={"x": 0, "y": -0.1},
            halign="center",
            valign="top",
        )

        layout = BoxLayout(orientation="vertical")
        layout.add_widget(self._icon)
        layout.add_widget(self._tab_label)
        self.add_widget(layout)
        # Button 不是 Layout, 不会自动把 size/pos 派发给子 BoxLayout
        # 必须显式 bind, 否则 layout 永远停在默认 (0,0) (100,100), 4 个 tab 视觉重叠在左下角
        self.bind(size=layout.setter("size"), pos=layout.setter("pos"))
        layout.size = self.size
        layout.pos = self.pos

    def set_active(self, active: bool) -> None:
        if active:
            self._tab_label.color = _to_rgba(PRIMARY_YELLOW)
        else:
            self._tab_label.color = _to_rgba(TEXT_GRAY)

    def set_color_icon(self, color: tuple[float, float, float, float]) -> None:
        self._icon.color = color


TAB_CONFIG: list[dict[str, str]] = [
    {"name": "checkin", "icon": "tab_checkin", "text": "打卡"},
    {"name": "history", "icon": "tab_history", "text": "历史"},
    {"name": "bet", "icon": "tab_bet", "text": "对赌"},
    {"name": "settings", "icon": "tab_settings", "text": "设置"},
]


class BottomTabBar(BoxLayout):  # type: ignore[misc]
    """底部导航栏。

    固定高度 56px，4 个 Tab，选中明黄高亮，未选中灰褐。
    """

    def __init__(self, screen_manager: ScreenManager, **kwargs: Any) -> None:
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", NAV_HEIGHT)
        super().__init__(**kwargs)
        self._sm = screen_manager
        self._tabs: list[TabButton] = []
        self._active_index = 0

        for i, cfg in enumerate(TAB_CONFIG):
            btn = TabButton(icon_name=cfg["icon"], text=cfg["text"])
            btn.bind(on_press=lambda _, idx=i: self.switch_tab(idx))
            self.add_widget(btn)
            self._tabs.append(btn)

        # 默认选中第一个
        self._set_active(0)

    def switch_tab(self, index: int) -> None:
        """切换到指定 Tab 并显示对应页面。"""
        if index == self._active_index:
            return
        old_index = self._active_index
        self._set_active(index)
        self._sm.current = TAB_CONFIG[index]["name"]
        # 页面切换动画
        self._sm.transition.direction = "left" if index > old_index else "right"
        self._sm.transition.duration = 0.2

    def _set_active(self, index: int) -> None:
        self._active_index = index
        for i, tab in enumerate(self._tabs):
            tab.set_active(i == index)


class AppScreenManager(ScreenManager):  # type: ignore[misc]
    """Kivy ScreenManager，注册 4 个页面 Screen。

    切换时触发渐隐渐显。
    """

    def __init__(self, screens: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        for name, widget in screens.items():
            screen = Screen(name=name)
            screen.add_widget(widget)
            self.add_widget(screen)

        self.transition.duration = 0.2
