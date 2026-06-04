"""Soloist Cabin Pro — Kivy APP 入口。

集成: 像素主题 + 字体加载 + 资源预加载 + 引导流程 + 导航 + 4 个页面。
"""

from __future__ import annotations

from kivy.config import Config

Config.set("graphics", "width", "420")
Config.set("graphics", "height", "750")

from kivy.app import App  # noqa: E402
from kivy.graphics import Color, Rectangle  # noqa: E402
from kivy.uix.boxlayout import BoxLayout  # noqa: E402

from app.db import init_db  # noqa: E402
from app.repositories.bet_repo import BetRepo  # noqa: E402
from app.repositories.checkin_repo import CheckinRepo  # noqa: E402
from app.repositories.ledger_repo import LedgerRepo  # noqa: E402
from app.repositories.settings_repo import SettingsRepo  # noqa: E402
from app.repositories.shooting_repo import ShootingRepo  # noqa: E402
from app.repositories.sync_repo import SyncRepo  # noqa: E402
from app.services.bet_service import BetService  # noqa: E402
from app.services.checkin_service import CheckinService  # noqa: E402
from app.services.history_service import HistoryService  # noqa: E402
from app.services.settings_service import SettingsService  # noqa: E402
from app.services.sync_service import SyncService  # noqa: E402
from app.ui.assets.loader import preload_all  # noqa: E402
from app.ui.fonts import apply_global_font  # noqa: E402
from app.ui.navigation import AppScreenManager, BottomTabBar  # noqa: E402
from app.ui.screens.bet_screen import BetScreen  # noqa: E402
from app.ui.screens.checkin_screen import CheckinScreen  # noqa: E402
from app.ui.screens.history_screen import HistoryScreen  # noqa: E402
from app.ui.screens.onboarding_screen import OnboardingScreen  # noqa: E402
from app.ui.screens.settings_screen import SettingsScreen  # noqa: E402
from app.ui.tokens import BG_CREAM, NAV_HEIGHT  # noqa: E402
from app.utils.clock import SystemClock, set_clock  # noqa: E402


def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)


class SoloistApp(App):  # type: ignore[misc]
    """Soloist Cabin Pro 主 APP。"""

    DB_PATH = "soloist.db"

    def build(self) -> BoxLayout:
        # 初始化时钟
        set_clock(SystemClock())

        # 初始化数据库
        init_db(self.DB_PATH)

        # 加载字体 (全局生效) + 预加载资源
        apply_global_font()
        preload_all()

        # 创建 Service
        settings_repo = SettingsRepo(self.DB_PATH)
        settings_svc = SettingsService(settings_repo)
        checkin_repo = CheckinRepo(self.DB_PATH)
        checkin_svc = CheckinService(checkin_repo, settings_repo)
        ledger_repo = LedgerRepo(self.DB_PATH)
        bet_svc = BetService(BetRepo(self.DB_PATH), ledger_repo, settings_repo)
        history_svc = HistoryService(checkin_repo, ledger_repo, ShootingRepo(self.DB_PATH))

        # 根布局 (垂直: 内容区 + 底部导航)
        self._root = BoxLayout(orientation="vertical")

        # 背景色
        with self._root.canvas.before:
            Color(*_to_rgba(BG_CREAM))
            self._bg_rect = Rectangle(size=self._root.size, pos=self._root.pos)
        self._root.bind(size=self._update_bg, pos=self._update_bg)

        # 判断首次启动
        settings_svc.is_first_launch()
        is_first = settings_svc.get("app_version") == ""

        if is_first:
            # 首次启动 → 引导流程
            self._show_onboarding(settings_svc, checkin_svc, bet_svc, history_svc)
        else:
            # 非首次 → 直接进入主界面
            self._show_main(settings_svc, checkin_svc, bet_svc, history_svc)

        return self._root

    def _update_bg(self, instance: object, value: object) -> None:
        self._bg_rect.size = self._root.size
        self._bg_rect.pos = self._root.pos

    def _show_onboarding(
        self,
        settings_svc: SettingsService,
        checkin_svc: CheckinService,
        bet_svc: BetService,
        history_svc: HistoryService,
    ) -> None:
        """显示首次引导流程。"""
        self._root.clear_widgets()
        onboarding = OnboardingScreen(
            on_finish=lambda: self._on_onboarding_done(settings_svc, checkin_svc, bet_svc, history_svc),
        )
        self._root.add_widget(onboarding)

    def _on_onboarding_done(
        self,
        settings_svc: SettingsService,
        checkin_svc: CheckinService,
        bet_svc: BetService,
        history_svc: HistoryService,
    ) -> None:
        """引导完成，标记并进入主界面。"""
        settings_svc.set("app_version", "1.0.0")
        settings_svc.complete_onboarding()
        self._show_main(settings_svc, checkin_svc, bet_svc, history_svc)

    def _show_main(
        self,
        settings_svc: SettingsService,
        checkin_svc: CheckinService,
        bet_svc: BetService,
        history_svc: HistoryService,
    ) -> None:
        """显示主界面: 底部导航 + 4 个页面。"""
        self._root.clear_widgets()

        # 创建页面
        screens = {
            "checkin": CheckinScreen(checkin_service=checkin_svc),
            "history": HistoryScreen(history_service=history_svc),
            "bet": BetScreen(bet_service=bet_svc),
            "settings": SettingsScreen(settings_service=settings_svc, sync_service=SyncService(SyncRepo(self.DB_PATH))),
        }

        sm = AppScreenManager(screens)

        # 底部导航栏
        tab_bar = BottomTabBar(sm, size_hint=(1, None), height=NAV_HEIGHT)

        # 内容区占满剩余空间，导航栏固定在底部
        self._root.add_widget(sm)
        self._root.add_widget(tab_bar)

    def on_stop(self) -> None:
        """应用退出时清理资源。"""
        # EventBus 取消等清理工作
        pass


def main() -> None:
    SoloistApp().run()


if __name__ == "__main__":
    main()
