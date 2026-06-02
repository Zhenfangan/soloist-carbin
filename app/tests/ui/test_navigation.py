"""测试全局导航 — BottomTabBar / AppScreenManager。"""

from __future__ import annotations

from kivy.uix.screenmanager import ScreenManager
from kivy.uix.widget import Widget

from app.ui.navigation import TAB_CONFIG, AppScreenManager, BottomTabBar, TabButton


class TestTabButton:
    """7.7 Tab 按钮测试"""

    def test_create_tab_button(self) -> None:
        btn = TabButton(icon_name="tab_checkin", text="打卡")
        assert btn is not None
        assert btn._label.text == "打卡"

    def test_tab_active_state(self) -> None:
        from app.ui.navigation import _to_rgba
        from app.ui.tokens import PRIMARY_YELLOW, TEXT_GRAY

        btn = TabButton(icon_name="tab_checkin", text="打卡")
        btn.set_active(True)
        # active = 明黄色
        expected_yellow = _to_rgba(PRIMARY_YELLOW)
        assert list(btn._label.color) == list(expected_yellow)

        btn.set_active(False)
        # inactive = 灰色
        expected_gray = _to_rgba(TEXT_GRAY)
        assert list(btn._label.color) == list(expected_gray)


class TestBottomTabBar:
    """7.6/7.8 BottomTabBar 测试"""

    def test_create_tab_bar(self) -> None:
        sm = ScreenManager()
        bar = BottomTabBar(sm)
        assert len(bar._tabs) == 4
        assert bar._active_index == 0

    def test_switch_tab(self) -> None:
        sm = ScreenManager()
        # 需要将 screens 加入 sm
        for cfg in TAB_CONFIG:
            from kivy.uix.screenmanager import Screen
            screen = Screen(name=cfg["name"])
            screen.add_widget(Widget())
            sm.add_widget(screen)

        bar = BottomTabBar(sm)
        bar.switch_tab(1)
        assert bar._active_index == 1
        assert sm.current == "history"
        bar.switch_tab(3)
        assert bar._active_index == 3
        assert sm.current == "settings"


class TestAppScreenManager:
    """7.9 AppScreenManager 测试"""

    def test_create_manager(self) -> None:
        screens = {
            "test1": Widget(),
            "test2": Widget(),
        }
        sm = AppScreenManager(screens)
        assert sm.has_screen("test1")
        assert sm.has_screen("test2")

    def test_switch_screen(self) -> None:
        screens = {"a": Widget(), "b": Widget()}
        sm = AppScreenManager(screens)
        sm.current = "b"
        assert sm.current == "b"
