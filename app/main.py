"""Soloist Cabin Pro — Kivy APP 入口。

集成: 像素主题 + 字体加载 + 资源预加载 + 引导流程 + 导航 + 4 个页面。
"""

from __future__ import annotations

import os

from kivy.config import Config

# 桌面窗口尺寸; 真机全屏会忽略此设置。开发时可用环境变量
# SOLOIST_WIN_W / SOLOIST_WIN_H 模拟真机分辨率, 在本地验证等比缩放布局。
Config.set("graphics", "width", os.environ.get("SOLOIST_WIN_W", "420"))
Config.set("graphics", "height", os.environ.get("SOLOIST_WIN_H", "750"))

from kivy.app import App  # noqa: E402
from kivy.graphics import Color, Rectangle  # noqa: E402
from kivy.uix.boxlayout import BoxLayout  # noqa: E402
from kivy.uix.floatlayout import FloatLayout  # noqa: E402
from kivy.uix.image import Image as KivyImage  # noqa: E402
from kivy.uix.scatterlayout import ScatterLayout  # noqa: E402
from kivy.core.window import Window  # noqa: E402

from app.db import init_db  # noqa: E402
from app.repositories.bet_repo import BetRepo  # noqa: E402
from app.repositories.checkin_repo import CheckinRepo  # noqa: E402
from app.repositories.ledger_repo import LedgerRepo  # noqa: E402
from app.repositories.settings_repo import SettingsRepo  # noqa: E402
from app.interfaces.notifier import NoOpNotifier  # noqa: E402
from app.repositories.shooting_repo import ShootingRepo  # noqa: E402
from app.repositories.streak_repo import StreakRepo  # noqa: E402
from app.services.shooting_service import ShootingService  # noqa: E402
from app.repositories.sync_repo import SyncRepo  # noqa: E402
from app.services.bet_service import BetService  # noqa: E402
from app.services.camera_desktop_mock import DesktopCameraMock  # noqa: E402
from app.services.checkin_service import CheckinService  # noqa: E402
from app.services.boyfriend_promise_service import BoyfriendPromiseService  # noqa: E402
from app.services.history_service import HistoryService  # noqa: E402
from app.services.motivation_service import MotivationService  # noqa: E402
from app.services.penalty_service import PenaltyService  # noqa: E402
from app.services.report_service import ReportService  # noqa: E402
from app.services.settings_service import SettingsService  # noqa: E402
from app.services.ntfy_service import NtfyPushService  # noqa: E402
from app.services.sync_service import SyncService  # noqa: E402
from app.ui.assets.landscape import BG_LANDSCAPE, get_grass_overlay_path  # noqa: E402
from app.ui.assets.loader import preload_all  # noqa: E402
from app.ui.fonts import apply_global_font  # noqa: E402
from app.ui.navigation import AppScreenManager, BottomTabBar  # noqa: E402
from app.ui.components.time_control_panel import TimeControlPanel  # noqa: E402
from app.ui.screens.bet_screen import BetScreen  # noqa: E402
from app.ui.screens.checkin_screen import CheckinScreen  # noqa: E402
from app.ui.screens.history_screen import HistoryScreen  # noqa: E402
from app.ui.screens.onboarding_screen import OnboardingScreen  # noqa: E402
from app.ui.screens.settings_screen import SettingsScreen  # noqa: E402
from app.ui.tokens import (  # noqa: E402
    BG_CREAM,
    GRASS_INSET,
    LOGICAL_HEIGHT,
    LOGICAL_WIDTH,
    NAV_HEIGHT,
)
from app.utils.clock import SimulatedClock, SystemClock, set_clock  # noqa: E402


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

        # 安卓: 启动即请求相机/存储运行时权限
        self._request_android_permissions()

        # 默认使用系统真实时钟（虚拟时钟在开发面板中手动开启）
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
        self._camera_svc = self._make_camera_service()
        ledger_repo = LedgerRepo(self.DB_PATH)
        bet_svc = BetService(BetRepo(self.DB_PATH), ledger_repo, settings_repo)
        # 启动时自动补扣滞纳金
        bet_svc.run_auto_checks()
        shooting_repo = ShootingRepo(self.DB_PATH)
        self._shooting_svc = ShootingService(shooting_repo)
        checkin_svc = CheckinService(checkin_repo, settings_repo, shooting_service=self._shooting_svc)
        history_svc = HistoryService(checkin_repo, ledger_repo, shooting_repo, BetRepo(self.DB_PATH))
        self._report_svc = ReportService(checkin_repo, ledger_repo, shooting_repo, settings_repo)
        # 实例化以触发 ATTENDANCE_JUDGED / DAY_FINISHED 事件订阅 (生成罚款/奖励流水)
        self._penalty_svc = PenaltyService(checkin_repo, ledger_repo, settings_repo)
        # 实例化以触发 DAY_FINISHED 事件订阅 (更新 streak) + CheckinScreen 显示连续天数
        self._motivation_svc = MotivationService(
            checkin_repo, StreakRepo(self.DB_PATH), settings_repo, NoOpNotifier()
        )
        self._promise_svc = BoyfriendPromiseService(ledger_repo, settings_repo, checkin_repo)
        self._ntfy_svc = NtfyPushService(settings_svc)
        self._ntfy_svc.start()

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
                promise_service=self._promise_svc,
                report_service=self._report_svc,
                bet_service=bet_svc,
                motivation_service=self._motivation_svc,
                camera_service=self._camera_svc,
                settings_service=settings_svc,
                shooting_service=self._shooting_svc,
            ),
            "history": HistoryScreen(history_service=history_svc, report_service=self._report_svc),
            "bet": BetScreen(bet_service=bet_svc),
            "settings": SettingsScreen(settings_service=settings_svc, sync_service=SyncService(SyncRepo(self.DB_PATH))),
        }

        sm = AppScreenManager(screens)
        self._sm = sm
        # design_canvas 是 FloatLayout(会处理 size_hint/pos_hint), 故这里用回
        # 相对布局: 宽度撑满画布, 高度=逻辑画布高, 底部对齐。
        sm.size_hint = (1, None)
        sm.height = LOGICAL_HEIGHT
        sm.pos_hint = {"x": 0, "y": 0}

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

        # 虚拟时钟浮动条（默认隐藏，开发面板中开启）
        self._time_panel = TimeControlPanel(
            size_hint=(1, None),
            height=0,
            opacity=0,
            pos_hint={"x": 0, "top": 1.0},
            on_time_changed=lambda: screens["checkin"].refresh() if "checkin" in screens else None,
        )
        self._time_panel_visible = False

        # ── 单根 ScatterLayout 整体等比缩放 ─────────────────────────────
        # ScatterLayout = Scatter + 内置 FloatLayout: 既能整体等比缩放, 又用
        # RelativeLayout 式坐标正确变换触摸。纯 Scatter 对深层 ScrollView
        # (CheckinScreen 即 ScrollView) 的触摸命中会错位 → 必须用 ScatterLayout。
        # 所有 UI 层直接加入, 内部 FloatLayout 按 size_hint/pos_hint 布局(与桌面一致)。
        scale = min(Window.width / LOGICAL_WIDTH, Window.height / LOGICAL_HEIGHT)
        self._content_scale = scale

        root_scatter = ScatterLayout(
            size=(LOGICAL_WIDTH, LOGICAL_HEIGHT),
            size_hint=(None, None),
            do_rotation=False,
            do_translation=False,
            do_scale=False,
        )
        root_scatter.scale = scale
        # 水平居中, 垂直底部对齐(草地/导航栏贴屏幕底, 拇指够得到)。
        root_scatter.pos = ((Window.width - LOGICAL_WIDTH * scale) / 2.0, 0)
        # 暴露给需要挂到"缩放后的设计画布"而非裸 Window 的组件
        # (如 CheckinSuccessPanel), 否则组件会以未缩放的逻辑尺寸画在真机原生
        # 分辨率的 Window 上, 显得极小甚至看不见。
        self._root_scatter = root_scatter
        # z-order: 先加=底层
        root_scatter.add_widget(_sky)
        root_scatter.add_widget(sm)
        root_scatter.add_widget(_grass)
        root_scatter.add_widget(tab_bar)
        root_scatter.add_widget(self._time_panel)

        # 全屏天空垫底: 填充画布等比缩放后顶部露出的空白, 视觉上仍是天空。
        _sky_full = _PassthroughImage(
            source=BG_LANDSCAPE,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
            fit_mode="fill",
        )

        self._root.add_widget(_sky_full)
        self._root.add_widget(root_scatter)

    def _make_camera_service(self) -> object:
        """按平台选相机实现: 安卓→真相机(plyer), 桌面→mock。"""
        try:
            from kivy.utils import platform  # type: ignore[import]
            if str(platform) == "android":
                from app.services.camera_android import AndroidCameraService
                return AndroidCameraService()
        except Exception:
            pass
        return DesktopCameraMock()

    def _request_android_permissions(self) -> None:
        """安卓运行时权限请求(相机/存储); 非安卓或失败均静默跳过。"""
        try:
            from kivy.utils import platform  # type: ignore[import]
            if str(platform) != "android":
                return
            from android.permissions import Permission, request_permissions  # type: ignore[import]
            request_permissions([
                Permission.CAMERA,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
            ])
        except Exception:
            pass

    def on_stop(self) -> None:
        """应用退出时清理资源。"""
        if hasattr(self, "_ntfy_svc"):
            self._ntfy_svc.stop()


def main() -> None:
    SoloistApp().run()


if __name__ == "__main__":
    main()
