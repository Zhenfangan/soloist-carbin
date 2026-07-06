"""IconLabel — 图标 + 文字组合行, emoji 的像素图标替代品。

背景: Kivy markup Label 不支持行内图片标签, 故用 Image+Label 横向拼接的组合组件
替代 `f"{emj('✍️')} 签到"` 这类写法。支持 0~N 个 (icon_name|None, text) 片段,
一个组件覆盖单图标/双同图标/双异图标/变长拼接所有真实场景(详见
docs/superpowers/specs/2026-07-06-emoji-to-pixel-icons-design.md)。
"""
from __future__ import annotations

from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from app.ui.components.icon_label import IconLabel


class TestIconLabelConstruction:
    def test_single_segment_with_icon(self) -> None:
        w = IconLabel(icon="icon_pen", text="签到")
        images = [c for c in w.children if isinstance(c, Image)]
        labels = [c for c in w.children if isinstance(c, Label)]
        assert len(images) == 1
        assert len(labels) == 1
        assert labels[0].text == "签到"
        assert "icon_pen.png" in images[0].source

    def test_icon_none_shows_no_icon(self) -> None:
        w = IconLabel(icon=None, text="纯文字")
        images = [c for c in w.children if isinstance(c, Image)]
        labels = [c for c in w.children if isinstance(c, Label)]
        assert len(images) == 0
        assert len(labels) == 1
        assert labels[0].text == "纯文字"

    def test_icon_applies_nearest_filter(self) -> None:
        w = IconLabel(icon="icon_pen", text="签到")
        images = [c for c in w.children if isinstance(c, Image)]
        texture = images[0].texture
        assert texture.mag_filter == "nearest"
        assert texture.min_filter == "nearest"

    def test_default_no_args_is_empty_text_no_icon(self) -> None:
        w = IconLabel()
        images = [c for c in w.children if isinstance(c, Image)]
        labels = [c for c in w.children if isinstance(c, Label)]
        assert len(images) == 0
        assert labels[0].text == ""


class TestSetStatus:
    """单段动态更新 — 覆盖 43/45 调用点的常见情况。"""

    def test_updates_text(self) -> None:
        w = IconLabel(icon="icon_clock", text="迟到")
        w.set_status("icon_clock", "旧文字")
        w.set_status(None, "新文字")
        labels = [c for c in w.children if isinstance(c, Label)]
        assert labels[0].text == "新文字"

    def test_updates_icon(self) -> None:
        w = IconLabel(icon="icon_clock", text="迟到")
        w.set_status("icon_run", "早退")
        images = [c for c in w.children if isinstance(c, Image)]
        assert len(images) == 1
        assert "icon_run.png" in images[0].source

    def test_switching_to_none_icon_removes_image(self) -> None:
        w = IconLabel(icon="icon_clock", text="迟到")
        w.set_status(None, "纯文字")
        images = [c for c in w.children if isinstance(c, Image)]
        assert len(images) == 0

    def test_switching_from_none_to_icon_adds_image(self) -> None:
        w = IconLabel(icon=None, text="纯文字")
        w.set_status("icon_clock", "迟到")
        images = [c for c in w.children if isinstance(c, Image)]
        assert len(images) == 1


