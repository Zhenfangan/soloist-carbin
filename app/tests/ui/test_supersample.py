"""文字超采样 —— fonts.py 的超采样系数 + Label.texture_update 编排。

背景: 真机把 420 逻辑画布用 ScatterLayout 整体线性放大约 2.57x, 文字先按逻辑
小字号光栅化再被 GPU 拉大 → 边缘发糊。超采样让 Label 在光栅化时用 font_size×SS
(得到 SS 倍分辨率的高清字形), 渲染后把 texture_size÷SS 压回(布局占用分毫不变),
经 ScatterLayout ×SS 放大后高清纹理 1:1 呈现, 不糊。

编排逻辑抽成 _supersample_texture_update(label, orig, ss), orig 可注入 → 无需 GL
即可精确单测"放大 → 还原 → 压回"三步。SS<=1 时(桌面/测试锁定 420 窗口)整个
patch 退化为纯透传, 桌面渲染与全量测试均不受影响。
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest


class _FakeCore:
    """模拟 Kivy CoreLabel: options 为普通 dict, usersize 为 [w, h](None=该轴不约束)。"""

    def __init__(self, font_size: float = 14, usersize: list | None = None) -> None:
        self.options = {"font_size": font_size}
        self.usersize = usersize if usersize is not None else [None, None]


class _FakeLabel:
    """模拟 Kivy Label widget 的超采样接触面(_label / texture / texture_size)。"""

    def __init__(self, font_size: float = 14, usersize: list | None = None) -> None:
        self._label = _FakeCore(font_size, usersize)
        self.texture = None
        self.texture_size = [0, 0]


def _make_orig(recorder: dict):
    """模拟 Kivy Label.texture_update: 用当前 core.options['font_size'] 光栅化,
    纹理尺寸正比字号(高=字号, 宽=3×高), 并设 self.texture / self.texture_size。
    recorder 捕获"渲染那一刻"的字号/usersize, 用于断言超采样确实放大了光栅化参数。
    """

    def _orig(label, *largs):
        fs = label._label.options["font_size"]
        recorder["render_font_size"] = fs
        recorder["render_usersize"] = list(label._label.usersize)
        h = int(round(fs))
        w = h * 3
        label.texture = SimpleNamespace(size=(w, h))
        label.texture_size = [w, h]

    return _orig


@pytest.fixture(autouse=True)
def _reset_scale():
    """每个测试前后把全局超采样系数还原为 1.0, 防跨测试污染。"""
    from app.ui.fonts import set_supersample_scale

    set_supersample_scale(1.0)
    yield
    set_supersample_scale(1.0)


class TestSupersampleScaleAccessor:
    def test_default_scale_is_one(self) -> None:
        from app.ui.fonts import get_supersample_scale

        assert get_supersample_scale() == 1.0

    def test_set_and_get(self) -> None:
        from app.ui.fonts import get_supersample_scale, set_supersample_scale

        set_supersample_scale(2.5)
        assert get_supersample_scale() == 2.5


class TestSupersampleTextureUpdate:
    def test_ss_le_1_passthrough(self) -> None:
        """SS<=1: 直接透传 orig — 不放大字号, 不压回 texture_size(桌面/测试免疫)。"""
        from app.ui.fonts import _supersample_texture_update

        rec: dict = {}
        lb = _FakeLabel(font_size=14)
        _supersample_texture_update(lb, _make_orig(rec), 1.0)

        assert rec["render_font_size"] == 14
        assert lb.texture_size == [42, 14]

    def test_ss_gt_1_enlarges_font_at_render(self) -> None:
        """SS>1: 光栅化时字号×SS → 得到高清字形纹理。"""
        from app.ui.fonts import _supersample_texture_update

        rec: dict = {}
        _supersample_texture_update(_FakeLabel(font_size=14), _make_orig(rec), 2.5)

        assert rec["render_font_size"] == pytest.approx(35.0)

    def test_ss_gt_1_restores_font_after_render(self) -> None:
        """渲染后 core 字号还原, 不污染后续渲染。"""
        from app.ui.fonts import _supersample_texture_update

        lb = _FakeLabel(font_size=14)
        _supersample_texture_update(lb, _make_orig({}), 2.5)

        assert lb._label.options["font_size"] == 14

    def test_ss_gt_1_shrinks_texture_size_back(self) -> None:
        """渲染后 texture_size÷SS 压回 1x → 布局占用与普通 Label 一致。"""
        from app.ui.fonts import _supersample_texture_update

        lb = _FakeLabel(font_size=14)
        _supersample_texture_update(lb, _make_orig({}), 2.5)

        # orig 以 35px 渲染 → texture (105, 35); 压回 /2.5 → [42, 14]
        assert lb.texture_size[0] == pytest.approx(42.0)
        assert lb.texture_size[1] == pytest.approx(14.0)

    def test_texture_stays_high_res(self) -> None:
        """压回的只是绘制矩形(texture_size); texture 本身保持 SS 倍高清像素。"""
        from app.ui.fonts import _supersample_texture_update

        lb = _FakeLabel(font_size=14)
        _supersample_texture_update(lb, _make_orig({}), 2.5)

        assert lb.texture.size == (105, 35)

    def test_ss_gt_1_scales_usersize_at_render(self) -> None:
        """text_size(usersize)光栅化时同步×SS → 换行框正确, 换行位置不变。"""
        from app.ui.fonts import _supersample_texture_update

        rec: dict = {}
        _supersample_texture_update(_FakeLabel(usersize=[200, None]), _make_orig(rec), 2.5)

        assert rec["render_usersize"] == [500, None]

    def test_ss_gt_1_restores_usersize_after_render(self) -> None:
        from app.ui.fonts import _supersample_texture_update

        lb = _FakeLabel(usersize=[200, None])
        _supersample_texture_update(lb, _make_orig({}), 2.5)

        assert lb._label.usersize == [200, None]

    def test_usersize_none_axes_untouched(self) -> None:
        """usersize 的 None 轴(不约束)在放大时保持 None, 不因 None×SS 报错。"""
        from app.ui.fonts import _supersample_texture_update

        rec: dict = {}
        lb = _FakeLabel(usersize=[None, None])
        _supersample_texture_update(lb, _make_orig(rec), 2.5)

        assert rec["render_usersize"] == [None, None]
        assert lb._label.usersize == [None, None]

    def test_empty_texture_is_noop(self) -> None:
        """空文本时 orig 未产生 texture(None) → 压回步骤跳过, 不崩。"""
        from app.ui.fonts import _supersample_texture_update

        def _orig_empty(label, *largs):
            label.texture = None
            label.texture_size = [0, 0]

        lb = _FakeLabel()
        _supersample_texture_update(lb, _orig_empty, 2.5)  # 不应抛异常

        assert lb.texture is None


class TestPatchInstallation:
    """补丁装到真实 Kivy Label 上必须存活于 Clock/WeakMethod 回调路径。"""

    def test_patched_update_keeps_texture_update_name(self) -> None:
        """补丁函数装到 Label.texture_update 后, 其 __name__ 必须仍是 'texture_update'。

        Kivy 用 Clock.create_trigger(self.texture_update) + WeakMethod 调度纹理刷新,
        WeakMethod 靠 __name__ 做 getattr(instance, name) 回调; 名字不符则回调时
        AttributeError, 真机/全量测试崩。
        """
        from kivy.uix.label import Label

        from app.ui.fonts import apply_global_font

        apply_global_font()
        assert Label.texture_update.__name__ == "texture_update"

    def test_patched_update_survives_clock_trigger(self) -> None:
        """改 font_size 触发 _trigger_texture_update → Clock 调度回调, tick 不应崩。"""
        from kivy.clock import Clock
        from kivy.uix.label import Label

        from app.ui.fonts import apply_global_font

        apply_global_font()
        label = Label(text="x")
        label.font_size = 20  # 触发 Clock 调度的 texture_update 回调
        Clock.tick()  # 名字不符会在此 AttributeError
