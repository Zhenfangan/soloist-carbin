"""TaskInlineList — 嵌入打卡页的任务清单组件。

显示今日任务列表，每项含 PixelCheckbox + 任务描述。
底部 "+ 添加任务" 入口。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

from app.ui.components.pixel_checkbox import PixelCheckbox
from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_PADDING,
    CARD_WHITE,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    GRID_UNIT,
    SHADOW_BLACK,
    TEXT_GRAY,
)

MAX_DISPLAY_TASKS = 5


class TaskInlineList(FloatLayout):  # type: ignore[misc]
    """嵌入打卡页的任务清单。

    通常只显示 5 条，支持勾选标记完成。

    属性:
        tasks: 任务列表 [{"id": int, "desc": str, "done": bool}, ...]
        on_check: 勾选回调 (task_id, checked) -> None
        on_add: 添加任务回调 () -> None
    """

    def __init__(
        self,
        tasks: list[dict[str, Any]] | None = None,
        on_check: Callable[[int, bool], Any] | None = None,
        on_add: Callable[[], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.size_hint = (1, None)
        self.height = 120

        self._tasks: list[dict[str, Any]] = tasks or []
        self._on_check_cb = on_check
        self._on_add_cb = on_add
        self._checkboxes: list[PixelCheckbox] = []

        # 标题
        self._title_label = Label(
            text="今日任务",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_GRAY),
            size_hint=(1, None),
            height=20,
            pos_hint={"x": 0, "y": 0},
            halign="left",
            valign="middle",
        )

        # 任务列表容器
        self._list_layout = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            pos_hint={"x": 0, "y": 0},
            spacing=2,
        )

        # 添加任务入口
        self._add_label = Label(
            text="+ 添加任务",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_GRAY),
            size_hint=(1, None),
            height=28,
            halign="left",
            valign="middle",
        )
        self._add_label.bind(on_touch_down=self._on_add_touch)

        self.add_widget(self._list_layout)
        self.add_widget(self._title_label)
        self.add_widget(self._add_label)

        self.bind(pos=self._redraw, size=self._redraw)

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    def set_tasks(self, tasks: list[dict[str, Any]]) -> None:
        """更新任务列表。"""
        self._tasks = tasks[:MAX_DISPLAY_TASKS]
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        """重建任务行列表。"""
        self._list_layout.clear_widgets()
        self._checkboxes.clear()

        for task in self._tasks:
            task_id = task.get("id", 0)
            desc = task.get("desc", "")
            done = task.get("done", False)

            cb = PixelCheckbox(
                checked=done,
                label=desc,
                on_toggle=lambda checked, tid=task_id: self._on_check(tid, checked),  # type: ignore[misc]
                size_hint=(1, None),
                height=28,
            )
            self._checkboxes.append(cb)
            self._list_layout.add_widget(cb)

        # 更新高度
        row_count = max(1, len(self._tasks))
        total_height = 20 + 30 + row_count * 30 + 28 + GRID_UNIT * 2
        self.height = total_height

    def _on_check(self, task_id: int, checked: bool) -> None:
        """勾选回调。"""
        if self._on_check_cb:
            self._on_check_cb(task_id, checked)

    def _on_add_touch(self, instance: Any, touch: Any) -> bool:
        """添加任务点击。"""
        if self._add_label.collide_point(*touch.pos):
            if self._on_add_cb:
                self._on_add_cb()
            return True
        return False

    def _redraw(self, *args: Any) -> None:
        """重绘像素边框。"""
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        bw = BORDER_WIDTH

        with self.canvas.before:
            # 阴影
            Color(*self._to_rgba(SHADOW_BLACK))
            Rectangle(pos=(x + 2, y - 2), size=(w, h))
            # 背景
            Color(*self._to_rgba(CARD_WHITE))
            Rectangle(pos=(x, y), size=(w, h))
            # 凸起边框
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(x, y + h - bw), size=(w, bw))
            Rectangle(pos=(x, y), size=(bw, h))
            Color(*self._to_rgba("#F0E8D0"))
            Rectangle(pos=(x, y), size=(w, bw))
            Rectangle(pos=(x + w - bw, y), size=(w, h))

        # 更新子组件位置
        self._title_label.pos = (x + CARD_PADDING, y + h - 24)
        self._title_label.size = (w - CARD_PADDING * 2, 20)
        self._list_layout.pos = (x + CARD_PADDING, y + 32)
        self._list_layout.size = (w - CARD_PADDING * 2, max(1, len(self._tasks)) * 30)
        self._add_label.pos = (x + CARD_PADDING, y + 4)
        self._add_label.size = (w - CARD_PADDING * 2, 28)
