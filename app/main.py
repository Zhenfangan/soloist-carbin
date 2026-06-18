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
from kivy.uix.floatlayout import FloatLayout  # noqa: E402
from kivy.uix.image import Image as KivyImage  # noqa: E402
from kivy.core.window import Window  # noqa: E402

from app.db import init_db  # noqa: E402
from app.repositories.bet_repo import BetRepo  # noqa: E402
from app.repositories.checkin_repo import CheckinRepo  # noqa: E402
from app.repositories.ledger_repo import LedgerRepo  # noqa: E402
from app.repositories.settings_repo import SettingsRepo  # noqa: E402
from app.interfaces.notifier import NoOpNotifier  # noqa: E402
from app.repositories.shooting_repo import ShootingRepo  # noqa: E402
from app.repositories.streak_repo import StreakRepo  # noqa: E402
from app.repositories.sync_repo import SyncRepo  # noqa: E402
from app.services.bet_service import BetService  # noqa: E402
from app.services.camera_desktop_mock import DesktopCameraMock  # noqa: E402
from app.services.checkin_service import CheckinService  # noqa: E402
from app.services.history_service import HistoryService  # noqa: E402
from app.services.motivation_service import MotivationService  # noqa: E402
from app.services.penalty_service import PenaltyService  # noqa: E402
from app.services.report_service import ReportService  # noqa: E402
from app.services.settings_service import SettingsService  # noqa: E402
from app.services.sync_service import SyncService  # noqa: E402
from app.ui.assets.landscape import BG_LANDSCAPE, get_grass_overlay_path  # noqa: E402
from app.ui.assets.loader import preload_all  # noqa: E402
from app.ui.fonts import apply_global_font  # noqa: E402
from app.ui.navigation import AppScreenManager, BottomTabBar  # noqa: E402
from app.ui.screens.bet_screen import BetScreen  # noqa: E402
from app.ui.screens.checkin_screen import CheckinScreen  # noqa: E402
from app.ui.screens.history_screen import HistoryScreen  # noqa: E402
from app.ui.screens.onboarding_screen import OnboardingScreen  # noqa: E402
from app.ui.screens.settings_screen import SettingsScreen  # noqa: E402
from app.ui.tokens import BG_CREAM, GRASS_INSET, NAV_HEIGHT  # noqa: E402
from app.utils.clock import SystemClock, set_clock  # noqa: E402


def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)


class _PassthroughImage(KivyImage):  # type: ignore[misc]
    """触控穿透 Image — 与 report_preview._PassthroughImage 完全一致。"""

    def collide_point(self, x: float, y: float) -> bool:  # type: ignore[override]
        return False


def _setup_debug_hooks() -> None:
    """启动诊断 — 仅在 SOLOIST_DEBUG=1 时安装事件日志。

    必须在任何 UI 组件实例化之前调用 (否则装饰只对之后实例化的对象生效)。
    """
    from app.ui.debug.event_logger import install_event_logger
    install_event_logger()


class SoloistApp(App):  # type: ignore[misc]
    """Soloist Cabin Pro 主 APP。"""

    DB_PATH = "soloist.db"

    def build(self) -> FloatLayout:
        # 诊断脚手架 (Wave 2 Phase 1) — 必须在任何 widget 实例化之前
        _setup_debug_hooks()

        # 初始化时钟 (虚拟时间: 周日 08:00 用于调试)
        from app.utils.clock import SimulatedClock
        from datetime import datetime
        set_clock(SimulatedClock(datetime(2026, 6, 14, 8, 0, 0)))

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
        self._camera_svc = DesktopCameraMock()
        ledger_repo = LedgerRepo(self.DB_PATH)
        bet_svc = BetService(BetRepo(self.DB_PATH), ledger_repo, settings_repo)
        shooting_repo = ShootingRepo(self.DB_PATH)
        history_svc = HistoryService(checkin_repo, ledger_repo, shooting_repo)
        self._report_svc = ReportService(checkin_repo, ledger_repo, shooting_repo, settings_repo)
        # 实例化以触发 ATTENDANCE_JUDGED / DAY_FINISHED 事件订阅 (生成罚款/奖励流水)
        self._penalty_svc = PenaltyService(checkin_repo, ledger_repo, settings_repo)
        # 实例化以触发 DAY_FINISHED 事件订阅 (更新 streak) + CheckinScreen 显示连续天数
        self._motivation_svc = MotivationService(
            checkin_repo, StreakRepo(self.DB_PATH), settings_repo, NoOpNotifier()
        )

        # 根布局: FloatLayout，子 widget 按添加顺序从底到顶堆叠
        self._root = FloatLayout()

        # 判断首次启动
        settings_svc.is_first_launch()
        is_first = settings_svc.get("app_version") == ""

        if is_first:
            self._show_onboarding(settings_svc, checkin_svc, bet_svc, history_svc)
        else:
            self._show_main(settings_svc, checkin_svc, bet_svc, history_svc)

        return self._root

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
        """显示主界面: 底部导航 + 4 个页面。

        PS 图层逻辑 (从底到顶):
          Layer 4 (最底): 天空背景 Image
          Layer 3:       内容区 ScreenManager, 底部对齐草地像素上沿
          Layer 2:       草地前景 Image (锯齿边)
          Layer 1 (最顶): 底部导航栏
        """
        self._root.clear_widgets()

        screens = {
            "checkin": CheckinScreen(
                checkin_service=checkin_svc,
                report_service=self._report_svc,
                bet_service=bet_svc,
                motivation_service=self._motivation_svc,
                camera_service=self._camera_svc,
            ),
            "history": HistoryScreen(history_service=history_svc, report_service=self._report_svc),
            "bet": BetScreen(bet_service=bet_svc),
            "settings": SettingsScreen(settings_service=settings_svc, sync_service=SyncService(SyncRepo(self.DB_PATH))),
        }

        sm = AppScreenManager(screens)
        sm.size_hint = (1, None)
        sm.pos_hint = {"x": 0, "y": 0}
        sm.height = Window.height

        # Layer 4: 天空背景 — 与 report_preview 一致的渲染方式
        _sky = _PassthroughImage(
            source=BG_LANDSCAPE,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
            fit_mode="fill",
        )

        # Layer 2: 草地前景锯齿遮罩
        _grass = _PassthroughImage(
            source=get_grass_overlay_path(),
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
            fit_mode="fill",
        )

        # Layer 1: 底部导航
        tab_bar = BottomTabBar(sm, size_hint=(1, None), height=NAV_HEIGHT, pos_hint={"x": 0, "y": 0})

        # z-order 决定渲染顺序: 先添加=底层, 后添加=顶层
        self._root.add_widget(_sky)
        self._root.add_widget(sm)
        self._root.add_widget(_grass)
        self._root.add_widget(tab_bar)

    def on_stop(self) -> None:
        """应用退出时清理资源。"""
        pass


def main() -> None:
    SoloistApp().run()


if __name__ == "__main__":
    main()
