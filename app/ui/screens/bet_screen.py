"""BetScreen — 对赌主页面。

ScrollView 垂直布局: WeekSummaryHeader -> 任务列表 -> "+ 添加任务"入口
-> BetConfigSection (折叠) -> "周结算"按钮。
周日可用(明黄色)，其他时间灰色+提示"周日结算"。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.logger import Logger
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from app.services.bet_service import BetService
from app.ui.components.add_task_dialog import AddTaskDialog
from app.ui.components.bet_config_section import BetConfigSection
from app.ui.components.bet_task_item import BetTaskItem
from app.ui.components.pixel_button import PixelButton
from app.ui.components.settlement_dialog import SettlementDialog
from app.ui.components.week_summary_header import WeekSummaryHeader
from app.ui.tokens import (
    CARD_PADDING,
    CARD_WHITE,
    COLORS,
    FONT_SIZE_SMALL,
    GRID_UNIT,
    TEXT_GRAY,
)
from app.utils.clock import get_clock


class BetScreen(ScrollView):  # type: ignore[misc]
    """对赌主页面。

    构造函数注入:
        bet_service: BetService 实例
    """

    def __init__(self, bet_service: BetService, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._bet_service = bet_service

        # 周起始计算
        now: datetime = get_clock().now()
        self._week_start = self._get_week_start(now)

        # 主容器
        self._layout = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=GRID_UNIT,
            padding=[CARD_PADDING, GRID_UNIT, CARD_PADDING, GRID_UNIT * 2],
        )
        self._layout.bind(minimum_height=self._layout.setter("height"))

        # 白色背景
        with self._layout.canvas.before:
            Color(*self._to_rgba(CARD_WHITE))
            self._layout_bg = Rectangle(size=self._layout.size, pos=self._layout.pos)
        self._layout.bind(size=self._update_layout_bg, pos=self._update_layout_bg)

        self.add_widget(self._layout)

        # UI 构建
        self._build_ui()

        # 首次加载
        Clock.schedule_once(lambda dt: self.refresh(), 0.1)

    @staticmethod
    def _get_week_start(dt: datetime) -> str:
        """计算给定日期所在周的周一日期。"""
        monday = dt - timedelta(days=dt.weekday())
        return monday.strftime("%Y-%m-%d")

    # ---- UI 构建 ----

    def _build_ui(self) -> None:
        """构建所有 UI 组件。"""
        # 1. 本周总结浮层
        empty_summary: dict[str, object] = {
            "completed": 0,
            "extra_count": 0,
            "total_reward": 0.0,
            "completion_rate": 0.0,
            "total_tasks": 0,
            "config": None,
        }
        self._header = WeekSummaryHeader(summary=empty_summary, size_hint_y=None)
        self._layout.add_widget(self._header)

        # 2. 任务列表容器
        self._task_container = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=GRID_UNIT // 2,
        )
        self._task_container.bind(minimum_height=self._task_container.setter("height"))
        self._layout.add_widget(self._task_container)

        # 3. "+ 添加任务" 入口
        self._add_btn = PixelButton(
            text="+ 添加任务",
            color=COLORS["CARD_SHADOW"],
            size_mode="normal",
            size_hint_y=None,
        )
        self._add_btn.bind(on_press=lambda _: self._open_add_dialog())
        self._layout.add_widget(self._add_btn)

        # 4. 赏罚设置折叠区
        self._config_section = BetConfigSection(
            week_start=self._week_start,
            bet_service=self._bet_service,
            size_hint_y=None,
        )
        self._layout.add_widget(self._config_section)

        # 5. 周结算按钮
        self._settle_btn = PixelButton(
            text="周结算",
            color=COLORS["PRIMARY_YELLOW"],  # 默认明黄
            size_mode="large",
            size_hint_y=None,
            disabled=True,  # 默认禁用，根据日期更新
        )
        self._settle_btn.bind(on_press=lambda _: self._open_settlement_dialog())
        self._layout.add_widget(self._settle_btn)

        # 结算提示文字
        self._settle_hint = Label(
            text="",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_GRAY),
            size_hint_y=None,
            height=20,
            halign="center",
            valign="middle",
        )
        self._layout.add_widget(self._settle_hint)

        # 更新结算按钮状态
        self._update_settle_button()

    # ---- 数据刷新 ----

    def refresh(self) -> None:
        """刷新所有数据（任务列表 + 总结 + 配置）。"""
        try:
            tasks = self._bet_service.get_week_tasks(self._week_start)
            summary = self._bet_service.get_week_summary(self._week_start)

            # 更新总结
            self._header.update_summary(summary)

            # 重建任务列表
            self._rebuild_task_list(tasks)

            # 更新结算按钮
            self._update_settle_button()
        except Exception as e:
            Logger.error(f"BetScreen: {e}")

    def _rebuild_task_list(self, tasks: list[Any]) -> None:
        """清空并重建任务列表。"""
        self._task_container.clear_widgets()

        for task in tasks:
            item = BetTaskItem(
                task=task,
                on_progress=self._on_task_progress,
                on_edit=self._on_task_edit,
                on_complete=self._on_task_complete,
                on_delete=self._on_task_delete,
                size_hint_y=None,
            )
            self._task_container.add_widget(item)

    # ---- 任务操作回调 ----

    def _on_task_progress(self, task_id: int, delta: int) -> None:
        """任务进度更新 — delta 是增量 (+1 / -1)。"""
        try:
            self._bet_service.update_task_progress(task_id, delta)
            self.refresh()
        except Exception as e:
            Logger.error(f"BetScreen: {e}")

    def _on_task_complete(self, task_id: int) -> None:
        """任务完成。"""
        try:
            self._bet_service.complete_task(task_id)
            self.refresh()
        except Exception as e:
            Logger.error(f"BetScreen: {e}")

    def _on_task_edit(self, task_id: int) -> None:
        """打开编辑对话框, 预填当前任务的 desc 和 target_qty。"""
        try:
            tasks = self._bet_service.get_week_tasks(self._week_start)
            target = next((t for t in tasks if t.id == task_id), None)
            if not target:
                return

            from app.ui.components.add_task_dialog import AddTaskDialog

            def _save(new_desc: str, new_qty: int) -> None:
                self._bet_service.update_task(task_id, new_desc, new_qty)
                self.refresh()

            dialog = AddTaskDialog(
                on_add=_save,
                initial_desc=target.task_desc,
                initial_qty=target.target_qty,
                title_text="编辑任务",
                confirm_text="保存",
            )
            dialog.open()
        except Exception as e:
            Logger.error(f"BetScreen edit: {e}")

    def _on_task_delete(self, task_id: int) -> None:
        """任务删除。"""
        try:
            self._bet_service.delete_task(task_id)
            self.refresh()
        except Exception as e:
            Logger.error(f"BetScreen: {e}")

    # ---- 添加任务 ----

    def _open_add_dialog(self) -> None:
        """打开添加任务弹窗。"""
        dialog = AddTaskDialog(on_add=self._on_add_task)
        dialog.open()

    def _on_add_task(self, desc: str, qty: int) -> None:
        """添加任务确认。"""
        try:
            self._bet_service.create_task(self._week_start, desc, qty)
            self.refresh()
        except Exception as e:
            Logger.error(f"BetScreen: {e}")

    # ---- 结算 ----

    def _update_settle_button(self) -> None:
        """根据当前日期更新结算按钮状态。"""
        now: datetime = get_clock().now()
        is_sunday = now.weekday() == 6  # Sunday = 6

        self._settle_btn.disabled = not is_sunday
        if is_sunday:
            self._settle_btn.set_color(COLORS["PRIMARY_YELLOW"])
            self._settle_btn.opacity = 1.0
            self._settle_hint.text = ""
        else:
            self._settle_btn.set_color(COLORS["CARD_SHADOW"])
            self._settle_btn.opacity = 0.5
            self._settle_hint.text = "周日结算"

    def _open_settlement_dialog(self) -> None:
        """打开结算确认弹窗。"""
        try:
            summary = self._bet_service.get_week_summary(self._week_start)
            dialog = SettlementDialog(
                week_start=self._week_start,
                bet_service=self._bet_service,
                summary=summary,
                on_settled=self._on_settled,
            )
            dialog.open()
        except Exception as e:
            Logger.error(f"BetScreen: {e}")

    def _on_settled(self) -> None:
        """结算完成回调。"""
        self.refresh()

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    def _update_layout_bg(self, instance: Any, value: Any) -> None:
        self._layout_bg.size = instance.size
        self._layout_bg.pos = instance.pos
