"""CheckinScreen — 打卡主界面。

ScrollView 垂直布局:
- 日期头 + 连续出勤天数
- 三时段 PeriodCard (morning/afternoon/evening)
- StatusBox 状态显示
- TaskInlineList 任务清单
- 男友承诺区 (上午打卡后显示)
- "结束今日并查看战报" 大按钮
"""

from __future__ import annotations

from typing import Any

from kivy.clock import Clock
from kivy.logger import Logger
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from app.ui.animations.checkin_animation import checkin_success_sequence
from app.ui.components.period_card import PeriodCard
from app.ui.components.pixel_button import PixelButton
from app.ui.components.promise_input import PromiseInput
from app.ui.components.status_box import StatusBox
from app.ui.components.task_inline_list import TaskInlineList
from app.ui.tokens import (
    CARD_PADDING,
    DOPAMINE_COLORS,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    GRID_UNIT,
    TEXT_BROWN,
    TEXT_GRAY,
)

# 中文星期
WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 请假选项的中文显示
LEAVE_OPTION_LABELS: dict[str, str] = {
    "morning": "上午请假",
    "afternoon": "下午请假",
    "all_day": "请假一整天",
}


class CheckinScreen(ScrollView):  # type: ignore[misc]
    """打卡主屏幕。

    构造函数注入需要的 Service 实例。
    """

    def __init__(
        self,
        checkin_service: Any = None,
        promise_service: Any = None,
        motivation_service: Any = None,
        report_service: Any = None,
        shooting_service: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.do_scroll_x = False
        self.do_scroll_y = True

        # Services
        self._checkin_service = checkin_service
        self._promise_service = promise_service
        self._motivation_service = motivation_service
        self._report_service = report_service
        self._shooting_service = shooting_service

        # 状态
        self._date_str = ""
        self._day_status: Any = None
        self._periods_data: list[Any] = []
        self._current_period_index = 0
        self._morning_checked_in = False
        self._promise_shown = False

        # 主容器
        self._container = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            spacing=GRID_UNIT,
            padding=[CARD_PADDING, CARD_PADDING, CARD_PADDING, CARD_PADDING],
        )
        self._container.bind(minimum_height=self._container.setter("height"))
        self.add_widget(self._container)

        # 1. 日期头部
        self._date_header = Label(
            text="",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=30,
            halign="center",
            valign="middle",
        )
        self._container.add_widget(self._date_header)

        # 2. 连续出勤天数
        self._streak_label = Label(
            text="",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(DOPAMINE_COLORS["mint"]["light"]),
            size_hint=(1, None),
            height=20,
            halign="center",
            valign="middle",
        )
        self._container.add_widget(self._streak_label)

        # 3. 三时段卡片
        self._period_cards: dict[str, PeriodCard] = {}
        self._container.add_widget(FloatLayout(size_hint=(1, None), height=GRID_UNIT))

        def make_period_card(
            period_name: str,
            on_checkin: Any,
            on_checkout: Any,
            on_leave: Any,
        ) -> PeriodCard:
            card = PeriodCard(
                period_name=period_name,
                on_checkin=on_checkin,
                on_checkout=on_checkout,
                on_leave=on_leave,
                is_current=(period_name == "morning"),
                size_hint=(1, None),
            )
            if period_name == "morning":
                card.height = card._EXPANDED_HEIGHT
                card.card_state = "expanded"
            return card

        # 上午卡
        self._period_cards["morning"] = make_period_card(
            "morning",
            self._on_morning_checkin,
            self._on_checkout,
            self._on_leave,
        )
        self._container.add_widget(self._period_cards["morning"])

        # 下午卡
        self._period_cards["afternoon"] = make_period_card(
            "afternoon",
            lambda p: self._on_checkin("afternoon"),
            self._on_checkout,
            self._on_leave,
        )
        self._period_cards["afternoon"].card_state = "collapsed"
        self._container.add_widget(self._period_cards["afternoon"])

        # 晚上卡
        self._period_cards["evening"] = make_period_card(
            "evening",
            lambda p: self._on_checkin("evening"),
            self._on_checkout,
            self._on_leave,
        )
        self._period_cards["evening"].card_state = "collapsed"
        self._container.add_widget(self._period_cards["evening"])

        # 4. StatusBox
        self._status_box = StatusBox(
            size_hint=(1, None),
            height=130,
        )
        self._container.add_widget(self._status_box)

        # 5. TaskInlineList
        self._task_list = TaskInlineList(
            size_hint=(1, None),
            on_check=self._on_task_check,
            on_add=self._on_task_add,
        )
        self._container.add_widget(self._task_list)

        # 6. 承诺区（初始隐藏）
        self._promise_area = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=80,
            opacity=0,
            spacing=GRID_UNIT // 2,
        )
        self._promise_title = Label(
            text="兜兜：今日目标",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=24,
            halign="left",
            valign="middle",
        )
        self._promise_desc = Label(
            text="",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_GRAY),
            size_hint=(1, None),
            height=20,
            halign="left",
            valign="middle",
        )
        self._promise_area.add_widget(self._promise_title)
        self._promise_area.add_widget(self._promise_desc)
        self._container.add_widget(self._promise_area)

        # 7. 战报入口按钮（初始隐藏）
        self._report_btn = PixelButton(
            text="结束今日并查看战报",
            color=DOPAMINE_COLORS["mint"]["light"],
            size_mode="large",
            size_hint=(1, None),
            opacity=0,
            disabled=True,
        )
        self._report_btn.bind(on_press=lambda _: self._on_report())
        self._container.add_widget(self._report_btn)

        # 加载数据
        Clock.schedule_once(lambda dt: self._load_data(), 0)

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    @staticmethod
    def _format_chinese_date(date_str: str) -> str:
        """将 2026-06-01 格式化为 2026年6月1日。"""
        try:
            parts = date_str.split("-")
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            return f"{year}年{month}月{day}日"
        except (IndexError, ValueError):
            return date_str

    def _load_data(self) -> None:
        """加载今日数据。"""
        if not self._checkin_service:
            return

        from app.utils.clock import get_clock

        clock = get_clock()
        self._date_str = clock.today_str()

        # 日期头
        from datetime import datetime

        try:
            dt = datetime.strptime(self._date_str, "%Y-%m-%d")
            weekday = dt.isoweekday() - 1  # isoweekday: 1=Mon, 7=Sun → 0-6
            weekday_name = WEEKDAY_NAMES[weekday]
            chinese_date = self._format_chinese_date(self._date_str)
            self._date_header.text = f"{chinese_date} {weekday_name}"
        except ValueError:
            self._date_header.text = self._date_str

        # 连续出勤天数
        if self._motivation_service:
            try:
                streak = self._motivation_service.get_current_streak()
                self._streak_label.text = f"已连续正常出勤 {streak} 天"
            except Exception as e:
                Logger.error(f"CheckinScreen: 获取连续出勤失败: {e}")
                self._streak_label.text = ""

        # 今日状态
        if self._checkin_service:
            try:
                day_status = self._checkin_service.get_today_status(self._date_str)
                self._day_status = day_status
                self._periods_data = getattr(day_status, "periods", [])

                # 更新 PeriodCards
                for ps in self._periods_data:
                    period = ps.period
                    card = self._period_cards.get(period)
                    if card:
                        card.set_status_from_period(ps)

                # 更新 StatusBox
                self._status_box.update_status(day_status)

                # 更新当前时段
                self._determine_current_period()

                # 检查是否已签到
                for ps in self._periods_data:
                    if ps.period == "morning" and ps.checkin_time:
                        self._morning_checked_in = True
                        self._check_promise()

                # 检查是否应该显示战报按钮
                self._check_all_completed()
            except Exception as e:
                Logger.error(f"CheckinScreen: {e}")

        # 容器高度由 minimum_height 自动维护

    def _determine_current_period(self) -> None:
        """确定当前时段并展开对应卡片。"""
        # 简化版：根据打卡情况推断
        morning_completed = False
        afternoon_completed = False

        for ps in self._periods_data:
            if ps.period == "morning" and ps.status not in ("pending",):
                morning_completed = True
            if ps.period == "afternoon" and ps.status not in ("pending",):
                afternoon_completed = True

        if not morning_completed:
            self._current_period_index = 0
            self._period_cards["morning"].height = self._period_cards["morning"]._EXPANDED_HEIGHT
            self._period_cards["morning"].card_state = "expanded"
            self._period_cards["morning"].is_current = True
            self._period_cards["afternoon"].height = self._period_cards["afternoon"]._COLLAPSED_HEIGHT
            self._period_cards["afternoon"].card_state = "collapsed"
            self._period_cards["afternoon"].is_current = False
            self._period_cards["evening"].height = self._period_cards["evening"]._COLLAPSED_HEIGHT
            self._period_cards["evening"].card_state = "collapsed"
            self._period_cards["evening"].is_current = False
        elif not afternoon_completed:
            self._current_period_index = 1
            self._period_cards["morning"].height = self._period_cards["morning"]._COLLAPSED_HEIGHT
            self._period_cards["morning"].card_state = "completed"
            self._period_cards["morning"].is_current = False
            self._period_cards["afternoon"].height = self._period_cards["afternoon"]._EXPANDED_HEIGHT
            self._period_cards["afternoon"].card_state = "expanded"
            self._period_cards["afternoon"].is_current = True
            self._period_cards["evening"].height = self._period_cards["evening"]._COLLAPSED_HEIGHT
            self._period_cards["evening"].card_state = "collapsed"
            self._period_cards["evening"].is_current = False
        else:
            self._current_period_index = 2
            self._period_cards["morning"].height = self._period_cards["morning"]._COLLAPSED_HEIGHT
            self._period_cards["morning"].card_state = "completed"
            self._period_cards["morning"].is_current = False
            self._period_cards["afternoon"].height = self._period_cards["afternoon"]._COLLAPSED_HEIGHT
            self._period_cards["afternoon"].card_state = "completed"
            self._period_cards["afternoon"].is_current = False
            self._period_cards["evening"].height = self._period_cards["evening"]._EXPANDED_HEIGHT
            self._period_cards["evening"].card_state = "expanded"
            self._period_cards["evening"].is_current = True

    # ── 签到/签退 ──────────────────────────────────────────

    def _on_morning_checkin(self, period: str) -> None:
        """上午签到。"""
        self._do_checkin("morning")

    def _on_checkin(self, period: str) -> None:
        """签到回调。"""
        self._do_checkin(period)

    def _do_checkin(self, period: str) -> None:
        """执行签到。"""
        if not self._checkin_service:
            return

        try:
            result = self._checkin_service.check_in(self._date_str, period)
            # 更新卡片
            card = self._period_cards.get(period)
            if card:
                card.has_checked_in = True
                card.checkin_time = result.checkin_time

            self._morning_checked_in = True

            # 打卡成功动画 — 加在内容容器而非 ScrollView (SV 只能有一个子组件)
            if card:
                checkin_success_sequence(
                    container=self._container,
                    animating_widget=card._action_btn,
                    on_mascot_show=lambda: None,
                    on_mascot_hide=lambda: self._after_checkin_animation(period),
                    on_complete=lambda: None,
                )

            # 重新加载状态
            self._refresh_status()
        except Exception as e:
            Logger.error(f"CheckinScreen: {e}")

    def _on_checkout(self, period: str) -> None:
        """签退回调。"""
        if not self._checkin_service:
            return

        try:
            result = self._checkin_service.check_out(self._date_str, period)
            card = self._period_cards.get(period)
            if card:
                card.has_checked_out = True
                card.checkout_time = result.checkout_time

            # 标记完成
            self._refresh_status()
            self._check_all_completed()

            # 自动展开下一时段
            period_order = ["morning", "afternoon", "evening"]
            current_idx = period_order.index(period) if period in period_order else -1
            if current_idx < len(period_order) - 1:
                next_period = period_order[current_idx + 1]
                next_card = self._period_cards.get(next_period)
                if next_card:
                    next_card.height = next_card._EXPANDED_HEIGHT
                    next_card.card_state = "expanded"
                    next_card.is_current = True
        except Exception as e:
            Logger.error(f"CheckinScreen: {e}")

    def _after_checkin_animation(self, period: str) -> None:
        """打卡动画完成后的处理。"""
        # 折叠当前时段，展开下一时段
        period_order = ["morning", "afternoon", "evening"]
        current_idx = period_order.index(period) if period in period_order else -1

        if current_idx < len(period_order) - 1:
            next_period = period_order[current_idx + 1]
            next_card = self._period_cards.get(next_period)
            if next_card:
                next_card.height = next_card._EXPANDED_HEIGHT
                next_card.card_state = "expanded"
                next_card.is_current = True

        # 如果是上午签到，弹出承诺弹窗
        if period == "morning":
            self._show_promise_dialog()

    def _refresh_status(self) -> None:
        """刷新状态显示 — 拉取最新 day_status 并同步更新 StatusBox 与所有 PeriodCard。"""
        if not self._checkin_service:
            return
        try:
            day_status = self._checkin_service.get_today_status(self._date_str)
            self._day_status = day_status
            self._periods_data = getattr(day_status, "periods", [])
            self._status_box.update_status(day_status)
            # 同步刷新所有 PeriodCard，确保签到/签退后卡片状态正确 (B10+B11)
            for ps in self._periods_data:
                card = self._period_cards.get(ps.period)
                if card:
                    card.set_status_from_period(ps)
        except Exception as e:
            Logger.error(f"CheckinScreen: {e}")

    def _check_all_completed(self) -> None:
        """检查所有时段是否已完成。"""
        if not self._checkin_service:
            return
        try:
            day_status = self._checkin_service.get_today_status(self._date_str)
            periods = getattr(day_status, "periods", [])

            # 简化：检查上午和下午是否都已签退，或者有请假/旷工/拍摄等状态
            morning_ok = False
            afternoon_ok = False
            for ps in periods:
                if ps.period == "morning":
                    if ps.checkout_time or ps.status in ("leave", "absent", "absent_morning", "absent_afternoon", "shooting", "normal"):
                        if ps.status != "pending":
                            morning_ok = True
                if ps.period == "afternoon":
                    if ps.checkout_time or ps.status in ("leave", "absent", "absent_morning", "absent_afternoon", "shooting", "normal"):
                        if ps.status != "pending":
                            afternoon_ok = True

            if morning_ok and afternoon_ok:
                self._report_btn.opacity = 1.0
                self._report_btn.disabled = False
            else:
                self._report_btn.opacity = 0
                self._report_btn.disabled = True
        except Exception as e:
            Logger.error(f"CheckinScreen: {e}")

    # ── 请假 ────────────────────────────────────────────────

    def _on_leave(self, period: str) -> None:
        """请假按钮回调。"""
        if not self._checkin_service:
            return

        from app.utils.clock import get_clock

        clock = get_clock()
        current_time = clock.current_time_str()

        try:
            options = self._checkin_service.get_leave_options(self._date_str, current_time)
            if not options:
                return

            # 构建弹窗
            if len(options) == 1:
                self._apply_leave(options[0])
            else:
                # 多选项弹窗
                self._show_leave_options(options)
        except Exception as e:
            Logger.error(f"CheckinScreen: {e}")

    def _show_leave_options(self, options: list[str]) -> None:
        """显示请假选项弹窗。"""
        # 简化：按顺序使用第一个可用选项
        # 实际应用中可以弹出一个带选项的对话框
        if options:
            self._apply_leave(options[0])

    def _apply_leave(self, scope: str) -> None:
        """执行请假。"""
        if not self._checkin_service:
            return
        try:
            self._checkin_service.apply_leave(self._date_str, scope)
            self._refresh_status()
        except Exception as e:
            Logger.error(f"CheckinScreen: {e}")

    # ── 男友承诺 ────────────────────────────────────────────

    def _check_promise(self) -> None:
        """检查是否已有承诺。"""
        if not self._promise_service:
            return
        try:
            promise = self._promise_service.get_today_promise(self._date_str)
            if promise:
                self._show_promise_area(
                    promise.reward_desc,
                    promise.reward_qty,
                )
                self._promise_shown = True
        except Exception as e:
            Logger.error(f"CheckinScreen: {e}")

    def _show_promise_dialog(self) -> None:
        """弹出男友承诺输入弹窗。"""
        if self._promise_shown:
            return
        self._promise_shown = True

        hours = 8.0
        if self._promise_service:
            try:
                # 尝试获取设置的工作时长阈值
                total_hours = self._promise_service.calculate_total_hours(self._date_str)
                hours = max(4.0, total_hours + 4.0)
            except Exception as e:
                Logger.error(f"CheckinScreen: {e}")

        dialog = PromiseInput(
            hours_threshold=hours,
            on_done=lambda result: self._on_promise_done(result),
        )
        Clock.schedule_once(lambda dt: dialog.open(), 0.3)

    def _on_promise_done(self, result: dict[str, Any] | None) -> None:
        """承诺弹窗回调。"""
        if result is None:
            # 跳过
            return

        reward_desc = result.get("reward_desc", "")
        reward_qty = result.get("reward_qty", 1)

        if self._promise_service and reward_desc:
            try:
                self._promise_service.set_promise(
                    self._date_str,
                    reward_desc,
                    reward_qty,
                )
                self._show_promise_area(reward_desc, reward_qty)
            except Exception as e:
                Logger.error(f"CheckinScreen: {e}")

    def _show_promise_area(self, reward_desc: str, reward_qty: int) -> None:
        """承诺区显示。"""
        self._promise_area.opacity = 1.0
        self._promise_desc.text = f"如果今天工作满8小时，奖励：{reward_desc} x{reward_qty}"

    # ── 任务 ────────────────────────────────────────────────

    def _on_task_check(self, task_id: int, checked: bool) -> None:
        """任务勾选回调。"""
        pass  # 由 BetService 处理

    def _on_task_add(self) -> None:
        """添加任务回调。"""
        pass  # 后续实现

    # ── 战报 ────────────────────────────────────────────────

    def _on_report(self) -> None:
        """战报按钮回调 — 生成战报 + 弹出 ReportPreview。"""
        if not self._report_service:
            Logger.warning("CheckinScreen: report_service 未注入, 无法弹出战报")
            return

        try:
            self._report_service.generate_and_save(self._date_str)
        except Exception as e:
            Logger.error(f"CheckinScreen: 生成战报失败 {e}")
            return

        from app.ui.components.report_preview import ReportPreview
        preview = ReportPreview(
            image_path="",
            date_str=self._date_str,
            on_save=lambda: Logger.info("ReportPreview: 保存至相册 (Android 端实现)"),
            on_settle=lambda: Logger.info("ReportPreview: 退出并结算"),
        )
        preview.open()