class TestSetSegments:
    """N 段动态更新 — 覆盖 _summary_label(0~2段)/_check_label(1~2段)/_streak_label(首尾同图标)。"""

    def test_empty_segments_clears_children(self) -> None:
        w = IconLabel(icon="icon_pen", text="签到")
        w.set_segments([])
        assert len(w.children) == 0

    def test_single_segment(self) -> None:
        w = IconLabel()
        w.set_segments([("icon_pen", "09:05")])
        images = [c for c in w.children if isinstance(c, Image)]
        labels = [c for c in w.children if isinstance(c, Label)]
        assert len(images) == 1
        assert len(labels) == 1
        assert labels[0].text == "09:05"

    def test_two_segments_different_icons(self) -> None:
        """_check_label: ⏰迟到 🏃早退

        Kivy 的 add_widget 默认 index=0(插到最前), 故 .children 是逆序;
        用 reversed() 还原为添加/视觉顺序再断言。
        """
        w = IconLabel()
        w.set_segments([("icon_clock", "迟到"), ("icon_run", "早退")])
        ordered = list(reversed(w.children))
        images = [c for c in ordered if isinstance(c, Image)]
        labels = [c for c in ordered if isinstance(c, Label)]
        assert len(images) == 2
        assert len(labels) == 2
        assert [lb.text for lb in labels] == ["迟到", "早退"]
        assert "icon_clock.png" in images[0].source
        assert "icon_run.png" in images[1].source

    def test_two_segments_same_icon_first_and_last(self) -> None:
        """_streak_label: 🔥 已连续出勤N天 🔥 — 首尾同图标, 中段无图标。"""
        w = IconLabel()
        w.set_segments([("icon_flame", ""), (None, "已连续出勤 5 天"), ("icon_flame", "")])
        images = [c for c in w.children if isinstance(c, Image)]
        labels = [c for c in w.children if isinstance(c, Label)]
        assert len(images) == 2
        assert len(labels) == 3
        assert labels[1].text == "已连续出勤 5 天"

    def test_segments_preserve_order(self) -> None:
        """子 widget 顺序必须与 segments 列表顺序一致, 否则图文错位。

        (Kivy add_widget 默认 index=0, .children 是逆序, 用 reversed() 还原)
        """
        w = IconLabel()
        w.set_segments([("icon_pen", "A"), (None, "B"), ("icon_run", "C")])
        ordered = list(reversed(w.children))
        kinds = ["img" if isinstance(c, Image) else "lbl" for c in ordered]
        assert kinds == ["img", "lbl", "lbl", "img", "lbl"]

    def test_rebuild_clears_previous_children(self) -> None:
        """重复调用 set_segments 不应残留上一次的 widget(子 widget 数量翻倍)。"""
        w = IconLabel()
        w.set_segments([("icon_pen", "A"), ("icon_run", "B")])
        w.set_segments([("icon_clock", "C")])
        assert len(w.children) == 2  # 1 icon + 1 label, 不是 4+2


class TestDynamicColor:
    """原调用点常见模式: 设置 .text 后单独设置 .color(如旷工态变红)。
    IconLabel 需支持同样的交互, 不用整个重建。"""

    def test_color_setter_applies_to_existing_labels(self) -> None:
        """Kivy Label.color 是 ColorProperty, 取值为 list, 故与 tuple 字面量比较需转换。"""
        w = IconLabel(icon="icon_pen", text="签到")
        w.color = (1, 0, 0, 1)
        labels = [c for c in w.children if isinstance(c, Label)]
        assert list(labels[0].color) == [1, 0, 0, 1]

    def test_color_setter_applies_to_future_segments(self) -> None:
        """set_segments 重建后, 新 Label 仍延续最近设置的颜色。"""
        w = IconLabel(icon="icon_pen", text="签到")
        w.color = (1, 0, 0, 1)
        w.set_segments([("icon_run", "早退"), (None, "备注")])
        labels = [c for c in w.children if isinstance(c, Label)]
        assert all(list(lb.color) == [1, 0, 0, 1] for lb in labels)

    def test_color_getter_returns_current_color(self) -> None:
        w = IconLabel(icon="icon_pen", text="签到", color=(0.2, 0.3, 0.4, 1))
        assert w.color == (0.2, 0.3, 0.4, 1)


class TestExplicitSizeOverride:
    """size_hint 轴为 None 不代表调用方想要"自适应内容大小" —— 也可能是
    "固定尺寸, 与内容无关"(如 status_box._title_label 的 height=28)。
    显式传入 width/height 时必须尊重, 不能被内部的 minimum_size 绑定覆盖。

    注意: BoxLayout.minimum_height/width 是 Kivy 布局引擎异步计算的, 构造后
    立即断言 height 仍是 28 会"假通过"(minimum_height 此时还是初始值 0,
    绑定即便存在也未触发)。故直接手动改 minimum_height 模拟布局引擎稍后
    算出真实值的时刻, 验证绑定是否真的不存在。
    """

    def test_explicit_height_not_overridden_by_content(self) -> None:
        w = IconLabel(icon="icon_pen", text="签到", size_hint=(1, None), height=28)
        w.minimum_height = 999  # 模拟布局引擎稍后算出的真实内容高度
        assert w.height == 28, "显式 height 被内部 minimum_height 绑定覆盖了"

    def test_explicit_width_not_overridden_by_content(self) -> None:
        w = IconLabel(icon="icon_pen", text="签到", size_hint=(None, 1), width=100)
        w.minimum_width = 999
        assert w.width == 100, "显式 width 被内部 minimum_width 绑定覆盖了"

    def test_no_explicit_height_still_auto_fits(self) -> None:
        """没显式传 height 时, 自适应绑定应仍然生效(不能被这次修复误伤)。"""
        w = IconLabel(icon="icon_pen", text="签到", size_hint=(1, None))
        w.minimum_height = 999
        assert w.height == 999


