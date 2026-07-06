"""BetScreen — 对赌主页面。

ScrollView 垂直布局: WeekSummaryHeader -> 任务列表 -> "+ 添加任务"入口
-> BetConfigSection (折叠) -> "周结算"按钮。
周日可用(明黄色)，其他时间灰色+提示"周日结算"。
"""

from __future__ import annotations

from datetime import datetime
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
from app.ui.components.rest_days_dialog import RestDaysDialog
from app.ui.components.settlement_dialog import SettlementDialog
from app.ui.components.week_summary_header import WeekSummaryHeader
from app.ui.tokens import (
    CARD_PADDING,
    CARD_WHITE,
    COLORS,
    FONT_SIZE_SMALL,
    GRASS_INSET,
    GRID_UNIT,
    TEXT_GRAY,
)
from app.utils.clock import get_clock


class BetScreen(ScrollView):  # type: ignore[misc]
    """对赌主页面。

    构造函数注入:
        bet_service: BetService 实例
    """

    def __init__(self, bet_service: BetService, settings_service: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._bet_service = bet_service
        self._settings_service = settings_service

        # 灵活周期起点：优先未结算周期，否则自动创建
        self._week_start = bet_service.get_current_cycle_start()

        # 主容器
        self._layout = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=GRID_UNIT,
            padding=[CARD_PADDING, GRID_UNIT, CARD_PADDING, GRID_UNIT * 2],
        )
        self._layout.bind(minimum_height=self._layout.setter("height"))

        self.add_widget(self._layout)

        # UI 构建
        self._build_ui()

        # 首次加载
        Clock.schedule_once(lambda dt: self.refresh(), 0.1)

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

        # 1.5 其他收入(如拍摄日奖励) —— 独立于赌约结算之外, 仅当非零时显示
        self._other_income_label = Label(
            text="",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_GRAY),
            size_hint=(1, None),
            height=20,
            halign="center",
            valign="middle",
            opacity=0,
        )
        self._layout.add_widget(self._other_income_label)

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
            # 自动补扣滞纳金
            self._bet_service.accrue_late_fees(self._week_start)

            tasks = self._bet_service.get_week_tasks(self._week_start)
            summary = self._bet_service.get_week_summary(self._week_start)

            # 更新总结
            self._header.update_summary(summary)

            # 其他收入(如拍摄日奖励) —— 仅非零时显示, 避免空条目占地方
            other_income = self._bet_service.get_other_income(self._week_start)
            if other_income > 0:
                self._other_income_label.text = f"其他收入: 拍摄奖励 +{other_income:.0f} 元"
                self._other_income_label.opacity = 1
            else:
                self._other_income_label.text = ""
                self._other_income_label.opacity = 0

            # 重建任务列表
            self._rebuild_task_list(tasks)

            # 更新结算按钮（传入 summary 以获取 status）
            self._update_settle_button(summary)

            # 检查是否有旧周期未结清 → 阻塞编辑
            can_edit = self._bet_service.can_start_new_week(
                exclude_week_start=self._week_start
            )
            self._add_btn.disabled = not can_edit
            self._config_section.disabled = not can_edit
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

    def _update_settle_button(self, summary: dict[str, object] | None = None) -> None:
        """根据当前周状态更新结算按钮。"""
        if summary is None:
            try:
                summary = self._bet_service.get_week_summary(self._week_start)
            except Exception:
                return

        status = str(summary.get("status", "active"))
        now: datetime = get_clock().now()
        weekday = now.weekday()  # 0=Monday ... 6=Sunday

        if status == "settled":
            self._settle_btn.text = "已结算 ✓"
            self._settle_btn.disabled = True
            self._settle_btn.set_color(COLORS["CARD_SHADOW"])
            self._settle_btn.opacity = 0.5
            self._settle_hint.text = ""
        elif status == "late":
            accrued = float(summary.get("accrued_late_fees", 0))
            self._settle_btn.text = f"完成结算 (滞纳金 -{int(accrued)})"
            self._settle_btn.disabled = False
            self._settle_btn.set_color(COLORS["PRIMARY_YELLOW"])
            self._settle_btn.opacity = 1.0
            self._settle_hint.text = ""
        else:  # active
            total_tasks = int(summary.get("total_tasks", 0) or 0)
            completed = int(summary.get("completed", 0) or 0)
            uncompleted = total_tasks - completed

            if total_tasks == 0:
                # 无任务，不允许结算
                self._settle_btn.text = "周结算"
                self._settle_btn.disabled = True
                self._settle_btn.set_color(COLORS["CARD_SHADOW"])
                self._settle_btn.opacity = 0.5
                self._settle_hint.text = "周日结算" if weekday != 6 else "请先添加任务"
            elif weekday == 6 and uncompleted == 0:
                # 周日 + 全部完成 → 正常结算
                self._settle_btn.text = "周结算 ✓"
                self._settle_btn.disabled = False
                self._settle_btn.set_color(COLORS["PRIMARY_YELLOW"])
                self._settle_btn.opacity = 1.0
                self._settle_hint.text = ""
            elif weekday == 6:
                # 周日 + 有未完成 → 期限未过，用户还有一整天可以完成
                self._settle_btn.text = "周结算"
                self._settle_btn.disabled = True
                self._settle_btn.set_color(COLORS["CARD_SHADOW"])
                self._settle_btn.opacity = 0.5
                self._settle_hint.text = "周日结算，请完成全部任务"
            elif weekday != 6 and uncompleted > 0:
                # 周一之后（已超时）+ 有未完成 → 进入滞纳期
                self._settle_btn.text = "结算并进入滞纳期"
                self._settle_btn.disabled = False
                self._settle_btn.set_color(COLORS["PRIMARY_YELLOW"])
                self._settle_btn.opacity = 1.0
                self._settle_hint.text = ""
            elif weekday != 6 and uncompleted == 0:
                # 周一之后 + 全部完成（补结算）
                self._settle_btn.text = "周结算 ✓"
                self._settle_btn.disabled = False
                self._settle_btn.set_color(COLORS["PRIMARY_YELLOW"])
                self._settle_btn.opacity = 1.0
                self._settle_hint.text = ""
            else:
                self._settle_btn.text = "周结算"
                self._settle_btn.disabled = True
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
        """结算完成回调 —— 切换到新周期、刷新, 并询问这个周期休息几天。"""
        self._week_start = self._bet_service.get_current_cycle_start()
        self._config_section._week_start = self._week_start
        self._config_section._load_config()
        self.refresh()
        self._prompt_rest_days()

    def _prompt_rest_days(self) -> None:
        """弹出"休息几天"弹窗 —— 独立于赌约结算之外, 不影响赌约本身的数据。"""
        if not self._settings_service:
            return
        dialog = RestDaysDialog(on_confirm=self._on_rest_days_chosen)
        dialog.open()

    def _on_rest_days_chosen(self, days: int | None) -> None:
        """休息天数确认回调 —— days=None 表示用户选择不休息。
        休息期从明天起算: 填 2 天 → 明天+后天休息, 今天不算在内。
        """
        if days is None or not self._settings_service:
            return
        try:
            from datetime import datetime, timedelta
            today = get_clock().today_str()
            tomorrow = (
                datetime.strptime(today, "%Y-%m-%d") + timedelta(days=1)
            ).strftime("%Y-%m-%d")
            self._settings_service.start_rest_period(tomorrow, days)
        except Exception as e:
            Logger.error(f"BetScreen: 开始休息期失败 {e}")

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

