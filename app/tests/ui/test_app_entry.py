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

    def test_on_resume_refreshes_current_screen_via_clock(self) -> None:
        """从后台恢复(相机 Intent 返回 / 切回前台)时刷新当前页, 但必须经
        Clock.schedule_once 切回 Kivy 主线程。

        根因(2026-07-08 真机坐实): Android 的生命周期回调(onActivityResult/
        onResume)运行在 Android UI 线程, 与 Kivy 渲染线程不是同一个; 在该线程
        里直接 refresh()(含创建/移除 widget 等 graphics 操作)会抛
        'Cannot change graphics instruction outside the main Kivy thread'。
        故 on_resume 里绝不能同步直接调 refresh, 而要交给 Clock 在主线程下一帧跑。
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

            result = app.on_resume()
            assert result is True
            assert mock_widget.refresh.call_count == 0  # 未同步(否则真机非主线程炸)
            Clock.tick()
            assert mock_widget.refresh.call_count == 1  # 主线程下一帧执行

    def test_on_resume_before_build_does_not_crash(self) -> None:
        """App 尚未 build()(_sm 不存在, 如启动极早期恢复)时 on_resume 不应崩溃。"""
        with patch.dict(os.environ, {"KIVY_NO_ARGS": "1"}), \
             patch("kivy.app.App.run", return_value=None):
            from app.main import SoloistApp
            app = SoloistApp()
            assert app.on_resume() is True

    def test_required_permissions_include_read_media_images(self) -> None:
        """Android 13+ (targetSdk 34) 读取系统相机写入公共相册的打卡照片, 必须
        持有 READ_MEDIA_IMAGES; 仅 READ_EXTERNAL_STORAGE 在 API33+ 被系统忽略
        (granted=false 且不弹框), 导致战报照片读不出、显示白色 —— 2026-07-08
        OPPO 真机 dumpsys 坐实。故运行时申请清单必须含 READ_MEDIA_IMAGES, 同时
        保留 READ_EXTERNAL_STORAGE 兼容 Android 12-。"""
        from app.main import _required_android_permissions
        perms = _required_android_permissions()
        assert "android.permission.READ_MEDIA_IMAGES" in perms
        assert "android.permission.CAMERA" in perms
        assert "android.permission.READ_EXTERNAL_STORAGE" in perms

    def test_main_guides_manage_all_files_access(self) -> None:
        """照片抢救要按路径直接读系统相机写的公共文件, scoped storage 下
        READ_MEDIA_IMAGES 只对 MediaStore API 生效, shutil/File 直接读会 PermissionError
        (2026-07-08 OPPO 真机坐实)。故 app 需引导用户开启'所有文件访问'
        (MANAGE_EXTERNAL_STORAGE + isExternalStorageManager 检查 + 跳设置页)。"""
        import inspect
        from app.main import SoloistApp
        src = inspect.getsource(SoloistApp)
        assert "_request_manage_storage" in src
        assert "isExternalStorageManager" in src
        assert "ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION" in src

    def test_first_launch_detection(self) -> None:
        """验证首次启动检测逻辑。"""
        # 使用内存数据库模拟
        from app.db import init_db
        from app.repositories.settings_repo import SettingsRepo

        init_db(":memory:")
        repo = SettingsRepo(":memory:")
        assert repo.get("app_version") is None  # 从未设置过
