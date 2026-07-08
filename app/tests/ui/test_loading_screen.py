"""LoadingScreen — 冷启动加载页, 真 Clock 驱动跑马灯读条(非静态)。

回归背景: 原生 presplash.png 是 Android 系统在 Python 启动前展示的静态图,
物理上无法做成动态读条; 需求是"读条要动"。方案: Python/Kivy 启动后立刻
展示这个组件, 读条用 Clock.schedule_interval 循环推进跑马灯, 不依赖具体
初始化进度百分比(冷启动耗时不定, 循环动画保证观感"一直在动"而非卡死)。
"""

from __future__ import annotations

from kivy.clock import Clock

from app.ui.components.loading_screen import LoadingScreen, _SegmentBar


class TestSegmentBar:
    """跑马灯读条 —— Clock 驱动, 点亮区间随时间推进, 循环不停。"""

    def test_lit_start_advances_over_time(self) -> None:
        bar = _SegmentBar(size_hint=(None, None), size=(180, 14))
        first = bar._lit_start
        for _ in range(5):
            Clock.tick()
        bar.stop()
        assert bar._lit_start != first, "跑马灯读条推进多个 Clock tick 后, 点亮位置应变化(证明是动画而非静态)"

    def test_lit_start_wraps_within_segment_count(self) -> None:
        bar = _SegmentBar(size_hint=(None, None), size=(180, 14))
        for _ in range(50):
            Clock.tick()
        bar.stop()
        assert 0 <= bar._lit_start < bar.segment_count

    def test_stop_cancels_further_advancement(self) -> None:
        bar = _SegmentBar(size_hint=(None, None), size=(180, 14))
        for _ in range(3):
            Clock.tick()
        bar.stop()
        frozen = bar._lit_start
        for _ in range(10):
            Clock.tick()
        assert bar._lit_start == frozen, "stop() 后不应再推进(避免组件销毁后残留 Clock 事件)"


class TestLoadingScreen:
    """加载页整体 —— 图标 + 标题 + 读条, stop() 级联停止内部动画。"""

    def test_shows_icon_title_and_bar(self) -> None:
        screen = LoadingScreen(icon_path="data/icon.png")
        assert screen._title.text == "独奏者小屋"
        assert screen._icon.source == "data/icon.png"
        screen.stop()

    def test_stop_is_idempotent(self) -> None:
        screen = LoadingScreen(icon_path="data/icon.png")
        screen.stop()
        screen.stop()  # 不应抛异常(如 build() 异常路径重复调用)
