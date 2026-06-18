"""测试 App 入口 — main.py 集成测试。"""

from __future__ import annotations

import os
from unittest.mock import patch


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
        """验证 apply_global_font 可调用 + 把 SmileySans 注册成 Roboto。"""
        from kivy.core.text import LabelBase

        from app.ui.fonts import apply_global_font

        apply_global_font()
        # 字体文件存在时, Roboto 应该被覆盖为 SmileySans
        assert "Roboto" in LabelBase._fonts

    def test_resource_preload(self) -> None:
        """验证资源预加载返回正确计数。"""
        from app.ui.assets.loader import preload_all

        result = preload_all()
        assert result["sprites"] == 5
        assert result["icons"] == 24  # 16 原有 + 8 active/inactive tab icons
        assert result["sequences"] == 5  # rabbit / bear / dog / pig / cat

    def test_clock_integration(self) -> None:
        """验证 SystemClock 可以正常使用。"""
        from app.utils.clock import SystemClock, get_clock, set_clock

        clock = SystemClock()
        set_clock(clock)
        retrieved = get_clock()
        assert isinstance(retrieved, SystemClock)

    def test_first_launch_detection(self) -> None:
        """验证首次启动检测逻辑。"""
        # 使用内存数据库模拟
        from app.db import init_db
        from app.repositories.settings_repo import SettingsRepo

        init_db(":memory:")
        repo = SettingsRepo(":memory:")
        assert repo.get("app_version") is None  # 从未设置过
