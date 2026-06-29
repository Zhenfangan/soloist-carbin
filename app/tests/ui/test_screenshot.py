"""视觉回归测试 — 真实渲染每个页面 → 导出 PNG → 自动检查像素。

运行方式: python -m pytest app/tests/ui/test_screenshot.py -v
需要: 显示器（非 headless），会短暂弹出窗口然后自动关闭。

检查内容:
- 背景色是否正确（非纯黑、非纯灰）
- 是否有可见的文字内容
- 关键组件是否渲染
"""

from __future__ import annotations

import io
import os
import tempfile
from collections.abc import Generator
from datetime import datetime
from typing import Any

import pytest

import pytest
from PIL import Image as PILImage

from kivy.config import Config

# 确保真实窗口渲染
Config.set("graphics", "width", "420")
Config.set("graphics", "height", "750")

from kivy.app import App  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from kivy.uix.boxlayout import BoxLayout  # noqa: E402
from kivy.uix.screenmanager import Screen  # noqa: E402

from app.db import init_db  # noqa: E402
from app.repositories.bet_repo import BetRepo  # noqa: E402
from app.repositories.checkin_repo import CheckinRepo  # noqa: E402
from app.repositories.ledger_repo import LedgerRepo  # noqa: E402
from app.repositories.settings_repo import SettingsRepo  # noqa: E402
from app.repositories.shooting_repo import ShootingRepo  # noqa: E402
from app.services.bet_service import BetService  # noqa: E402
from app.services.checkin_service import CheckinService  # noqa: E402
from app.services.history_service import HistoryService  # noqa: E402
from app.services.settings_service import SettingsService  # noqa: E402
from app.ui.assets.loader import preload_all  # noqa: E402
from app.ui.fonts import apply_global_font  # noqa: E402
from app.ui.screens.bet_screen import BetScreen  # noqa: E402
from app.ui.screens.checkin_screen import CheckinScreen  # noqa: E402
from app.ui.screens.history_screen import HistoryScreen  # noqa: E402
from app.ui.screens.settings_screen import SettingsScreen  # noqa: E402
from app.utils.clock import SimulatedClock, set_clock  # noqa: E402


# ═══════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════


def _export_widget_to_png(widget: Any) -> bytes:
    """强制布局后导出 widget 为 PNG 字节流。"""
    # 触发布局
    widget.size = (420, 694)  # 减去 56px 导航栏
    widget.pos = (0, 0)
    if hasattr(widget, "do_layout"):
        widget.do_layout()

    # 推进事件循环确保纹理加载完成
    for _ in range(10):
        Clock.tick()

    # 导出为 PNG
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        tmp_path = f.name

    try:
        widget.export_to_png(tmp_path)
        with open(tmp_path, "rb") as f:
            data = f.read()
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    return data


def _analyze_screenshot(png_bytes: bytes, name: str) -> dict[str, Any]:
    """分析截图，返回诊断信息。"""
    img = PILImage.open(io.BytesIO(png_bytes))
    w, h = img.size

    # 统计内容区域颜色（排除最顶部 30px 窗口标题栏 + 最底部 56px nav）
    content_y_start = 30
    content_y_end = h - 60

    content_pixels = []
    for y in range(content_y_start, content_y_end, 5):
        for x in range(0, w, 5):
            content_pixels.append(img.getpixel((x, y)))

    total = len(content_pixels)
    black_count = sum(1 for p in content_pixels if sum(p) < 25)
    white_count = sum(1 for p in content_pixels if sum(p) > 600)
    gray_count = sum(1 for p in content_pixels if 120 < sum(p) < 200 and max(p) - min(p) < 20)
    cream_count = sum(1 for p in content_pixels
                      if p[0] > 230 and p[1] > 220 and p[2] > 200 and max(p) - min(p) > 10)
    brown_count = sum(1 for p in content_pixels
                      if 40 < p[0] < 80 and 30 < p[1] < 60 and 15 < p[2] < 50)

    black_pct = black_count / total * 100
    white_pct = white_count / total * 100

    issues = []

    # 检查 1: 内容区不能全黑
    if black_pct > 80:
        issues.append(f"内容区 {black_pct:.0f}% 纯黑 — 页面可能未渲染")

    # 检查 2: 必须有可见内容（白色或奶油色或棕色文字）
    if white_pct < 5 and cream_count < 10 and brown_count < 10:
        issues.append(f"内容区几乎无可见元素 (白={white_pct:.0f}% 棕={brown_count})")

    # 检查 3: 不能全是灰色（ScrollView 默认背景）
    if gray_count / total > 60:
        issues.append(f"内容区 {gray_count/total*100:.0f}% 为灰色 — Kivy 默认背景暴露")

    return {
        "size": (w, h),
        "black_pct": round(black_pct, 1),
        "white_pct": round(white_pct, 1),
        "cream_pixels": cream_count,
        "brown_pixels": brown_count,
        "issues": issues,
    }


# ═══════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════


