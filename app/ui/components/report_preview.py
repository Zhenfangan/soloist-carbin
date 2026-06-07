"""ReportPreview — 战报全屏弹层。

Y 轴从底部滑入，包含战报长图预览 + 保存/结算按钮。
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from kivy.animation import Animation
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView

from app.ui.components.pixel_button import PixelButton
from app.ui.tokens import (
    BG_CREAM,
    CARD_PADDING,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    GRID_UNIT,
    TEXT_BROWN,
    TEXT_GRAY,
)

if TYPE_CHECKING:
    from app.models.report import ReportData


def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)


class ReportPreview(ModalView):  # type: ignore[misc]
    """全屏战报预览弹层。

    Args:
        image_path: 战报 PNG 图片路径 (Android 端使用)
        date_str: 日期字符串 (如 "2026.6.1")
        report_data: ReportData 战报数据 (传此参数时优先渲染 Kivy widget)
        on_save: 保存回调
        on_settle: 结算回调
    """

    def __init__(
        self,
        image_path: str = "",
        date_str: str = "",
        report_data: ReportData | None = None,
        on_save: Any = None,
        on_settle: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.background = ""
        self.background_color = (0, 0, 0, 0)

        root = FloatLayout()

        # 半透明遮罩
        with root.canvas.before:
            Color(0, 0, 0, 0.6)
            self._mask = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_mask, pos=self._update_mask)

        # 弹层主体
        panel = FloatLayout(
            size_hint=(1, 0.9),
            pos_hint={"x": 0, "y": 0},
        )
        with panel.canvas.before:
            Color(*_to_rgba(BG_CREAM))
            Rectangle(pos=panel.pos, size=panel.size)
        panel.bind(pos=lambda w, _: w.canvas.before.clear() or self._draw_panel_bg(w),
                   size=lambda w, _: w.canvas.before.clear() or self._draw_panel_bg(w))

        # 顶部标题
        title = Label(
            text=f"{date_str} 战报" if date_str else "今日战报",
            font_size=FONT_SIZE_TITLE,
            color=_to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=48,
            pos_hint={"x": 0, "y": 0.92},
            halign="center",
            valign="middle",
        )
        panel.add_widget(title)

        # 战报内容预览 (可滚动)
        scroll = ScrollView(
            size_hint=(1, None),
            pos_hint={"x": 0, "y": 0.12},
        )
        self._scroll_view = scroll
        # 计算高度: 弹层90% - 标题48 - 底部按钮80
        panel.bind(size=lambda w, v: setattr(scroll, "height", w.height * 0.9 - 48 - 80))

        self._content_box = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            spacing=GRID_UNIT,
            padding=[CARD_PADDING, 8],
        )
        self._content_box.bind(minimum_height=self._content_box.setter("height"))

        if report_data is not None:
            self._build_report_content(report_data)
        elif image_path and os.path.exists(image_path):
            img = Image(source=image_path, size_hint=(1, None), height=400)
            self._content_box.add_widget(img)
        else:
            self._content_box.add_widget(Label(
                text="战报数据加载中...",
                font_size=FONT_SIZE_BODY,
                color=_to_rgba(TEXT_BROWN),
                size_hint_y=None,
                height=100,
                halign="center",
                valign="middle",
            ))

        scroll.add_widget(self._content_box)
        panel.add_widget(scroll)

        # 底部按钮
        btn_area = BoxLayout(
            orientation="horizontal",
            spacing=GRID_UNIT * 2,
            size_hint=(1, None),
            height=56,
            pos_hint={"x": 0, "y": 0.01},
            padding=[CARD_PADDING, 6],
        )

        save_btn = PixelButton(
            text="保存至相册",
            color="#60C8FF",
            size_mode="normal",
            size_hint=(1, None),
        )
        if on_save:
            save_btn.bind(on_press=lambda _: on_save())

        settle_btn = PixelButton(
            text="退出并结算",
            color="#50E8B0",
            size_mode="normal",
            size_hint=(1, None),
        )
        settle_btn.bind(on_press=lambda _: self._handle_settle(on_settle))

        btn_area.add_widget(save_btn)
        btn_area.add_widget(settle_btn)
        panel.add_widget(btn_area)

        root.add_widget(panel)
        self.add_widget(root)

        # 入场动画
        panel.y = -panel.height
        anim = Animation(y=0, duration=0.25, t="out_quad")
        Clock = __import__("kivy.clock", fromlist=["Clock"]).Clock
        Clock.schedule_once(lambda dt: anim.start(panel), 0.05)

    def _update_mask(self, instance: Any, value: Any) -> None:
        self._mask.size = instance.size
        self._mask.pos = instance.pos

    @staticmethod
    def _draw_panel_bg(widget: Any) -> None:
        """绘制面板背景。"""
        with widget.canvas.before:
            Color(*_to_rgba(BG_CREAM))
            Rectangle(pos=widget.pos, size=widget.size)

    def _build_report_content(self, data: ReportData) -> None:
        """用 Kivy Label 渲染 ReportData 内容。

        生成日期标题、打卡详情、奖惩汇总、工作时长、
        承诺、完成任务、鼓励语等区块。
        """
        _add = self._content_box.add_widget
        brown = _to_rgba(TEXT_BROWN)
        gray = _to_rgba(TEXT_GRAY)

        # ── 日期 + 类型 ──
        day_type = "拍摄日" if data.is_shooting_day else "办公日"
        _add(Label(
            text=f"{data.date}  {day_type}",
            font_size=FONT_SIZE_TITLE,
            color=brown,
            size_hint_y=None,
            height=36,
            halign="center",
            valign="middle",
        ))

        # ── 打卡详情 ──
        _add(self._spacer(8))
        _add(self._section_title("打卡详情"))
        period_labels = {"morning": "上午", "afternoon": "下午", "evening": "晚上(加班)"}
        for p in data.periods:
            plabel = period_labels.get(p.period, p.period)
            checkin = p.checkin_time or "--"
            checkout = p.checkout_time or "--"
            _add(Label(
                text=f"  {plabel}  {checkin} ~ {checkout}  {p.status_label}",
                font_size=FONT_SIZE_BODY,
                color=brown,
                size_hint_y=None,
                height=24,
                halign="left",
                valign="middle",
            ))

        # ── 奖惩汇总 ──
        _add(self._spacer(4))
        _add(self._section_title("奖惩汇总"))
        _add(Label(
            text=f"  罚款: {data.penalty_total:.0f}",
            font_size=FONT_SIZE_BODY,
            color=_to_rgba("#e74c3c"),
            size_hint_y=None,
            height=24,
            halign="left",
            valign="middle",
        ))
        _add(Label(
            text=f"  奖励: +{data.reward_total:.0f}",
            font_size=FONT_SIZE_BODY,
            color=_to_rgba("#27ae60"),
            size_hint_y=None,
            height=24,
            halign="left",
            valign="middle",
        ))
        _add(Label(
            text=f"  净额: {data.net_amount:+.0f}",
            font_size=FONT_SIZE_BODY,
            color=brown,
            size_hint_y=None,
            height=24,
            halign="left",
            valign="middle",
        ))

        # ── 工作时长 ──
        _add(self._spacer(4))
        _add(self._section_title("工作时长"))
        _add(Label(
            text=f"  总计: {data.total_work_hours:.1f}h",
            font_size=FONT_SIZE_BODY,
            color=brown,
            size_hint_y=None,
            height=24,
            halign="left",
            valign="middle",
        ))
        if data.overtime_hours > 0:
            _add(Label(
                text=f"  加班: {data.overtime_hours:.1f}h",
                font_size=FONT_SIZE_BODY,
                color=_to_rgba("#e67e22"),
                size_hint_y=None,
                height=24,
                halign="left",
                valign="middle",
            ))

        # ── 满 8 小时鼓励 ──
        if data.total_work_hours >= 8:
            _add(self._spacer(4))
            _add(Label(
                text="今天工作超过 8 小时，太棒了！给自己一个大大的赞！",
                font_size=FONT_SIZE_BODY,
                color=_to_rgba("#e67e22"),
                size_hint_y=None,
                height=32,
                halign="center",
                valign="middle",
            ))

        # ── 男友承诺 ──
        if data.promise:
            _add(self._spacer(4))
            fulfilled_text = "已兑现" if data.promise.fulfilled else "未达标"
            _add(Label(
                text=f"男友承诺: {data.promise.reward_desc} x{data.promise.reward_qty}  ({fulfilled_text})",
                font_size=FONT_SIZE_BODY,
                color=brown,
                size_hint_y=None,
                height=28,
                halign="center",
                valign="middle",
            ))

        # ── 完成任务 ──
        if data.completed_tasks:
            _add(self._spacer(4))
            _add(self._section_title("完成的任务"))
            for task in data.completed_tasks:
                _add(Label(
                    text=f"  {task}",
                    font_size=FONT_SIZE_BODY,
                    color=_to_rgba("#27ae60"),
                    size_hint_y=None,
                    height=24,
                    halign="left",
                    valign="middle",
                ))

        # ── 鼓励语 ──
        _add(self._spacer(8))
        _add(Label(
            text=data.encouragement or "继续加油!",
            font_size=FONT_SIZE_SMALL,
            color=gray,
            size_hint_y=None,
            height=32,
            halign="center",
            valign="middle",
        ))

    # ── 内部辅助 ──

    @staticmethod
    def _section_title(text: str) -> Label:
        """生成区块标题 Label。"""
        return Label(
            text=text,
            font_size=FONT_SIZE_BODY,
            color=_to_rgba(TEXT_BROWN),
            size_hint_y=None,
            height=28,
            halign="left",
            valign="middle",
            bold=True,
        )

    @staticmethod
    def _spacer(height: int = 4) -> Label:
        """生成空白间隔 Label。"""
        return Label(text="", size_hint_y=None, height=height)

    def _handle_settle(self, on_settle: Any) -> None:
        if on_settle:
            on_settle()
        self.dismiss()
