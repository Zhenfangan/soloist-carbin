"""UI 视觉诊断工具 — 启动 App → 自动切换页面 → 截图 → 分析 → 保存。

用法: python -m app.tests.ui.diagnose
输出: doc/ui-design/testreport/screenshots/ 目录下的截图 + analysis.json
"""

from __future__ import annotations

import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from kivy.config import Config

Config.set("graphics", "width", "420")
Config.set("graphics", "height", "750")

from kivy.app import App  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.uix.boxlayout import BoxLayout  # noqa: E402
from kivy.uix.button import Button  # noqa: E402
from kivy.uix.image import Image as KivyImage  # noqa: E402
from kivy.uix.label import Label  # noqa: E402
from kivy.uix.screenmanager import Screen, ScreenManager  # noqa: E402

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
from app.ui.assets.loader import IconLoader, preload_all  # noqa: E402
from app.ui.fonts import apply_global_font  # noqa: E402
from app.ui.screens.bet_screen import BetScreen  # noqa: E402
from app.ui.screens.checkin_screen import CheckinScreen  # noqa: E402
from app.ui.screens.history_screen import HistoryScreen  # noqa: E402
from app.ui.screens.settings_screen import SettingsScreen  # noqa: E402
from app.ui.tokens import (
    BG_CREAM,
    FONT_SIZE_SMALL,
    PRIMARY_YELLOW,
    TEXT_BROWN,
)
from app.utils.clock import SimulatedClock, set_clock  # noqa: E402

OUTPUT_DIR = Path("doc/ui-design/testreport/screenshots")
PAGES = ["checkin", "history", "bet", "settings"]


class DiagnoseApp(App):
    """诊断 App — 加载所有页面，依次截图分析。"""

    DB_PATH = ":memory:"

    def build(self):
        set_clock(SimulatedClock(start_time=datetime(2026, 6, 1, 9, 0, 0)))
        init_db(self.DB_PATH)
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

        # 根布局
        self._root = BoxLayout(orientation="vertical")

        # ScreenManager
        self.sm = ScreenManager()
        screens = {
            "checkin": CheckinScreen(
                checkin_service=checkin_svc,
                promise_service=None,
                motivation_service=None,
            ),
            "history": HistoryScreen(history_service=history_svc),
            "bet": BetScreen(bet_service=bet_svc),
            "settings": SettingsScreen(settings_service=settings_svc, sync_service=None),
        }
        for name, widget in screens.items():
            s = Screen(name=name)
            s.add_widget(widget)
            self.sm.add_widget(s)

        content = BoxLayout()
        content.add_widget(self.sm)
        self._root.add_widget(content)

        # 底部导航（带图标）
        nav = BoxLayout(orientation="horizontal", size_hint=(1, None), height=56)
        tabs = [
            ("打卡", "checkin", "tab_checkin"),
            ("历史", "history", "tab_history"),
            ("对赌", "bet", "tab_bet"),
            ("设置", "settings", "tab_settings"),
        ]
        for text, name, icon_name in tabs:
            btn = Button(
                background_normal="",
                background_color=_rgba(PRIMARY_YELLOW if name == "checkin" else "#E0E0E0"),
                size_hint=(1, 1),
            )
            inner = BoxLayout(orientation="vertical", padding=[0, 4, 0, 2])
            try:
                icon = KivyImage(
                    source=str(IconLoader.get_icon_path(icon_name)),
                    size_hint=(None, None),
                    size=(28, 28),
                    pos_hint={"center_x": 0.5},
                    allow_stretch=True,
                    keep_ratio=True,
                )
                inner.add_widget(icon)
            except Exception:
                pass
            inner.add_widget(Label(
                text=text,
                font_size=FONT_SIZE_SMALL,
                color=_rgba(TEXT_BROWN),
                size_hint=(1, None),
                height=20,
                halign="center",
                valign="middle",
            ))
            btn.add_widget(inner)
            nav.add_widget(btn)

        self._root.add_widget(nav)

        # 启动自动诊断
        self._page_index = 0
        self._results: dict[str, Any] = {}
        Clock.schedule_once(lambda dt: self._diagnose_next(), 1.0)

        return self._root

    def _diagnose_next(self) -> None:
        if self._page_index >= len(PAGES):
            self._finish()
            return

        page = PAGES[self._page_index]
        self.sm.current = page
        # 等待渲染完成
        Clock.schedule_once(lambda dt, p=page: self._capture(p), 0.5)

    def _capture(self, page: str) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / f"{page}.png"
        self._root.export_to_png(str(path))

        # 分析
        from PIL import Image as PILImage

        img = PILImage.open(str(path))
        w, h = img.size
        content_pixels = []
        for y in range(30, h - 60, 3):
            for x in range(0, w, 3):
                content_pixels.append(img.getpixel((x, y)))

        total = len(content_pixels)
        black = sum(1 for p in content_pixels if sum(p) < 25) / total * 100
        white = sum(1 for p in content_pixels if sum(p) > 600) / total * 100
        brown = sum(1 for p in content_pixels
                    if 40 < p[0] < 80 and 30 < p[1] < 60 and 15 < p[2] < 50)
        cream = sum(1 for p in content_pixels
                    if p[0] > 230 and p[1] > 220 and p[2] > 200 and max(p) - min(p) > 10)

        issues = []
        if black > 80:
            issues.append(f"BLACKOUT: {black:.0f}% pure black")
        if white < 5 and brown < 5:
            issues.append(f"NO_CONTENT: white={white:.0f}% brown={brown}")
        if white > 50:
            issues.append("OK: white background visible")
        if brown > 20:
            issues.append("OK: Chinese text rendering")
        if cream > 30:
            issues.append("OK: BG_CREAM background")

        self._results[page] = {
            "path": str(path),
            "black_pct": round(black, 1),
            "white_pct": round(white, 1),
            "brown_pixels": brown,
            "cream_pixels": cream,
            "status": "PASS" if not issues or all(i.startswith("OK") for i in issues) else "FAIL",
            "issues": issues,
        }

        print(f"[{page}] black={black:.0f}% white={white:.0f}% brown={brown} cream={cream} "
              f"→ {' | '.join(issues)}")

        self._page_index += 1
        Clock.schedule_once(lambda dt: self._diagnose_next(), 0.3)

    def _finish(self) -> None:
        # 保存分析结果
        result_path = OUTPUT_DIR / "analysis.json"
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(self._results, f, ensure_ascii=False, indent=2)

        print(f"\n诊断完成。截图: {OUTPUT_DIR}")
        print(f"分析报告: {result_path}")

        failed = [k for k, v in self._results.items() if v["status"] == "FAIL"]
        if failed:
            print(f"\n⚠  {len(failed)} 个页面未通过: {failed}")
        else:
            print("\n✓ 所有页面通过检查")

        # 自动退出
        Clock.schedule_once(lambda dt: self.stop(), 0.5)


def _rgba(hex_color: str, alpha: float = 1.0):
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, alpha)


if __name__ == "__main__":
    DiagnoseApp().run()
