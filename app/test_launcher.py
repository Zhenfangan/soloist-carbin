"""临时测试启动器 — 验证 UI 页面能否正常渲染。"""

from __future__ import annotations

from kivy.config import Config

Config.set("graphics", "width", "420")
Config.set("graphics", "height", "750")

# ruff: noqa: E402  (Kivy Config must be set before importing kivy modules)
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
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

        # 底部 Tab 栏
        root = BoxLayout(orientation="vertical")

        # 内容区
        content = BoxLayout()
        content.add_widget(self.sm)
        root.add_widget(content)

        # 简易底部导航
        nav = BoxLayout(orientation="horizontal", size_hint=(1, None), height=56)
        tabs = [
            ("打卡", "checkin", PRIMARY_YELLOW),
            ("历史", "history", "#E0E0E0"),
            ("对赌", "bet", "#E0E0E0"),
            ("设置", "settings", "#E0E0E0"),
        ]
        self._tab_btns = []
        for text, name, color in tabs:
            btn = Button(
                text=text,
                background_normal="",
                background_color=self._to_rgba(color),
                color=self._to_rgba(TEXT_BROWN),
                font_size=FONT_SIZE_SMALL,
                size_hint=(1, 1),
            )
            btn.bind(on_press=lambda _, n=name: self._switch_tab(n))
            nav.add_widget(btn)
            self._tab_btns.append((btn, name))

        root.add_widget(nav)
        return root

    def _switch_tab(self, name: str):
        self.sm.current = name
        for btn, n in self._tab_btns:
            if n == name:
                btn.background_color = self._to_rgba(PRIMARY_YELLOW)
            else:
                btn.background_color = self._to_rgba("#E0E0E0")

    def _wrap_screen(self, widget, name: str):
        screen = Screen(name=name)
        screen.add_widget(widget)
        return screen

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0):
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)


if __name__ == "__main__":
    TestLauncher().run()
