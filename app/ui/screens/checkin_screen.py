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

import os
from typing import Any

from kivy.clock import Clock
from kivy.logger import Logger
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from app.ui.components.checkin_success_panel import CheckinSuccessPanel
from app.ui.components.icon_label import IconLabel
from app.ui.components.period_card import PeriodCard
from app.ui.components.pixel_button import PixelButton
from app.ui.components.promise_input import PromiseInput
from app.ui.components.rest_day_card import RestDayCard
from app.ui.components.shooting_day_card import ShootingDayCard
from app.ui.components.status_box import StatusBox
from app.ui.components.task_inline_list import TaskInlineList
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
        # 追踪当前活动的 CheckinSuccessPanel, refresh() 时强制清理
        # (真机相机后台返回后面板偶发不自动 dismiss, 卡住盖住按钮; 见 root_scatter 跨 tab 存活)
        self._active_success_panel: Any = None

        # 主容器
        self._container = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            spacing=GRID_UNIT,
            padding=[CARD_PADDING, CARD_PADDING, CARD_PADDING, CARD_PADDING + GRASS_INSET],
        )
        self._container.bind(minimum_height=self._container.setter("height"))
        self.add_widget(self._container)

        # 1. 日期头部 — 整行居中
        self._date_header = IconLabel(
            icon=None, text="",
            font_size=int(FONT_SIZE_TITLE * 1.4),
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=40,
            centered=True,
        )
        self._container.add_widget(self._date_header)

        # 2. 连续出勤天数 — 亮粉色 + 白色描边, 整行居中
        self._streak_label = IconLabel(
            icon=None, text="",
            font_size=int(FONT_SIZE_TITLE * 1.2),
            color=self._to_rgba(DOPAMINE_COLORS["coral"]["light"]),
            outline_color=self._to_rgba("#FFFFFF"),
            outline_width=2,
            size_hint=(1, None),
            height=0,  # 修复: 空数据时不占高度, 数据到位时手动设 height=32
            centered=True,
        )
        self._container.add_widget(self._streak_label)

        # 2.4 休息日卡片 — 对赌周期结算后手动指定的休息期内, 替代一切正常
        #     UI(时段卡/拍摄入口/状态框), 只显示"今日休息" + 小兔动画。
        #     优先级高于拍摄日: 休息期内不显示拍摄入口。初始隐藏，由
        #     _apply_rest_ui() 按当天是否在休息期切换。
        self._rest_card = RestDayCard(
            size_hint=(1, None),
            height=0,
            opacity=0,
        )
        self._container.add_widget(self._rest_card)

        # 2.5 拍摄日卡片 — 非拍摄日上午上班前显示"设为拍摄日"入口；
        #     拍摄日则替代三时段卡显示"完成拍摄/查看战报"。初始隐藏，
        #     由 _apply_shooting_ui() 按当天状态切换。
        self._shooting_card = ShootingDayCard(
            on_set=self._on_set_shooting_day,
            on_complete=self._on_complete_shooting,
            on_cancel=self._on_cancel_shooting_day,
            on_capture=self._on_capture_scene,
            settings_service=settings_service,
            size_hint=(1, None),
            height=0,
            opacity=0,
            disabled=True,
        )
        self._container.add_widget(self._shooting_card)

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
        self._promise_title = IconLabel(
            icon="icon_target", text="今日目标",
            font_size=FONT_SIZE_TITLE,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=36,
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

    def refresh(self) -> None:
        """外部调用 — 切换 Tab 回打卡页时刷新数据。"""
        # 先清理可能卡住的成功动画面板(真机相机后台→前台后偶发 _auto_dismiss
        # 不触发, 面板残留盖住卡片按钮 → 看着像"签到没翻成签退"或"卡在小兔"。
        # 面板挂在 root_scatter 上跨 tab 存活, 必须在此强制解挂)。
        if self._active_success_panel is not None:
            try:
                self._active_success_panel._dismissed = False
                self._active_success_panel._auto_dismiss(0)
            except Exception:
                pass
            self._active_success_panel = None
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
            self._date_header.set_status("icon_calendar", f"{chinese_date} {weekday_name}")
        except ValueError:
            self._date_header.set_status("icon_calendar", self._date_str)

        # 连续出勤天数
        if self._motivation_service:
            try:
                streak = self._motivation_service.get_current_streak()
                self._streak_label.set_segments([
                    ("icon_flame", ""),
                    (None, f"已连续正常出勤 {streak} 天"),
                    ("icon_flame", ""),
                ])
                self._streak_label.height = 32
            except Exception as e:
                Logger.error(f"CheckinScreen: 获取连续出勤失败: {e}")
                self._streak_label.set_segments([])
                self._streak_label.height = 0

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

                # 休息日优先: 休息期内不切换拍摄日 UI(不显示拍摄入口)
                if not self._apply_rest_ui():
                    self._apply_shooting_ui()
                Clock.schedule_once(
                    lambda dt: self._check_yesterday_reflection_reminder(), 1.5
                )
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

        拍摄日整套时段卡都被 _apply_shooting_ui() 隐藏，这里不应展开任何卡片
        （即便 checkin 记录的 status 因为某些原因还没跟上 shooting_service，
        也不能让本方法把已隐藏的卡片重新撑开挡住 ShootingDayCard 的按钮）。
        休息日同理（优先级更高，见 _apply_rest_ui()）。
        """
        if self._settings_service and self._settings_service.is_rest_day(self._date_str):
            return
        if self._shooting_service and self._shooting_service.is_shooting_day(self._date_str):
            return
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
        except Exception as e:
            Logger.error(f"CheckinScreen: {e}")
            return

        card = self._period_cards.get(period)
        if card:
            card.has_checked_in = True
            card.checkin_time = result.checkin_time
        self._morning_checked_in = True

        # ── 功能性推进: 同步执行, 绝不依赖 Clock ──
        # 真机相机 Intent 返回前台后, 事件循环只在"恢复瞬间画的那几帧"里
        # 推进 Clock, 此后靠触摸输入驱动。旧代码把"刷新卡片 + 弹男友奖励框"
        # 全挂在面板 dismiss 回调(4.5s)和 6s 兜底定时器上 —— 都是远超那几帧
        # 的长延迟 Clock 回调, 等不到就不执行 → 卡片不翻面、承诺框不弹, 必须
        # 切 tab 触发 on_enter→refresh 才恢复。改为在相机 on_done 回调链里
        # 同步执行: 刷新是同步属性变更(恢复帧即渲染), 弹窗是同步 open(0.1s
        # 淡入能在恢复那几帧内完成)。成功动画退化为可有可无的装饰叠加。
        self._refresh_status()
        self._check_all_completed()
        # 装饰性成功动画(真机 Clock 空转时退化为静态帧, 切 tab 由 refresh 清理)
        self._show_success_panel(card, is_checkin=True, is_night=period in ("evening", "night"))
        # 男友承诺输入(功能性, 首次签到后引导设置今日奖励)
        self._show_promise_dialog()

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
        except Exception as e:
            Logger.error(f"CheckinScreen: {e}")
            return

        card = self._period_cards.get(period)
        if card:
            card.has_checked_out = True
            card.checkout_time = result.checkout_time

        # 同步推进(同 _finish_checkin 的相机 Clock 空转规避)。_refresh_status
        # 里的 _determine_current_period 会自动展开下一个非终态时段, 无需
        # 再手动找下一张卡。
        self._refresh_status()
        self._check_all_completed()
        # 装饰性签退动画(签退后卡片折叠成完成态, 面板多半不可见, 纯兜底)
        self._show_success_panel(card, is_checkin=False, is_night=period in ("evening", "night"))

    def _show_success_panel(self, card: Any, *, is_checkin: bool, is_night: bool) -> None:
        """展示打卡/签退成功动画(纯装饰)。

        真机相机 Intent 返回后 Clock 可能空转 → 面板退化为静态帧且不自动
        关闭; 因此所有功能性推进(刷新/承诺弹窗)都不放这里, 面板 dismiss
        仅清理自身引用, refresh()/切 tab 会兜底解挂残留面板。
        """
        if card is None:
            return
        try:
            panel = CheckinSuccessPanel(
                target_card=card,
                is_checkin=is_checkin,
                is_night=is_night,
                settings_service=self._settings_service,
                on_dismiss_callback=lambda: setattr(self, "_active_success_panel", None),
            )
            panel.open()
            self._active_success_panel = panel
        except Exception as e:
            Logger.error(f"CheckinScreen: 成功动画显示失败 {e!r}")
            self._active_success_panel = None

    def _refresh_status(self) -> None:
        """刷新状态显示 — 拉取最新 day_status 并同步更新 StatusBox 与所有 PeriodCard。"""
        if not self._checkin_service:
            return
        try:
            from app.utils.clock import get_clock
            from datetime import datetime
            self._date_str = get_clock().today_str()  # 同步时钟日期
            # 同步日期头文案
            try:
                dt = datetime.strptime(self._date_str, "%Y-%m-%d")
                weekday = dt.isoweekday() - 1
                weekday_name = WEEKDAY_NAMES[weekday]
                chinese_date = self._format_chinese_date(self._date_str)
                self._date_header.set_status("icon_calendar", f"{chinese_date} {weekday_name}")
            except ValueError:
                self._date_header.set_status("icon_calendar", self._date_str)
            self._checkin_service.mark_absent(self._date_str)
            day_status = self._checkin_service.get_today_status(self._date_str)
            self._day_status = day_status
            self._periods_data = getattr(day_status, "periods", [])
            self._status_box.update_status(day_status)
            # 同步刷新所有 PeriodCard，确保签到/签退后卡片状态正确 (B10+B11)
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
            # 休息日优先: 休息期内不切换拍摄日 UI(不显示拍摄入口)
            if not self._apply_rest_ui():
                # 拍摄日 UI 切换(拍摄日卡片 ⇄ 正常时段卡)
                self._apply_shooting_ui()
        except Exception as e:
            Logger.error(f"CheckinScreen: {e}")

    def _is_rest_or_shooting_day(self) -> bool:
        """今天是否休息日或拍摄日 —— 这两种日子的战报按钮可见性由
        _apply_rest_ui / _apply_shooting_ui 独占决定, _check_all_completed
        不能插手(否则拍摄日 shooting 状态会被判为"已完成"→在拍摄卡下方
        重复冒出底部大战报按钮, 与卡片形成重复)。"""
        try:
            if self._settings_service and self._settings_service.is_rest_day(self._date_str):
                return True
            if self._shooting_service and self._shooting_service.is_shooting_day(self._date_str):
                return True
        except Exception:
            pass
        return False

    def _check_all_completed(self) -> None:
        """决定战报按钮可见性。

        显示战报有两种条件：
        1) 上午 + 下午都已完成（签退 / 请假 / 旷工 / 拍摄）
        2) 已过用户设置的下午下班时间（默认 18:00），无论时段状态如何
        """
        if not self._checkin_service:
            return
        # 休息日/拍摄日的战报按钮由各自 UI 切换独占, 这里直接跳过避免重复。
        if self._is_rest_or_shooting_day():
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

    # ── 拍摄日 ──────────────────────────────────────────────

    def _is_before_morning_start(self) -> bool:
        """当前是否早于上午上班时间(拍摄日可设置/可取消的窗口)。"""
        from app.utils.clock import get_clock
        now = get_clock().current_time_str()
        start = "09:00"
        if self._settings_service:
            start = self._settings_service.get("morning_start") or "09:00"
        return now < start

    def _apply_rest_ui(self) -> bool:
        """按当天是否处于休息期切换整套 UI。

        返回 True 表示今天是休息日 —— 调用方(_load_data/_refresh_status)
        应跳过后续的拍摄日/正常时段 UI 切换, 休息优先级最高。
        """
        is_resting = bool(
            self._settings_service and self._settings_service.is_rest_day(self._date_str)
        )
        self._set_rest_card_visible(is_resting)
        if is_resting:
            self._set_normal_day_visible(False)
            self._set_shooting_card_visible(False)
        return is_resting

    def _set_rest_card_visible(self, show: bool) -> None:
        self._rest_card.opacity = 1.0 if show else 0.0
        self._rest_card.height = self._rest_card.natural_height if show else 0
        # 非休息日隐藏卡片时同步关停精灵动画, 避免小兔空转 Clock 帧循环
        # (SequenceSprite autoplay 永不自动停止, 隐藏后仍在后台逐帧推进,
        # 真机上与其它动画叠加导致切 tab 回来卡顿)。
        self._rest_card.set_animation_active(show)

    def _apply_shooting_ui(self) -> None:
        """按当天拍摄日状态切换整套 UI(拍摄日卡片 ⇄ 正常时段卡)。"""
        if not self._shooting_service:
            self._set_shooting_card_visible(False)
            return
        try:
            is_shooting = self._shooting_service.is_shooting_day(self._date_str)
            before_morning = self._is_before_morning_start()
            if is_shooting:
                reflection = self._shooting_service.get_reflection(self._date_str)
                is_done = reflection is not None
                self._shooting_card.set_state(
                    "done" if is_done else "active",
                    can_cancel=before_morning,
                )
                self._set_shooting_card_visible(True)
                self._set_normal_day_visible(False)
                # 复盘完成后, 战报统一走页面底部大按钮(卡片内不再重复放"查看
                # 战报"); 复盘完成前无战报可看, 保持隐藏。
                self._report_btn.opacity = 1.0 if is_done else 0.0
                self._report_btn.disabled = not is_done
            else:
                self._set_normal_day_visible(True)
                if before_morning:
                    self._shooting_card.set_state("idle")
                    self._set_shooting_card_visible(True)
                else:
                    self._set_shooting_card_visible(False)
        except Exception as e:
            Logger.error(f"CheckinScreen: 拍摄日 UI 刷新失败 {e}")

    def _set_shooting_card_visible(self, show: bool) -> None:
        self._shooting_card.opacity = 1.0 if show else 0.0
        self._shooting_card.disabled = not show
        self._shooting_card.height = self._shooting_card.natural_height if show else 0

    def _set_normal_day_visible(self, visible: bool) -> None:
        """拍摄日时收起正常时段 UI(时段卡 + 状态框 + 承诺区 + 战报按钮)。"""
        op = 1.0 if visible else 0.0
        for card in self._period_cards.values():
            card.opacity = op
            card.disabled = not visible
            if not visible:
                card.card_state = "collapsed"
                card.height = 0
        self._status_box.opacity = op
        if visible:
            self._status_box.height = 130
        else:
            self._status_box.height = 0
            self._promise_area.opacity = 0
            self._promise_area.height = 0
            self._report_btn.opacity = 0
            self._report_btn.disabled = True

    def _on_set_shooting_day(self) -> None:
        """点击"设为拍摄日" — 一次性定死整天。"""
        if not self._checkin_service:
            return
        try:
            self._checkin_service.set_shooting_day(self._date_str)
            self._refresh_status()
        except Exception as e:
            Logger.error(f"CheckinScreen: 设置拍摄日失败 {e}")

    def _on_cancel_shooting_day(self) -> None:
        """点击"取消"拍摄日(仅上午上班前窗口内有效)。"""
        if not self._checkin_service:
            return
        try:
            ok = self._checkin_service.cancel_shooting_day(self._date_str)
            if not ok:
                from app.ui.components.toast import show_toast
                show_toast("已过上午上班时间，无法取消拍摄日")
            self._refresh_status()
        except Exception as e:
            Logger.error(f"CheckinScreen: 取消拍摄日失败 {e}")

    def _on_complete_shooting(self) -> None:
        """点击"完成拍摄" — 弹复盘弹窗。"""
        from app.ui.components.shooting_reflection_dialog import ShootingReflectionDialog
        dialog = ShootingReflectionDialog(on_submit=self._on_reflection_submit)
        dialog.open()

    def _on_reflection_submit(self, answers: dict[str, str]) -> None:
        """复盘提交回调 — 写库计奖励 + 刷新。"""
        if self._shooting_service:
            try:
                self._shooting_service.submit_reflection(self._date_str, answers)
                from app.ui.components.toast import show_reward_celebration
                show_reward_celebration("拍摄复盘已记录，奖励已入账")
            except Exception as e:
                Logger.error(f"CheckinScreen: 提交复盘失败 {e}")
        self._refresh_status()

    def _on_capture_scene(self) -> None:
        """拍摄日「拍张现场」— 可选留念, 不考勤、不影响奖励, 拍完存 shooting_scene 供战报读取。"""
        if not self._camera_service:
            return
        try:
            self._camera_service.take_photo(
                period="shooting",
                action="scene",
                on_done=self._on_scene_captured,
            )
        except Exception as e:
            Logger.error(f"CheckinScreen: 拍摄现场失败 {e}")

    def _on_scene_captured(self, path: Any) -> None:
        """现场照拍完回调 — 有照片则轻提示(战报会自动读取该照片)。"""
        if path:
            from app.ui.components.toast import show_toast
            show_toast("现场照已记录，会出现在战报里~")

    def _check_yesterday_reflection_reminder(self) -> None:
        """次日温和提醒 — 昨天是拍摄日但没写复盘。"""
        if not self._shooting_service or not self._date_str:
            return
        try:
            from datetime import datetime, timedelta
            today = datetime.strptime(self._date_str, "%Y-%m-%d")
            yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
            if (self._shooting_service.is_shooting_day(yesterday)
                    and self._shooting_service.get_reflection(yesterday) is None):
                from app.ui.components.toast import show_toast
                show_toast("昨天的拍摄还没写复盘哦~", duration=3.0)
        except Exception as e:
            Logger.error(f"CheckinScreen: 复盘提醒检查失败 {e}")

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
        # 直接 open, 不用 Clock 延迟: 相机返回后 Clock 空转会吞掉延迟回调,
        # 导致男友奖励框不弹(真机复现的回归)。ModalView 0.1s 淡入能在
        # 恢复那几帧内自行完成。
        dialog.open()

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
        nickname = ""
        if self._settings_service:
            nickname = self._settings_service.get_user_nickname()
        cleaned = reward_desc.replace("兜兜", nickname).lstrip("：:、, ").strip()
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

        def _save_report() -> None:
            """导出战报为所见即所得长图 PNG。

            布局: 吸取景观图第一行像素色填充顶部 | 景观图保持比例底部贴合 |
            内容区居中 | 草地锯齿前景最顶层底边。
            """
            import traceback
            date_str = preview._date_str if hasattr(preview, '_date_str') else data.date
            try:
                content = preview._content_box
                scroll = content.parent

                content_h = int(content.minimum_height)
                pad_t = content.padding[1]
                pad_b = content.padding[3]

                from kivy.uix.floatlayout import FloatLayout
                from kivy.uix.image import Image as KivyImage
                from kivy.graphics import Color, Rectangle
                from app.ui.assets.landscape import BG_LANDSCAPE, get_grass_overlay_path
                from app.ui.assets.loader import apply_pixel_filter

                img_w = 390

                # ── 天空色: 从景观图顶部吸取 ──
                from PIL import Image as PILImage
                pil_bg = PILImage.open(BG_LANDSCAPE)
                bg_w, bg_h = pil_bg.size  # 600×1080
                top_pixel = pil_bg.getpixel((bg_w // 2, 0))
                if len(top_pixel) == 4:
                    sky_rgba = (top_pixel[0]/255, top_pixel[1]/255, top_pixel[2]/255, 1.0)
                else:
                    sky_rgba = (top_pixel[0]/255, top_pixel[1]/255, top_pixel[2]/255, 1.0)

                # 两个图层等比缩放到 390 宽: 高度 = 390 * 1080/600 = 702
                layer_h = int(img_w * bg_h / bg_w)
                # 草地前景底部约 15% 是草地+土地(非透明)
                grass_bottom_h = int(layer_h * 0.15)

                # 总高度: 内容全高 + 草地区(去掉 content 内部的顶部 padding)
                orig_padding = list(content.padding)
                content.padding = [orig_padding[0], 4, orig_padding[2], orig_padding[3]]  # 压扁顶部留白
                content_h = int(content.minimum_height)  # 重新取
                total_h = grass_bottom_h + content_h + 4

                # 1. 拆 content_box
                if scroll:
                    scroll.remove_widget(content)

                # 2. 构建导出画布
                export_root = FloatLayout(size=(img_w, total_h))
                # 天空色铺满全背景
                with export_root.canvas.before:
                    Color(*sky_rgba)
                    Rectangle(size=(img_w, total_h))

                # 天空背景层(底部对齐,保持比例)
                sky_bg = KivyImage(
                    source=BG_LANDSCAPE,
                    size_hint=(None, None),
                    size=(img_w, layer_h),
                    pos=(0, 0),
                    allow_stretch=True,
                    keep_ratio=False,
                )
                apply_pixel_filter(sky_bg.texture)
                export_root.add_widget(sky_bg)

                # 内容层(叠在草地上方)
                content_y = grass_bottom_h - 15
                content.size = (img_w, content_h)
                content.pos = (0, content_y)
                content.size_hint = (None, None)
                export_root.add_widget(content)

                # 草地前景层(最顶层,底部贴合,保持比例)
                grass_fg = KivyImage(
                    source=get_grass_overlay_path(),
                    size_hint=(None, None),
                    size=(img_w, layer_h),
                    pos=(0, 0),
                    allow_stretch=True,
                    keep_ratio=False,
                )
                apply_pixel_filter(grass_fg.texture)
                export_root.add_widget(grass_fg)

                # 3. 导出
                from kivy.clock import Clock
                def _do_export(_dt):
                    try:
                        from app.utils.storage import get_pictures_dir, scan_media
                        save_dir = get_pictures_dir()
                        filepath = str(save_dir / f"战报_{date_str}.png")
                        export_root.export_to_png(filepath)
                        scan_media(save_dir / f"战报_{date_str}.png")
                        print(f"[战报] 长图已保存: {filepath}")
                    except Exception as e2:
                        Logger.error(f"[战报] 导出失败: {e2}")
                        traceback.print_exc()
                    finally:
                        export_root.remove_widget(content)
                        content.padding = orig_padding  # 恢复原始 padding
                        content.size_hint = (1, None)
                        if scroll:
                            scroll.add_widget(content)
                Clock.schedule_once(_do_export, 0.1)

            except Exception as e:
                Logger.error(f"ReportPreview: 保存长图失败 {e}")
                traceback.print_exc()

        preview = ReportPreview(
            image_path="",
            date_str=self._date_str,
            report_data=data,
            on_save=_save_report,
            on_settle=lambda: Logger.info("ReportPreview: 退出并结算"),
            settings_service=self._settings_service,
        )
        preview.open()

