"""TaskInlineList — 嵌入打卡页的任务清单组件。

显示今日任务列表，每项含 PixelCheckbox + 任务描述。
底部 "+ 添加任务" 入口。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from app.ui.components.glass_bg import draw_glass_card_bg
from app.ui.components.pixel_checkbox import PixelCheckbox
from app.ui.fonts import emj
from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_PADDING,
    CARD_WHITE,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    GRID_UNIT,
    SHADOW_BLACK,
    TEXT_BROWN,
)

MAX_DISPLAY_TASKS = 20


class TaskInlineList(BoxLayout):  # type: ignore[misc]
    """嵌入打卡页的任务清单 — 垂直柱状排列。

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
        on_edit: Callable[[int], Any] | None = None,
        on_delete: Callable[[int], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("padding", [CARD_PADDING, GRID_UNIT, CARD_PADDING, GRID_UNIT])
        kwargs.setdefault("spacing", 2)
        super().__init__(**kwargs)
        # 内容自适应高度 — 添加任务后面板自动撑高, 否则固定 120 会限制溢出
        self.bind(minimum_height=self.setter("height"))

        self._tasks: list[dict[str, Any]] = tasks or []
        self._on_check_cb = on_check
        self._on_add_cb = on_add
        self._on_edit_cb = on_edit
        self._on_delete_cb = on_delete
        self._checkboxes: list[PixelCheckbox] = []

        # 标题 — 大字号显示
        self._title_label = Label(
            text=f"{emj('📝')} 今日任务",
            font_size=FONT_SIZE_TITLE,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=28,
            halign="left",
            valign="middle",
            bold=True,
            markup=True,
        )
        self.add_widget(self._title_label)

        # 任务列表容器
        self._list_layout = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            spacing=2,
        )
        self._list_layout.bind(minimum_height=self._list_layout.setter("height"))
        self.add_widget(self._list_layout)

        # 添加任务入口
        self._add_label = Label(
            text=f"{emj('➕')} 添加任务",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=28,
            halign="left",
            valign="middle",
            markup=True,
        )
        self._add_label.bind(on_touch_down=self._on_add_touch)
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

            label_tap = self._make_label_tap(task_id, desc) if (self._on_edit_cb or self._on_delete_cb) else None

            cb = PixelCheckbox(
                checked=done,
                label=desc,
                on_toggle=lambda checked, tid=task_id: self._on_check(tid, checked),  # type: ignore[misc]
                on_label_tap=label_tap,
                size_hint=(1, None),
                height=28,
            )
            self._checkboxes.append(cb)
            self._list_layout.add_widget(cb)

    def _make_label_tap(self, task_id: int, task_desc: str) -> Callable[[], None]:
        def _tap() -> None:
            from app.ui.components.pixel_dialog import TaskActionDialog
            dialog = TaskActionDialog(
                task_desc=task_desc,
                on_edit=lambda: self._on_edit_cb(task_id) if self._on_edit_cb else None,
                on_delete=lambda: self._on_delete_cb(task_id) if self._on_delete_cb else None,
            )
            dialog.open()
        return _tap

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
        """重绘玻璃背景。"""
        draw_glass_card_bg(self)
