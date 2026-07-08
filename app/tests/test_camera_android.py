"""AndroidCameraService 回调线程修复。

真机根因(2026-07-08 logcat 坐实): 系统相机经 plyer 的 onActivityResult 在
【非 Kivy 主线程】回调, 若在该线程里直接跑 on_done(它会刷新卡片/弹庆祝动画/
弹男友承诺框, 全是 graphics 操作)会抛:

    TypeError: Cannot change graphics instruction outside the main Kivy thread

异常打断整条签到收尾 → 动画不弹、承诺框不弹、卡片图标纹理传不上 GL 显示黑块、
必须切 Tab 才恢复(切 Tab 的 on_enter 由主循环在主线程触发)。

修复: 在 Android/Kivy 边界用 Clock.schedule_once 把结果回调切回主线程。
本测试验证该调度机制, 桌面 mock 因回调本就在主线程(Button on_press)从不复现。
"""

from __future__ import annotations

from pathlib import Path

from kivy.clock import Clock

from app.services.camera_android import _dispatch_to_main_thread, _make_result_handler


class TestDispatchToMainThread:
    def test_does_not_run_callback_synchronously(self) -> None:
        """非主线程直接跑会炸 graphics, 故绝不能同步立即执行。"""
        called: list[int] = []
        _dispatch_to_main_thread(lambda: called.append(1))
        assert called == []

    def test_runs_callback_after_clock_tick(self) -> None:
        """Clock 在主线程 tick, 回调应在其下一帧执行。"""
        called: list[int] = []
        _dispatch_to_main_thread(lambda: called.append(1))
        Clock.tick()
        assert called == [1]


class TestResultHandler:
    def test_existing_file_rescued_into_private_dir(self, tmp_path: Path) -> None:
        """系统相机写入公共相册的照片, 回调这一刻立即抢救复制到 app 私有目录;
        on_done 收到的是【私有目录】里的路径(而非易失的公共路径), 且内容一致。"""
        public = tmp_path / "public"
        public.mkdir()
        photo = public / "morning_in.jpg"
        photo.write_bytes(b"\x89PNG\r\nDATA")
        private_root = tmp_path / "private"
        got: list[Path | None] = []
        handler = _make_result_handler(
            lambda p: got.append(p), private_dir_provider=lambda: private_root
        )

        handler(str(photo))
        assert got == []            # 未同步执行(否则真机在非主线程炸)
        Clock.tick()
        assert len(got) == 1
        result = got[0]
        assert result is not None
        assert private_root in result.parents      # 落在私有目录下
        assert result.exists()
        assert result.read_bytes() == b"\x89PNG\r\nDATA"
        assert result.name == "morning_in.jpg"

    def test_rescue_failure_falls_back_to_original_path(self, tmp_path: Path) -> None:
        """复制到私有目录失败时, 退回原始路径(至少当次战报能显示), 不丢回调。"""
        photo = tmp_path / "evening_in.jpg"
        photo.write_bytes(b"x")
        got: list[Path | None] = []

        def _boom() -> Path:
            raise OSError("private dir unavailable")

        handler = _make_result_handler(lambda p: got.append(p), private_dir_provider=_boom)
        handler(str(photo))
        Clock.tick()
        assert got == [photo]       # 退回原路径

    def test_missing_file_dispatches_none(self, tmp_path: Path) -> None:
        got: list[Path | None] = []
        handler = _make_result_handler(lambda p: got.append(p))

        handler(str(tmp_path / "nope.jpg"))
        Clock.tick()
        assert got == [None]

    def test_none_filename_dispatches_none(self) -> None:
        got: list[Path | None] = []
        handler = _make_result_handler(lambda p: got.append(p))

        handler(None)
        Clock.tick()
        assert got == [None]