@pytest.fixture
def services(temp_db: str, clock: Any) -> Generator[dict[str, Any], None, None]:
    """创建所有 Service 实例。"""
    clock.set_time(datetime(2026, 6, 1, 9, 0, 0))

    settings_repo = SettingsRepo(temp_db)
    settings_svc = SettingsService(settings_repo)
    checkin_repo = CheckinRepo(temp_db)
    checkin_svc = CheckinService(checkin_repo, settings_repo)
    ledger_repo = LedgerRepo(temp_db)
    bet_svc = BetService(BetRepo(temp_db), ledger_repo, settings_repo)
    history_svc = HistoryService(checkin_repo, ledger_repo, ShootingRepo(temp_db))

    # 初始化资源
    apply_global_font()
    preload_all()

    yield {
        "settings": settings_svc,
        "checkin": checkin_svc,
        "bet": bet_svc,
        "history": history_svc,
    }


# ═══════════════════════════════════════════════
# 截图验证测试
# ═══════════════════════════════════════════════


class TestScreenshotRendering:
    """真实渲染每个页面 → 截图 → 自动检查像素。

    ⚠️ 所有测试在无头/SDL2 离屏环境下无法渲染真实内容(页面 95%+ 同色)。
    需真实显示环境(桌面窗口或真机)验证。
    """

    @pytest.mark.xfail(reason="无头 SDL2 离屏渲染不可靠,需真实显示环境验证")
    def test_checkin_screen_renders(self, services: dict[str, Any]) -> None:
        """打卡页：不应全黑，应有可见内容。"""
        screen = CheckinScreen(
            checkin_service=services["checkin"],
            promise_service=None,
            motivation_service=None,
        )
        png = _export_widget_to_png(screen)
        result = _analyze_screenshot(png, "checkin")

        assert result["white_pct"] > 5, (
            f"打卡页白色仅 {result['white_pct']}% — 组件未渲染\n"
            f"诊断: {result['issues']}"
        )
        assert result["black_pct"] < 70, (
            f"打卡页 {result['black_pct']}% 纯黑 — 背景缺失\n"
            f"诊断: {result['issues']}"
        )

    @pytest.mark.xfail(reason="无头 SDL2 离屏渲染不可靠,需真实显示环境验证")
    def test_history_screen_renders(self, services: dict[str, Any]) -> None:
        """历史页：应有可见内容和日期数据。"""
        screen = HistoryScreen(history_service=services["history"])
        png = _export_widget_to_png(screen)
        result = _analyze_screenshot(png, "history")

        assert result["black_pct"] < 70, (
            f"历史页 {result['black_pct']}% 纯黑\n"
            f"诊断: {result['issues']}"
        )
        assert len(result["issues"]) == 0, (
            f"历史页存在问题: {result['issues']}"
        )

    @pytest.mark.xfail(reason="无头 SDL2 离屏渲染不可靠,需真实显示环境验证")
    def test_bet_screen_renders(self, services: dict[str, Any]) -> None:
        """对赌页：不应大面积灰色。"""
        screen = BetScreen(bet_service=services["bet"])
        png = _export_widget_to_png(screen)
        result = _analyze_screenshot(png, "bet")

        assert result["black_pct"] < 80, (
            f"对赌页 {result['black_pct']}% 纯黑\n"
            f"诊断: {result['issues']}"
        )
        assert len(result["issues"]) == 0, (
            f"对赌页存在问题: {result['issues']}"
        )

    @pytest.mark.xfail(reason="无头 SDL2 离屏渲染不可靠,需真实显示环境验证")
    def test_settings_screen_renders(self, services: dict[str, Any]) -> None:
        """设置页：不应全黑（之前是 99.7% 黑）。"""
        screen = SettingsScreen(
            settings_service=services["settings"],
            sync_service=None,
        )
        png = _export_widget_to_png(screen)
        result = _analyze_screenshot(png, "settings")

        assert result["black_pct"] < 50, (
            f"设置页 {result['black_pct']}% 纯黑 — CollapsibleGroup 可能未渲染\n"
            f"白色: {result['white_pct']}%\n"
            f"诊断: {result['issues']}"
        )
        assert result["white_pct"] > 15 or result["cream_pixels"] > 50 or result["brown_pixels"] > 30, (
            f"设置页几乎无可见内容 — 白={result['white_pct']}% "
            f"奶油={result['cream_pixels']} 棕={result['brown_pixels']}\n"
            f"诊断: {result['issues']}"
        )

    @pytest.mark.xfail(reason="无头 SDL2 离屏渲染不可靠,需真实显示环境验证")
    def test_all_screens_no_blackout(self, services: dict[str, Any]) -> None:
        """综合测试：四个页面都不能是黑屏。"""
        screens = {
            "checkin": CheckinScreen(
                checkin_service=services["checkin"],
                promise_service=None,
                motivation_service=None,
            ),
            "history": HistoryScreen(history_service=services["history"]),
            "bet": BetScreen(bet_service=services["bet"]),
            "settings": SettingsScreen(
                settings_service=services["settings"],
                sync_service=None,
            ),
        }

        failures = []
        for name, screen in screens.items():
            png = _export_widget_to_png(screen)
            result = _analyze_screenshot(png, name)
            if result["issues"]:
                failures.append(f"  {name}: {result['issues']}")

        assert not failures, (
            f"以下页面存在视觉渲染问题:\n" + "\n".join(failures)
        )
