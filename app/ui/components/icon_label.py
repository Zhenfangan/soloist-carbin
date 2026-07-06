"""IconLabel — 图标 + 文字组合行, emoji 的像素图标替代品。

Kivy markup Label 不支持行内图片标签, 故用 Image+Label 横向拼接替代
`f"{emj('✍️')} 签到"` 这类写法。支持一组 (icon_name|None, text) 片段,
覆盖单图标/双同图标/双异图标/变长拼接等实际场景(见
docs/superpowers/specs/2026-07-06-emoji-to-pixel-icons-design.md)。
"""

from __future__ import annotations

from typing import Any

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from app.ui.assets.loader import IconLoader, apply_pixel_filter
from app.ui.tokens import FONT_SIZE_BODY, TEXT_BROWN


def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)


class IconLabel(BoxLayout):  # type: ignore[misc]
    """图标 + 文字的组合行。

    属性:
        icon/text: 单段构造糖(等价于一个片段的 set_segments)
        icon_size: 图标显示边长(px), 默认 18 — 明显小于 32×32 源图, 随文字大小
    """

    def __init__(
        self,
        icon: str | None = None,
        text: str = "",
        font_size: int = FONT_SIZE_BODY,
        color: tuple[float, float, float, float] | None = None,
        icon_size: int = 18,
        spacing: int = 4,
        outline_color: tuple[float, float, float, float] | None = None,
        outline_width: int = 0,
        centered: bool = False,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint", (None, None))
        # size_hint 轴为 None 有两种调用方意图: "自适应内容大小"(默认场景)或
        # "固定尺寸, 与内容无关"(调用方显式传了 width/height, 如 status_box
        # ._title_label 的 height=28)。用 kwargs 是否显式带 width/height 区分,
        # 避免后者被 Kivy 布局引擎稍后算出的 minimum_height/width 静默覆盖。
        has_explicit_width = "width" in kwargs
        has_explicit_height = "height" in kwargs
        super().__init__(spacing=spacing, **kwargs)
        self._font_size = font_size
        self._color = color if color is not None else _to_rgba(TEXT_BROWN)
        self._icon_size = icon_size
        self._outline_color = outline_color
        self._outline_width = outline_width
        # centered: 两端加弹性 spacer 把图文挤到整行中间(日期头/连续出勤/
        # 卡片标题需要)。注意参数名不能叫 center —— Widget.center 是保留属性。
        self._centered = centered
        if self.size_hint_x is None and not has_explicit_width:
            self.bind(minimum_width=self.setter("width"))
        if self.size_hint_y is None and not has_explicit_height:
            self.bind(minimum_height=self.setter("height"))
        self.set_segments([(icon, text)])

    @property
    def color(self) -> tuple[float, float, float, float]:
        return self._color

    @color.setter
    def color(self, value: tuple[float, float, float, float]) -> None:
        """动态改色, 不重建 widget(原调用点常见模式: 设 text 后单独设 color)。"""
        self._color = value
        for child in self.children:
            if isinstance(child, Label):
                child.color = value

    @property
    def text(self) -> str:
        """组合行的纯文字内容(只读) — 按视觉顺序拼接各段 Label 文本, 跳过图标。

        大量既有断言写作 `assert "签到" in widget.text`, 迁移到 IconLabel 后需
        真实反映"这一行显示了什么文字"。Kivy add_widget 默认 index=0, children
        为逆序, 用 reversed() 还原视觉顺序。设置文字请用 set_status/set_segments。
        """
        return "".join(
            child.text for child in reversed(self.children)
            if isinstance(child, Label)
        )

    def do_layout(self, *largs: Any) -> None:
        """BoxLayout 只在 child pos_hint/size_hint 变化时重算位置,
        Label 的 texture_size 异步计算 → child.size 变化 → Kivy 不
        触发父级 do_layout → pos_hint center_y 用的是旧(默认 100×100)
        尺寸 → y 坐标算错。在此兜底: 对所有 Image/Label 子控件强制
        重算垂直居中, Spacer(纯 Widget)跳过(它填满整行高度)。
        """
        super().do_layout(*largs)
        for child in self.children:
            if isinstance(child, (Image, Label)):
                child.y = self.y + (self.height - child.height) / 2

    def set_status(self, icon: str | None, text: str) -> None:
        """单段动态更新 — 43/45 调用点的常见情况, 等价于 set_segments([(icon, text)])。"""
        self.set_segments([(icon, text)])

    def set_segments(self, segments: list[tuple[str | None, str]]) -> None:
        """N 段动态更新(清空重建子 widget), 覆盖 0/1/2+ 段的所有场景。"""
        self.clear_widgets()
        # centered 时首尾各加一个弹性 spacer, 两者等分行内剩余宽度 → 内容居中。
        # spacer 是纯 Widget, .text getter / .color setter 的 isinstance(Label)
        # 判断会自动跳过它, 不影响文字拼接与改色。
        if self._centered:
            self.add_widget(Widget(size_hint_x=1))
        _parent = self  # 闭包捕获, 避免循环变量延迟绑定问题
        for icon_name, text in segments:
            if icon_name is not None:
                img = Image(
                    source=str(IconLoader.get_icon_path(icon_name)),
                    size_hint=(None, None),
                    size=(self._icon_size, self._icon_size),
                    allow_stretch=True,
                    keep_ratio=True,
                    # 盒子高于内容时 BoxLayout 默认底部对齐, 会让文字沉到卡片
                    # 底部像溢出 —— 垂直居中锚定修正。
                    pos_hint={"center_y": 0.5},
                )
                apply_pixel_filter(img.texture)
                self.add_widget(img)
            label = Label(
                text=text,
                font_size=self._font_size,
                color=self._color,
                size_hint=(None, None),
                valign="middle",
                outline_color=self._outline_color or (0, 0, 0, 0),
                outline_width=self._outline_width,
                pos_hint={"center_y": 0.5},
            )
            # texture_size 异步计算 → Label 尺寸变化 → Kivy 不会自动
            # 触发父级 do_layout → pos_hint center_y 用旧尺寸算错 y。
            # 绑定里同时更新尺寸 + 触发父级重布局, 配合 do_layout 覆写
            # 在下一帧用真实尺寸重算垂直居中。
            def _on_ts(lb: Label, ts: tuple[int, int], p: IconLabel = _parent) -> None:
                setattr(lb, "size", ts)
                p._trigger_layout()

            label.bind(texture_size=_on_ts)
            label.text_size = (None, None)
            self.add_widget(label)
        if self._centered:
            self.add_widget(Widget(size_hint_x=1))
