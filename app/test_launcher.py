"""临时测试启动器 — 验证 UI 页面能否正常渲染。"""

from __future__ import annotations

from kivy.config import Config

Config.set("graphics", "width", "420")
Config.set("graphics", "height", "750")

# ruff: noqa: E402  (Kivy Config must be set before importing kivy modules)
from kivy.app import App
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager

from app.db import init_db
from app.repositories.bet_repo import BetRepo
from app.repositories.checkin_repo import CheckinRepo
from app.repositories.ledger_repo import LedgerRepo
from app.repositories.settings_repo import SettingsRepo
from app.repositories.shooting_repo import ShootingRepo
from app.services.bet_service import BetService
from app.services.checkin_service import CheckinService
from app.services.history_service import HistoryService
from app.services.settings_service import SettingsService
from app.ui.screens.bet_screen import BetScreen
from app.ui.screens.checkin_screen import CheckinScreen
from app.ui.screens.history_screen import HistoryScreen
from app.ui.screens.settings_screen import SettingsScreen
from app.ui.tokens import (
    BG_CREAM,
    FONT_SIZE_SMALL,
    PRIMARY_YELLOW,
    TEXT_BROWN,
)
from app.utils.clock import RealClock, set_clock


class TestLauncher(App):
    """临时测试启动器 — 底部按钮切换 4 个页面。"""

    def build(self):
        set_clock(RealClock())
        init_db()
        from app.ui.assets.loader import preload_all
        from app.ui.fonts import apply_global_font
        apply_global_font()
        preload_all()

        self.sm = ScreenManager()

        # 创建各个页面的 Service
        settings_repo = SettingsRepo("soloist.db")
        settings_svc = SettingsService(settings_repo)
        checkin_repo = CheckinRepo("soloist.db")
        checkin_svc = CheckinService(checkin_repo, settings_repo)
        ledger_repo = LedgerRepo("soloist.db")
        bet_svc = BetService(BetRepo("soloist.db"), ledger_repo, settings_repo)
        history_svc = HistoryService(checkin_repo, ledger_repo, ShootingRepo("soloist.db"))

        self.sm.add_widget(self._wrap_screen(CheckinScreen(checkin_service=checkin_svc), "checkin"))
        self.sm.add_widget(self._wrap_screen(HistoryScreen(history_service=history_svc), "history"))
        self.sm.add_widget(self._wrap_screen(BetScreen(bet_service=bet_svc), "bet"))
        self.sm.add_widget(self._wrap_screen(SettingsScreen(settings_service=settings_svc), "settings"))

        # 根布局
        root = BoxLayout(orientation="vertical")

        # 背景色 (对齐 main.py)
        with root.canvas.before:
            Color(*self._to_rgba(BG_CREAM))
            self._bg_rect = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_bg, pos=self._update_bg)

        # 内容区
        content = BoxLayout()
        content.add_widget(self.sm)
        root.add_widget(content)

        # 底部导航（含图标）
        from app.ui.assets.loader import IconLoader

        nav = BoxLayout(orientation="horizontal", size_hint=(1, None), height=56)
        tabs = [
            ("打卡", "checkin", "tab_checkin", PRIMARY_YELLOW),
            ("历史", "history", "tab_history", "#E0E0E0"),
            ("对赌", "bet", "tab_bet", "#E0E0E0"),
            ("设置", "settings", "tab_settings", "#E0E0E0"),
        ]
        self._tab_btns = []
        for text, name, icon_name, init_color in tabs:
            btn = Button(
                background_normal="",
                background_color=self._to_rgba(init_color),
                size_hint=(1, 1),
            )
            btn.bind(on_press=lambda _, n=name: self._switch_tab(n))
            # 图标 + 文字 垂直布局
            inner = BoxLayout(orientation="vertical", padding=[0, 4, 0, 2])
            try:
                icon_path = IconLoader.get_icon_path(icon_name)
                icon = KivyImage(
                    source=str(icon_path),
                    size_hint=(None, None),
                    size=(28, 28),
                    pos_hint={"center_x": 0.5},
                    allow_stretch=True,
                    keep_ratio=True,
                )
                inner.add_widget(icon)
            except Exception:
                pass
            lbl = Label(
                text=text,
                font_size=FONT_SIZE_SMALL,
                color=self._to_rgba(TEXT_BROWN),
                size_hint=(1, None),
                height=20,
                halign="center",
                valign="middle",
            )
            inner.add_widget(lbl)
            btn.add_widget(inner)
            nav.add_widget(btn)
            self._tab_btns.append((btn, name))

        root.add_widget(nav)
        return root

    def _switch_tab(self, name: str):
        self.sm.current = name
        for btn, n in self._tab_btns:
            active = n == name
            btn.background_color = self._to_rgba(PRIMARY_YELLOW if active else "#E0E0E0")
            # 更新图标颜色
            if btn.children:
                inner = btn.children[0]
                if inner.children:
                    for child in inner.children:
                        if isinstance(child, KivyImage):
                            child.color = self._to_rgba(TEXT_BROWN) if active else (0.54, 0.5, 0.47, 1.0)

    def _wrap_screen(self, widget, name: str):
        screen = Screen(name=name)
        screen.add_widget(widget)
        return screen

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0):
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    def _update_bg(self, instance: object, value: object) -> None:
        self._bg_rect.size = instance.size  # type: ignore[union-attr]
        self._bg_rect.pos = instance.pos  # type: ignore[union-attr]


if __name__ == "__main__":
    TestLauncher().run()
