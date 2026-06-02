"""OnboardingScreen — 首次引导分步设置。

分步引导：欢迎 → 上午时间 → 下午时间 → 工作日 → 惩罚 → 奖励 → 门槛 → 拍摄 → 完成。
"""

from __future__ import annotations

from typing import Any

from kivy.animation import Animation
from kivy.graphics import Color, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

from app.ui.components.pixel_button import PixelButton
from app.ui.tokens import (
    BG_CREAM,
    BORDER_WIDTH,
    CARD_WHITE,
    COLORS,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    PRIMARY_YELLOW,
    TEXT_BROWN,
    TEXT_GRAY,
)

_FG = TEXT_BROWN


def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)


class _StepCard(FloatLayout):  # type: ignore[misc]
    """单张引导卡片 — 像素边框 + 标题 + 内容 + 按钮。"""

    def __init__(self, mascot_label: str, title: str, subtitle: str = "", **kwargs: Any) -> None:
        super().__init__(size_hint=(1, 0.7), pos_hint={"center_x": 0.5, "center_y": 0.45}, **kwargs)
        self._mascot_label = mascot_label
        self._title = title
        self._subtitle = subtitle

        # 卡片背景
        self.bind(pos=self._redraw, size=self._redraw)

        # 角色图标
        self._mascot = Label(
            text=mascot_label,
            font_size=48,
            size_hint=(1, None),
            height=64,
            pos_hint={"x": 0, "y": 0.75},
            halign="center",
            valign="middle",
        )

        # 标题
        self._title_label = Label(
            text=title,
            font_size=FONT_SIZE_TITLE,
            color=_to_rgba(_FG),
            size_hint=(1, None),
            height=36,
            pos_hint={"x": 0, "y": 0.6},
            halign="center",
            valign="middle",
        )

        # 副标题
        self._sub_label = Label(
            text=subtitle,
            font_size=FONT_SIZE_SMALL,
            color=_to_rgba(TEXT_GRAY),
            size_hint=(1, None),
            height=24,
            pos_hint={"x": 0, "y": 0.45},
            halign="center",
            valign="middle",
        )

        self.add_widget(self._mascot)
        self.add_widget(self._title_label)
        self.add_widget(self._sub_label)

        self._content_area: FloatLayout | None = None

    def set_content(self, widget: FloatLayout) -> None:
        if self._content_area:
            self.remove_widget(self._content_area)
        self._content_area = widget
        widget.size_hint = (0.8, None)
        widget.height = 100
        widget.pos_hint = {"center_x": 0.5, "y": 0.12}
        self.add_widget(widget)

    def _redraw(self, *args: Any) -> None:
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        bw = BORDER_WIDTH
        with self.canvas.before:
            Color(*_to_rgba(COLORS["SHADOW_BLACK"]))
            Rectangle(pos=(x + 2, y - 2), size=(w, h))
            Color(*_to_rgba(CARD_WHITE))
            Rectangle(pos=(x, y), size=(w, h))
            Color(*_to_rgba("#FFFFFF"))
            Rectangle(pos=(x, y + h - bw), size=(w, bw))
            Rectangle(pos=(x, y), size=(bw, h))
            Color(*_to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(x, y), size=(w, bw))
            Rectangle(pos=(x + w - bw, y), size=(w, h))


def _make_time_picker_row(label: str, initial: str) -> FloatLayout:
    """生成时间选择行。"""
    row = FloatLayout(size_hint=(1, None), height=48)
    lbl = Label(
        text=label,
        font_size=FONT_SIZE_BODY,
        color=_to_rgba(_FG),
        size_hint=(None, 1),
        width=120,
        pos_hint={"x": 0, "y": 0},
        halign="left",
        valign="middle",
    )
    val_btn = Label(
        text=initial,
        font_size=FONT_SIZE_BODY,
        color=_to_rgba(_FG),
        size_hint=(None, 1),
        width=80,
        pos_hint={"right": 1, "y": 0},
        halign="right",
        valign="middle",
    )
    row.add_widget(lbl)
    row.add_widget(val_btn)
    return row


def _make_weekday_picker(work_days: list[int]) -> FloatLayout:
    """生成工作日多选行。"""
    row = FloatLayout(size_hint=(1, None), height=48)
    names = ["一", "二", "三", "四", "五", "六", "日"]
    btn_w = 42
    for i, name in enumerate(names):
        btn = Label(
            text=name,
            font_size=FONT_SIZE_BODY,
            color=_to_rgba(_FG) if i in work_days else _to_rgba(TEXT_GRAY),
            size_hint=(None, 1),
            width=btn_w,
            pos_hint={"x": i * btn_w / 350, "y": 0},
            halign="center",
            valign="middle",
        )
        row.add_widget(btn)
    return row


