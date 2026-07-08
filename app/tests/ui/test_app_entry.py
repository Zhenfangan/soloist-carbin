"""测试 App 入口 — main.py 集成测试。"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch


class TestAppEntry:
    """7.17~7.20 应用入口测试"""

    def test_main_module_imports(self) -> None:
        """验证 main.py 可以成功导入。"""
        # patching to avoid actual window creation
        with patch.dict(os.environ, {"KIVY_NO_ARGS": "1"}), \
             patch("kivy.app.App.run", return_value=None):
            from app.main import SoloistApp
            app = SoloistApp()
            assert app.DB_PATH == "soloist.db"

    def test_main_module_references_penalty_service(self) -> None:
        """回归: main.py 必须实例化 PenaltyService — 否则 ATTENDANCE_JUDGED
        事件无订阅者, 旷工/迟到不写 ledger → 战报罚款一直显示 0
        (bug 报告: 2026-06-11)。
        """
        import inspect
        from app.main import SoloistApp

        source = inspect.getsource(SoloistApp)
        assert "PenaltyService(" in source, (
            "main.py 中 SoloistApp 必须实例化 PenaltyService, "
            "否则旷工不会写罚款 ledger 条目"
        )
        # 实例必须挂在 self 上, 否则 __init__ 结束后被 GC, 订阅丢失
        assert "self._penalty_svc" in source or "self.penalty_svc" in source, (
            "PenaltyService 实例必须保存为 SoloistApp 属性 (避免 GC 清理订阅者)"
        )

    def test_main_module_references_motivation_service(self) -> None:
        """回归: main.py 必须实例化 MotivationService 并传给 CheckinScreen —
        否则连续出勤天数 streak 永不更新 + CheckinScreen 的 "已连续正常出勤 N 天"
        标签永远是空 (bug 报告: 2026-06-12)。
        """
        import inspect
        from app.main import SoloistApp

        source = inspect.getsource(SoloistApp)
        assert "MotivationService(" in source, (
            "main.py 中 SoloistApp 必须实例化 MotivationService"
        )
        # 实例必须挂在 self 上, 否则 __init__ 结束后被 GC, DAY_FINISHED 订阅丢失
        assert "self._motivation_svc" in source or "self.motivation_svc" in source, (
            "MotivationService 实例必须保存为 SoloistApp 属性 (避免 GC 清理订阅者)"
        )
        # 必须实际传给 CheckinScreen, 否则 streak 显示永远是空
        assert "motivation_service=" in source, (
            "MotivationService 必须以 motivation_service= 关键字传给 CheckinScreen"
        )

    def test_font_loading(self) -> None:
        """验证 apply_global_font 可调用 + 把长坂点宋16 注册成 Roboto。"""
        from kivy.core.text import LabelBase

        from app.ui.fonts import apply_global_font

        apply_global_font()
        assert "Roboto" in LabelBase._fonts

    def test_resource_preload(self) -> None:
        """验证资源预加载返回正确计数。"""
        from app.ui.assets.loader import preload_all

        result = preload_all()
        assert result["sprites"] == 5
        assert result["icons"] == 36  # 24 原有 + 12 emoji 替代像素图标
        assert result["sequences"] == 5  # rabbit / bear / dog / pig / cat

    def test_clock_integration(self) -> None:
        """验证 SystemClock 可以正常使用。"""
        from app.utils.clock import SystemClock, get_clock, set_clock

        clock = SystemClock()
        set_clock(clock)
        retrieved = get_clock()
        assert isinstance(retrieved, SystemClock)

    def test_on_resume_refreshes_current_screen(self) -> None:
        """回归(真机): 相机 Intent 返回前台后, Kivy 的 Clock/渲染有时不会
        立即恢复正常, CheckinSuccessPanel 的 4.5s 自动关闭定时器卡死, 面板
        永久盖住按钮 —— 用户唯一能恢复的办法是切到其他 Tab 再切回来, 因为
        切 Tab 触发的 on_enter→refresh() 里有强制解挂面板的兜底逻辑。

        Android 恢复前台会可靠触发 App.on_resume()(与本 App 已验证生效的
        on_pause 备份钩子同一套生命周期机制), 这里复用同一个 refresh(),
        让"切 Tab 才能恢复"的效果自动发生, 不需要用户手动操作。
        """
        with patch.dict(os.environ, {"KIVY_NO_ARGS": "1"}), \
             patch("kivy.app.App.run", return_value=None):
            from app.main import SoloistApp
            app = SoloistApp()

            mock_widget = MagicMock()
            stub_sm = MagicMock()
            stub_sm.current = "checkin"
            stub_sm._screen_widgets = {"checkin": mock_widget}
            app._sm = stub_sm

            result = app.on_resume()

            mock_widget.refresh.assert_called_once()
            assert result is True

    def test_on_resume_schedules_delayed_second_refresh(self) -> None:
        """真机复现: 相机 Intent 返回瞬间, IconLabel 的像素图标纹理偶发渲染成
        黑块(GL 上下文刚恢复的时机不稳定); 已知能自愈的办法是再触发一次
        refresh()(如手动切 Tab)。on_resume 应自动补一次延迟 refresh, 不必
        等用户手动切 Tab 才能修复黑块图标。
        """
        with patch.dict(os.environ, {"KIVY_NO_ARGS": "1"}), \
             patch("kivy.app.App.run", return_value=None):
            from kivy.clock import Clock

            from app.main import SoloistApp
            app = SoloistApp()

            mock_widget = MagicMock()
            stub_sm = MagicMock()
            stub_sm.current = "checkin"
            stub_sm._screen_widgets = {"checkin": mock_widget}
            app._sm = stub_sm

            app.on_resume()
            assert mock_widget.refresh.call_count == 1  # 立即那次

            for _ in range(60):
                Clock.tick()
            assert mock_widget.refresh.call_count == 2  # 延迟兜底那次

    def test_on_resume_before_build_does_not_crash(self) -> None:
        """App 尚未 build()(_sm 不存在, 如启动极早期恢复)时 on_resume 不应崩溃。"""
        with patch.dict(os.environ, {"KIVY_NO_ARGS": "1"}), \
             patch("kivy.app.App.run", return_value=None):
            from app.main import SoloistApp
            app = SoloistApp()
            assert app.on_resume() is True

    def test_first_launch_detection(self) -> None:
        """验证首次启动检测逻辑。"""
        # 使用内存数据库模拟
        from app.db import init_db
        from app.repositories.settings_repo import SettingsRepo

        init_db(":memory:")
        repo = SettingsRepo(":memory:")
        assert repo.get("app_version") is None  # 从未设置过
