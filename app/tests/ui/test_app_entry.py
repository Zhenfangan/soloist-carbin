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

    def test_font_loading(self) -> None:
        """验证字体加载函数可调用。"""
        from app.ui.fonts import get_available_font_name, load_pixel_fonts

        loaded = load_pixel_fonts()
        assert isinstance(loaded, dict)
        name = get_available_font_name()
        assert isinstance(name, str)

    def test_resource_preload(self) -> None:
        """验证资源预加载返回正确计数。"""
        from app.ui.assets.loader import preload_all

        result = preload_all()
        assert result["sprites"] == 5
        assert result["icons"] == 16

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