def _make_amount_row(label: str, initial: str) -> FloatLayout:
    """生成金额设置行。"""
    row = FloatLayout(size_hint=(1, None), height=48)
    lbl = Label(
        text=label,
        font_size=FONT_SIZE_BODY,
        color=_to_rgba(_FG),
        size_hint=(None, 1),
        width=120,
        pos_hint={"x": 0, "y": 0},
        halign="left",
        valign="middle",
    )
    val_btn = Label(
        text=initial,
        font_size=FONT_SIZE_BODY,
        color=_to_rgba(_FG),
        size_hint=(None, 1),
        width=100,
        pos_hint={"right": 1, "y": 0},
        halign="right",
        valign="middle",
    )
    row.add_widget(lbl)
    row.add_widget(val_btn)
    return row


class OnboardingScreen(FloatLayout):  # type: ignore[misc]
    """首次引导分步设置主容器。

    一次只显示一张卡片，底部有"下一步"/"跳过"按钮。
    """

    MASCOTS = ["🐻", "🐝", "🐶", "🐼", "🐻", "🐶", "🐼", "🐱", "🐻🐶"]

    def __init__(self, on_finish: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._on_finish = on_finish
        self._step = 0
        self._collected: dict[str, str] = {}
        self._work_days: list[int] = [0, 1, 2, 3, 4]

        # 背景色
        with self.canvas.before:
            Color(*_to_rgba(BG_CREAM))
            self._bg = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_bg, pos=self._update_bg)

        # 步骤进度指示
        self._progress = Label(
            text="1 / 9",
            font_size=FONT_SIZE_SMALL,
            color=_to_rgba(TEXT_GRAY),
            size_hint=(1, None),
            height=24,
            pos_hint={"x": 0, "y": 0.93},
            halign="center",
            valign="middle",
        )
        self.add_widget(self._progress)

        # 底部按钮
        btn_area = FloatLayout(size_hint=(1, None), height=64, pos_hint={"x": 0, "y": 0.02})

        self._skip_btn = PixelButton(
            text="跳过",
            color=COLORS["CARD_SHADOW"],
            size_mode="small",
            size_hint=(None, None),
            width=100,
            pos_hint={"x": 0.05, "y": 0},
        )
        self._skip_btn.bind(on_press=lambda _: self._next_step())

        self._next_btn = PixelButton(
            text="下一步",
            color=PRIMARY_YELLOW,
            size_mode="normal",
            size_hint=(None, None),
            width=200,
            pos_hint={"center_x": 0.5, "y": 0},
        )
        self._next_btn.bind(on_press=lambda _: self._next_step())

        btn_area.add_widget(self._skip_btn)
        btn_area.add_widget(self._next_btn)
        self.add_widget(btn_area)

        # 初始卡片
        self._current_card: _StepCard | None = None
        self._show_step(0)

    def _update_bg(self, *args: Any) -> None:
        self._bg.size = self.size
        self._bg.pos = self.pos

    def _show_step(self, index: int) -> None:
        """显示指定步骤的卡片。"""
        if self._current_card:
            self._current_card.parent.remove_widget(self._current_card) if self._current_card.parent else None

        total = 9
        self._progress.text = f"{index + 1} / {total}"

        if index >= total:
            self._finish()
            return

        steps = [
            # (mascot, title, subtitle, content_factory)
            ("🐻", "欢迎来到\nSoloist Cabin Pro", "自律打卡，从今天开始", None),
            ("🐝 嗡嗡", "设置上午时间", "上班和下班时间", lambda: _make_time_picker_row("上午上班", "09:00")),
            ("🐶 旺仔", "设置下午时间", "上班和下班时间", lambda: _make_time_picker_row("下午上班", "14:00")),
            ("🐼 团团", "选择工作日", "勾选需要打卡的日子", lambda: _make_weekday_picker(self._work_days)),
            ("🐻 兜兜", "设置惩罚金额", "迟到 / 早退 / 旷工罚款", lambda: _make_amount_row("迟到罚款", "-10")),
            ("🐶 旺仔", "设置全勤奖励", "每月全勤奖励金额", lambda: _make_amount_row("全勤奖励", "+100")),
            ("🐼 团团", "男友奖励门槛", "每天工作满X小时触发", lambda: _make_amount_row("门槛时长", "8 小时")),
            ("🐱 咪咕", "拍摄日奖励", "拍摄日额外奖励金额", lambda: _make_amount_row("拍摄奖励", "+30")),
            ("🐻 兜兜 + 🐶 旺仔", "全部准备好了！", "开始你的自律之旅吧", None),
        ]

        mascot, title, subtitle, content_factory = steps[index]
        card = _StepCard(mascot_label=mascot, title=title, subtitle=subtitle)
        if content_factory:
            card.set_content(content_factory())

        self.add_widget(card)
        self._current_card = card

        # 最后一步改变按钮文字
        if index == len(steps) - 2:
            self._skip_btn.opacity = 0
        if index == len(steps) - 1:
            self._next_btn.text = "进入主界面"
            self._next_btn.set_color("#50E8B0")
            self._skip_btn.opacity = 0

        # 动画
        card.opacity = 0
        anim = Animation(opacity=1.0, duration=0.2)
        anim.start(card)

    def _next_step(self) -> None:
        self._step += 1
        self._show_step(self._step)

    def _finish(self) -> None:
        if self._on_finish:
            self._on_finish()