class TestOutlinePassthrough:
    """checkin_screen._streak_label 需要白色描边突出彩色文字, IconLabel 需透传。"""

    def test_outline_applied_to_label(self) -> None:
        w = IconLabel(icon=None, text="连续 5 天",
                      outline_color=(1, 1, 1, 1), outline_width=2)
        labels = [c for c in w.children if isinstance(c, Label)]
        assert list(labels[0].outline_color) == [1, 1, 1, 1]
        assert labels[0].outline_width == 2


class TestTextAccessor:
    """.text getter — 返回组合行的纯文字(按视觉顺序拼接各段 Label, 跳过图标)。

    大量既有断言写作 `assert "签到" in widget.text`; emoji 迁移到 IconLabel 后,
    组件需提供只读 text 以真实反映"这一行显示了什么文字"。设置文字仍走
    set_status/set_segments, 不提供 text setter(避免误丢图标)。
    """

    def test_text_returns_single_segment_text(self) -> None:
        w = IconLabel(icon="icon_pen", text="签到")
        assert w.text == "签到"

    def test_text_concatenates_in_visual_order(self) -> None:
        w = IconLabel()
        w.set_segments([("icon_clock", "迟到"), ("icon_run", "早退")])
        assert w.text == "迟到早退"

    def test_text_empty_when_no_label(self) -> None:
        w = IconLabel()
        w.set_segments([])
        assert w.text == ""


class TestVerticalCentering:
    """回归: IconLabel 是水平 BoxLayout, 当盒子高度大于内容(如 status_box 行/
    period_card 头部 48px)时, 固定尺寸的图标+文字会被 BoxLayout 底部对齐,
    导致"旷工"等文案沉到卡片底部像溢出。子控件须 pos_hint center_y=0.5 垂直居中。
    """

    def test_label_child_vertically_centered(self) -> None:
        w = IconLabel(icon=None, text="X")
        labels = [c for c in w.children if isinstance(c, Label)]
        assert labels[0].pos_hint.get("center_y") == 0.5

    def test_icon_child_vertically_centered(self) -> None:
        w = IconLabel(icon="icon_pen", text="X")
        images = [c for c in w.children if isinstance(c, Image)]
        assert images[0].pos_hint.get("center_y") == 0.5

    def test_vertical_centering_survives_rebuild(self) -> None:
        w = IconLabel(icon="icon_pen", text="X")
        w.set_segments([("icon_clock", "迟到"), (None, "备注")])
        for c in w.children:
            if isinstance(c, (Image, Label)):
                assert c.pos_hint.get("center_y") == 0.5


class TestHorizontalCentering:
    """opt-in 水平居中 — 日期头/连续出勤/状态框标题/今日任务标题需要内容居中,
    而 IconLabel 默认把图文靠左打包。centered=True 时两端加弹性 spacer 把内容挤到中间。"""

    def test_center_true_adds_two_flex_spacers(self) -> None:
        w = IconLabel(icon="icon_pen", text="X", centered=True, size_hint=(1, None), height=40)
        spacers = [c for c in w.children if type(c) is Widget]
        assert len(spacers) == 2
        assert all(s.size_hint_x == 1 for s in spacers)

    def test_center_false_has_no_spacers(self) -> None:
        w = IconLabel(icon="icon_pen", text="X")
        spacers = [c for c in w.children if type(c) is Widget]
        assert len(spacers) == 0

    def test_center_survives_rebuild(self) -> None:
        w = IconLabel(icon="icon_pen", text="X", centered=True, size_hint=(1, None), height=40)
        w.set_status(None, "Y")
        spacers = [c for c in w.children if type(c) is Widget]
        assert len(spacers) == 2

    def test_center_text_getter_ignores_spacers(self) -> None:
        w = IconLabel(centered=True, size_hint=(1, None), height=40)
        w.set_segments([("icon_clock", "迟到"), ("icon_run", "早退")])
        assert w.text == "迟到早退"

    def test_center_preserves_segment_order(self) -> None:
        w = IconLabel(centered=True, size_hint=(1, None), height=40)
        w.set_segments([("icon_flame", ""), (None, "中"), ("icon_flame", "")])
        # 去掉两端 spacer 后, 图文顺序不变(首尾火苗各带一个空 label + 中段 label)
        inner = [c for c in reversed(w.children) if isinstance(c, (Image, Label))]
        kinds = ["img" if isinstance(c, Image) else "lbl" for c in inner]
        assert kinds == ["img", "lbl", "lbl", "img", "lbl"]
