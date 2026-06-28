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

from app.ui.components.checkin_success_panel import CheckinSuccessPanel
from app.ui.components.period_card import PeriodCard
from app.ui.components.pixel_button import PixelButton
from app.ui.components.promise_input import PromiseInput
from app.ui.components.status_box import StatusBox
from app.ui.components.task_inline_list import TaskInlineList
from app.ui.fonts import emj
from app.ui.tokens import (
    CARD_PADDING,
    DOPAMINE_COLORS,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    GRASS_INSET,
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
        bet_service: Any = None,
        camera_service: Any = None,
        settings_service: Any = None,
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
        self._bet_service = bet_service
        self._camera_service = camera_service
        self._settings_service = settings_service

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
            padding=[CARD_PADDING, CARD_PADDING, CARD_PADDING, CARD_PADDING + GRASS_INSET],
        )
        self._container.bind(minimum_height=self._container.setter("height"))
        self.add_widget(self._container)

        # 1. 日期头部
        self._date_header = Label(
            text="",
            font_size=int(FONT_SIZE_TITLE * 1.4),
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=40,
            halign="center",
            valign="middle",
            bold=True,
            markup=True,
        )
        self._container.add_widget(self._date_header)

        # 2. 连续出勤天数 — 亮粉色 + 白色描边
        self._streak_label = Label(
            text="",
            font_size=int(FONT_SIZE_TITLE * 1.2),
            color=self._to_rgba(DOPAMINE_COLORS["coral"]["light"]),
            outline_color=self._to_rgba("#FFFFFF"),
            outline_width=2,
            size_hint=(1, None),
            height=0,  # 修复: 空数据时不占高度, text 变化时同步更新
            halign="center",
            valign="middle",
            bold=True,
            markup=True,
        )
        self._streak_label.bind(text=self._update_streak_height)
        self._container.add_widget(self._streak_label)

        # 3. 三时段卡片
        self._period_cards: dict[str, PeriodCard] = {}

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
            on_edit=self._on_task_edit,
            on_delete=self._on_task_delete,
        )
        self._container.add_widget(self._task_list)

        # 6. 承诺区（初始高度为 0，完全不可见不占位；填写目标后才撑开）
        self._promise_area = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=0,
            opacity=0,
            spacing=GRID_UNIT // 2,
        )
        self._promise_title = Label(
            text=f"{emj('🎯')} 今日目标",
            font_size=FONT_SIZE_TITLE,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=36,
            halign="left",
            valign="middle",
            bold=True,
            markup=True,
        )
        self._promise_desc = Label(
            text="",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=30,
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

    def _update_streak_height(self, *args: Any) -> None:
        """text 变化时同步 height — 空 text height=0, 非空 height=32。"""
        self._streak_label.height = 32 if self._streak_label.text else 0

    def refresh(self) -> None:
        """外部调用 — 切换 Tab 回打卡页时刷新数据。"""
        self._refresh_status()
        self._check_all_completed()

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
            self._date_header.text = f"{emj('📅')} {chinese_date} {weekday_name}"
        except ValueError:
            self._date_header.text = f"{emj('📅')} {self._date_str}"

        # 连续出勤天数
        if self._motivation_service:
            try:
                streak = self._motivation_service.get_current_streak()
                self._streak_label.text = f"{emj('🔥')} 已连续正常出勤 {streak} 天 {emj('🔥')}"
            except Exception as e:
                Logger.error(f"CheckinScreen: 获取连续出勤失败: {e}")
                self._streak_label.text = ""

        # 今日状态
        if self._checkin_service:
            try:
                self._checkin_service.mark_absent(self._date_str)
                day_status = self._checkin_service.get_today_status(self._date_str)
                self._day_status = day_status
                self._periods_data = getattr(day_status, "periods", [])

                # 更新 PeriodCards
                current_time = clock.current_time_str()
                start_times = {
                    "morning": (
                        self._settings_service.get("morning_start")
                        if self._settings_service else "09:00"
                    ),
                    "afternoon": (
                        self._settings_service.get("afternoon_start")
                        if self._settings_service else "14:00"
                    ),
                }
                end_times = {
                    "morning": (
                        self._settings_service.get("morning_end")
                        if self._settings_service else "12:00"
                    ),
                    "afternoon": (
                        self._settings_service.get("afternoon_end")
                        if self._settings_service else "18:00"
                    ),
                }
                for ps in self._periods_data:
                    period = ps.period
                    card = self._period_cards.get(period)
                    if card:
                        card.set_status_from_period(ps)
                        # 同步用户设置的时段起止时间
                        st = start_times.get(ps.period, "")
                        et = end_times.get(ps.period, "")
                        if st or et:
                            card.set_time_range(st, et)
                        card.leave_enabled = (
                            ps.status == "pending"
                            and ps.period in ("morning", "afternoon")
                            and bool(st)
                            and current_time < st
                        )

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

        # 今日任务 — 从 bet_service 加载本周任务
        if self._bet_service:
            try:
                from datetime import datetime, timedelta
                dt = datetime.strptime(self._date_str, "%Y-%m-%d")
                week_start = (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")
                tasks = self._bet_service.get_week_tasks(week_start)
                self._task_list.set_tasks([
                    {"id": t.id, "desc": t.task_desc, "done": bool(t.is_completed)}
                    for t in tasks
                ])
            except Exception as e:
                Logger.error(f"CheckinScreen: 加载任务失败 {e}")

    def _determine_current_period(self) -> None:
        """确定当前时段并展开对应卡片。

        终态（请假/旷工/拍摄）不阻塞后续时段：找到第一个需要用户操作的时段
        （pending 待签到 或 in_progress 待签退），展开它作为当前卡片。
        如果第一个是 in_progress（已签未退）且后续还有 pending，同时展开后续。
        """
        period_order = ["morning", "afternoon", "evening"]
        absent_statuses = {"absent", "absent_morning", "absent_afternoon"}
        terminal = {"absent", "absent_morning", "absent_afternoon", "leave", "shooting"}

        status_map = {ps.period: ps.status for ps in self._periods_data}
        checkin_map = {ps.period: ps.checkin_time for ps in self._periods_data}
        checkout_map = {ps.period: ps.checkout_time for ps in self._periods_data}

        def _resolved_state(period: str) -> str | None:
            s = status_map.get(period, "pending")
            if s in absent_statuses:
                return "absent"
            if s in terminal or checkout_map.get(period):
                return "completed"
            return None  # pending

        # 找第一个 in_progress（已签未退且非终态）和第一个 pending
        first_in_progress: str | None = None
        first_pending: str | None = None
        for p in period_order:
            s = status_map.get(p, "pending")
            if s in terminal or checkout_map.get(p):
                continue  # 终态或已完成，跳过
            if checkin_map.get(p):
                if first_in_progress is None:
                    first_in_progress = p
            else:
                if first_pending is None:
                    first_pending = p

        # 先全部折叠/完成
        for p in period_order:
            card = self._period_cards[p]
            card.height = card._COLLAPSED_HEIGHT
            card.card_state = _resolved_state(p) or "collapsed"
            card.is_current = False

        # 确定当前展开的时段
        current = first_in_progress or first_pending
        if current is None:
            self._current_period_index = 3
            return

        self._current_period_index = period_order.index(current)
        current_card = self._period_cards[current]
        current_card.height = current_card._EXPANDED_HEIGHT
        current_card.card_state = "expanded"
        current_card.is_current = True
        # 严格顺序：只展开当前一个时段，后续时段保持折叠直到当前签退完成

    # ── 签到/签退 ──────────────────────────────────────────

    def _on_morning_checkin(self, period: str) -> None:
        """上午签到。"""
        self._do_checkin("morning")

    def _on_checkin(self, period: str) -> None:
        """签到回调。"""
        self._do_checkin(period)

    def _do_checkin(self, period: str) -> None:
        """执行签到 — 有相机服务时先拍照，照片获取后再写打卡记录。"""
        if not self._checkin_service:
            return

        if self._camera_service:
            self._camera_service.take_photo(
                period=period,
                action="in",
                on_done=lambda path: self._finish_checkin(period, path),
            )
        else:
            self._finish_checkin(period, None)

    def _finish_checkin(self, period: str, photo_path: Any) -> None:
        """拍照完成后执行实际签到写库。photo_path=None 且有相机服务 → 用户取消，不写记录。"""
        if self._camera_service and photo_path is None:
            return

        try:
            result = self._checkin_service.check_in(
                self._date_str, period,
                str(photo_path) if photo_path else None,
            )
            card = self._period_cards.get(period)
            if card:
                card.has_checked_in = True
                card.checkin_time = result.checkin_time

            self._morning_checked_in = True

            if card:
                panel = CheckinSuccessPanel(
                    target_card=card,
                    is_checkin=True,
                    is_night=period in ("evening", "night"),
                    settings_service=self._settings_service,
                    on_dismiss_callback=lambda p=period: self._after_checkin_animation(p),
                )
                panel.open()
        except Exception as e:
            Logger.error(f"CheckinScreen: {e}")

    def _on_checkout(self, period: str) -> None:
        """签退回调 — 若在时段结束时间前签退，先弹确认框。"""
        if not self._checkin_service:
            return

        from app.utils.clock import get_clock
        clock = get_clock()
        current_time = clock.current_time_str()
        end_time = self._checkin_service.get_period_end_time(period)

        if end_time and current_time < end_time:
            _PERIOD_LABELS = {"morning": "上午", "afternoon": "下午", "evening": "晚间"}
            label = _PERIOD_LABELS.get(period, period)
            from app.ui.components.pixel_dialog import ConfirmDialog
            dialog = ConfirmDialog(
                title="确认提前签退",
                message=f"当前 {current_time}，{label}下班时间为 {end_time}，\n确定提前签退（记早退）吗？",
                confirm_text="确定签退",
                cancel_text="再等等",
                on_confirm=lambda: self._do_checkout(period),
            )
            dialog.open()
            return

        self._do_checkout(period)

    def _do_checkout(self, period: str) -> None:
        """执行签退 — 有相机服务时先拍照，照片获取后再写签退记录。"""
        if not self._checkin_service:
            return

        if self._camera_service:
            self._camera_service.take_photo(
                period=period,
                action="out",
                on_done=lambda path: self._finish_checkout(period, path),
            )
        else:
            self._finish_checkout(period, None)

    def _finish_checkout(self, period: str, photo_path: Any) -> None:
        """拍照完成后执行实际签退写库。photo_path=None 且有相机服务 → 用户取消，不写记录。"""
        if self._camera_service and photo_path is None:
            return

        try:
            result = self._checkin_service.check_out(
                self._date_str, period,
                str(photo_path) if photo_path else None,
            )
            card = self._period_cards.get(period)
            if card:
                card.has_checked_out = True
                card.checkout_time = result.checkout_time

            def _after_checkout_anim() -> None:
                self._refresh_status()
                self._check_all_completed()
                # 推进到下一个非终态时段（跳过请假/旷工/拍摄）
                period_order = ["morning", "afternoon", "evening"]
                terminal = {"absent", "absent_morning", "absent_afternoon", "leave", "shooting"}
                current_idx = period_order.index(period) if period in period_order else -1
                for next_idx in range(current_idx + 1, len(period_order)):
                    next_period = period_order[next_idx]
                    next_card = self._period_cards.get(next_period)
                    if next_card is None:
                        continue
                    # 从当前 _periods_data 读取该时段状态判断是否终态
                    next_ps = next(
                        (p for p in self._periods_data if p.period == next_period), None
                    )
                    next_status = next_ps.status if next_ps else "pending"
                    if next_status not in terminal:
                        next_card.height = next_card._EXPANDED_HEIGHT
                        next_card.card_state = "expanded"
                        next_card.is_current = True
                        break

            if card:
                panel = CheckinSuccessPanel(
                    target_card=card,
                    is_checkin=False,
                    is_night=period in ("evening", "night"),
                    settings_service=self._settings_service,
                    on_dismiss_callback=_after_checkout_anim,
                )
                panel.open()
            else:
                _after_checkout_anim()
        except Exception as e:
            Logger.error(f"CheckinScreen: {e}")

    def _after_checkin_animation(self, period: str) -> None:
        """打卡动画完成后的处理。"""
        self._refresh_status()
        # 任意时段首次签到后弹出承诺弹窗（上午旷工时下午签到也会触发）
        self._show_promise_dialog()

    def _refresh_status(self) -> None:
        """刷新状态显示 — 拉取最新 day_status 并同步更新 StatusBox 与所有 PeriodCard。"""
        if not self._checkin_service:
            return
        try:
            self._checkin_service.mark_absent(self._date_str)
            day_status = self._checkin_service.get_today_status(self._date_str)
            self._day_status = day_status
            self._periods_data = getattr(day_status, "periods", [])
            self._status_box.update_status(day_status)
            # 同步刷新所有 PeriodCard，确保签到/签退后卡片状态正确 (B10+B11)
            from app.utils.clock import get_clock
            current_time = get_clock().current_time_str()
            start_times = {
                "morning": (
                    self._settings_service.get("morning_start")
                    if self._settings_service else "09:00"
                ),
                "afternoon": (
                    self._settings_service.get("afternoon_start")
                    if self._settings_service else "14:00"
                ),
            }
            end_times = {
                "morning": (
                    self._settings_service.get("morning_end")
                    if self._settings_service else "12:00"
                ),
                "afternoon": (
                    self._settings_service.get("afternoon_end")
                    if self._settings_service else "18:00"
                ),
            }
            for ps in self._periods_data:
                card = self._period_cards.get(ps.period)
                if card:
                    card.set_status_from_period(ps)
                    # 同步用户设置的时段起止时间
                    st = start_times.get(ps.period, "")
                    et = end_times.get(ps.period, "")
                    if st or et:
                        card.set_time_range(st, et)
                    # 请假允许条件：pending + morning/afternoon + 当前时间早于签到时间
                    card.leave_enabled = (
                        ps.status == "pending"
                        and ps.period in ("morning", "afternoon")
                        and bool(st)
                        and current_time < st
                    )
            # 重新确定当前时段（终态不阻塞后续）
            self._determine_current_period()
        except Exception as e:
            Logger.error(f"CheckinScreen: {e}")

    def _check_all_completed(self) -> None:
        """决定战报按钮可见性。

        显示战报有两种条件：
        1) 上午 + 下午都已完成（签退 / 请假 / 旷工 / 拍摄）
        2) 已过用户设置的下午下班时间（默认 18:00），无论时段状态如何
        """
        if not self._checkin_service:
            return
        try:
            day_status = self._checkin_service.get_today_status(self._date_str)
            periods = getattr(day_status, "periods", [])

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

            # 条件 2：超过下午下班时间也强制开放战报
            past_workend = False
            if self._settings_service is not None:
                try:
                    from app.utils.clock import get_clock
                    pm_end = self._settings_service.get("afternoon_end") or "18:00"
                    now_str = get_clock().current_time_str()
                    if now_str[:5] >= pm_end[:5]:
                        past_workend = True
                except Exception:
                    pass

            if (morning_ok and afternoon_ok) or past_workend:
                self._report_btn.opacity = 1.0
                self._report_btn.disabled = False
            else:
                self._report_btn.opacity = 0
                self._report_btn.disabled = True
        except Exception as e:
            Logger.error(f"CheckinScreen: {e}")

    # ── 请假 ────────────────────────────────────────────────

    def _on_leave(self, period: str) -> None:
        """请假按钮回调 — 先向 service 验证该时段是否仍可请假。"""
        if not self._checkin_service:
            return

        from app.utils.clock import get_clock

        clock = get_clock()
        current_time = clock.current_time_str()

        try:
            options = self._checkin_service.get_leave_options(self._date_str, current_time)
            if not options:
                return

            # period → leave scope 映射
            scope_map = {"morning": "morning", "afternoon": "afternoon"}
            scope = scope_map.get(period)

            # 优先用当前时段对应的 scope
            if scope and scope in options:
                self._apply_leave(scope)
            elif len(options) == 1:
                self._apply_leave(options[0])
            else:
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
            # 上午请假也弹出承诺输入框
            if scope in ("morning", "all_day"):
                self._show_promise_dialog()
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
        """承诺区显示 — 从无到有撑开高度。"""
        # 剥离用户数据中可能出现的 "兜兜" 昵称前缀
        cleaned = reward_desc.replace("兜兜", "").lstrip("：:、, ").strip()
        self._promise_area.height = 110
        self._promise_area.opacity = 1.0
        self._promise_desc.text = f"如果今天工作满8小时，奖励：{cleaned} ×{reward_qty}"

    # ── 任务 ────────────────────────────────────────────────

    def _on_task_check(self, task_id: int, checked: bool) -> None:
        """任务勾选回调。"""
        pass  # 由 BetService 处理

    def _on_task_add(self) -> None:
        """添加任务回调 — 弹出 AddTaskDialog。"""
        from app.ui.components.add_task_dialog import AddTaskDialog
        dialog = AddTaskDialog(on_add=self._handle_task_add)
        dialog.open()

    def _handle_task_add(self, desc: str, qty: int) -> None:
        """添加任务确认回调 — 调 bet_service 创建任务 + 刷新列表。"""
        if not self._bet_service:
            Logger.warning("CheckinScreen: bet_service 未注入, 任务仅本地显示")
            return
        try:
            from datetime import datetime, timedelta
            dt = datetime.strptime(self._date_str, "%Y-%m-%d")
            week_start = (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")
            self._bet_service.create_task(week_start, desc, qty)
            # 刷新 UI 列表 — 从 service 重新拉取保证一致性
            tasks = self._bet_service.get_week_tasks(week_start)
            self._task_list.set_tasks([
                {"id": t.id, "desc": t.task_desc, "done": bool(t.is_completed)}
                for t in tasks
            ])
        except Exception as e:
            Logger.error(f"CheckinScreen: 添加任务失败 {e}")

    def _on_task_edit(self, task_id: int) -> None:
        """编辑任务 — 弹出预填 AddTaskDialog。"""
        if not self._bet_service:
            return
        try:
            from datetime import datetime, timedelta
            dt = datetime.strptime(self._date_str, "%Y-%m-%d")
            week_start = (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")
            tasks = self._bet_service.get_week_tasks(week_start)
            target = next((t for t in tasks if t.id == task_id), None)
            if not target:
                return

            from app.ui.components.add_task_dialog import AddTaskDialog

            def _save(new_desc: str, new_qty: int) -> None:
                self._bet_service.update_task(task_id, new_desc, new_qty)
                self._reload_tasks()

            dialog = AddTaskDialog(
                on_add=_save,
                initial_desc=target.task_desc,
                initial_qty=target.target_qty,
                title_text="编辑任务",
                confirm_text="保存",
            )
            dialog.open()
        except Exception as e:
            Logger.error(f"CheckinScreen: 编辑任务失败 {e}")

    def _on_task_delete(self, task_id: int) -> None:
        """删除任务并刷新列表。"""
        if not self._bet_service:
            return
        try:
            self._bet_service.delete_task(task_id)
            self._reload_tasks()
        except Exception as e:
            Logger.error(f"CheckinScreen: 删除任务失败 {e}")

    def _reload_tasks(self) -> None:
        """从 bet_service 重新拉取本周任务并刷新 UI。"""
        if not self._bet_service or not self._date_str:
            return
        try:
            from datetime import datetime, timedelta
            dt = datetime.strptime(self._date_str, "%Y-%m-%d")
            week_start = (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")
            tasks = self._bet_service.get_week_tasks(week_start)
            self._task_list.set_tasks([
                {"id": t.id, "desc": t.task_desc, "done": bool(t.is_completed)}
                for t in tasks
            ])
        except Exception as e:
            Logger.error(f"CheckinScreen: 刷新任务列表失败 {e}")

    # ── 战报 ────────────────────────────────────────────────

    def _on_report(self) -> None:
        """战报按钮回调 — 生成战报 + 弹出 ReportPreview。"""
        if not self._report_service:
            Logger.warning("CheckinScreen: report_service 未注入, 无法弹出战报")
            return

        try:
            data = self._report_service.collect_data(self._date_str)
        except Exception as e:
            Logger.error(f"CheckinScreen: 生成战报失败 {e}")
            return

        from app.ui.components.report_preview import ReportPreview
        preview = ReportPreview(
            image_path="",
            date_str=self._date_str,
            report_data=data,
            on_save=lambda: Logger.info("ReportPreview: 保存至相册 (Android 端实现)"),
            on_settle=lambda: Logger.info("ReportPreview: 退出并结算"),
        )
        preview.open()

