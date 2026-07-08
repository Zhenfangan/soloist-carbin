"""测试 — 打卡主界面 (UI-03)。

覆盖:
- PeriodCard: 三状态渲染、展开/折叠切换、签到按钮回调
- StatusBox: 各状态文案正确、颜色正确
- CheckinScreen: 打卡流程完整走通 (mock service)、时段切换、请假弹窗
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
from kivy.clock import Clock

from app.ui.components.period_card import PeriodCard
from app.ui.components.status_box import StatusBox
from app.ui.components.task_inline_list import TaskInlineList
from app.ui.screens.checkin_screen import CheckinScreen
from app.ui.tokens import SEMANTIC_COLORS

# ── Fixtures ──────────────────────────────────────────────


@pytest.fixture
def mock_checkin_service() -> MagicMock:
    """创建模拟 CheckinService。"""
    service = MagicMock()

    # 模拟 DayStatus
    class MockPeriodStatus:
        def __init__(self, period: str, status: str = "pending", checkin_time: str | None = None, checkout_time: str | None = None):
            self.period = period
            self.status = status
            self.checkin_time = checkin_time
            self.checkout_time = checkout_time
            self.checkout_type = "manual"

    class MockDayStatus:
        def __init__(self, date: str = "2026-06-01"):
            self.date = date
            self.is_work_day = True
            self.is_shooting_day = False
            self.periods = [
                MockPeriodStatus("morning", "pending"),
                MockPeriodStatus("afternoon", "pending"),
                MockPeriodStatus("evening", "pending"),
            ]

    service.get_today_status.return_value = MockDayStatus()

    # 模拟 CheckinResult
    class MockCheckinResult:
        def __init__(self, period: str):
            self.record_id = 1
            self.period = period
            self.date = "2026-06-01"
            self.type = "checkin"
            self.status = "normal"
            self.time = "09:00"
            self.checkin_time = "09:00"
            self.checkout_time = None
            self.message = ""

    service.check_in.return_value = MockCheckinResult("morning")

    class MockCheckoutResult:
        def __init__(self, period: str):
            self.record_id = 1
            self.period = period
            self.date = "2026-06-01"
            self.type = "checkout"
            self.status = "normal"
            self.time = "12:00"
            self.checkin_time = "09:00"
            self.checkout_time = "12:00"
            self.message = ""

    service.check_out.return_value = MockCheckoutResult("morning")
    service.get_leave_options.return_value = ["morning", "afternoon", "all_day"]
    service.apply_leave.return_value = []
    service.get_period_end_time.return_value = None
    service.mark_absent.return_value = None

    return service


@pytest.fixture
def mock_promise_service() -> MagicMock:
    """创建模拟 BoyfriendPromiseService。"""
    service = MagicMock()
    service.get_today_promise.return_value = None

    class MockPromise:
        def __init__(self) -> None:
            self.promise_date = "2026-06-01"
            self.reward_desc = "一杯奶茶"
            self.reward_qty = 1
            self.fulfilled = 0

    service.set_promise.return_value = MockPromise()
    service.calculate_total_hours.return_value = 4.0
    return service


@pytest.fixture
def mock_motivation_service() -> MagicMock:
    """创建模拟 MotivationService。"""
    service = MagicMock()
    service.get_current_streak.return_value = 12
    return service


@pytest.fixture
def mock_report_service() -> MagicMock:
    """创建模拟 ReportService。"""
    service = MagicMock()
    service.generate_and_save.return_value = "<html>mock</html>"
    return service


@pytest.fixture
def mock_shooting_service() -> MagicMock:
    """创建模拟 ShootingService。"""
    service = MagicMock()
    service.is_shooting_day.return_value = False
    return service


# ── PeriodCard Tests ─────────────────────────────────────


class TestPeriodCard:
    """测试 PeriodCard 三状态及交互。"""

    def test_initial_expanded_state(self) -> None:
        """测试展开态初始状态。"""
        card = PeriodCard(period_name="morning", is_current=True)
        card.card_state = "expanded"
        Clock.tick()
        assert card.card_state == "expanded"

    def test_collapsed_state(self) -> None:
        """测试折叠态。"""
        card = PeriodCard(period_name="morning")
        card.card_state = "collapsed"
        Clock.tick()
        assert card.card_state == "collapsed"

    def test_completed_state(self) -> None:
        """测试完成态。"""
        card = PeriodCard(period_name="morning")
        card.has_checked_in = True
        card.checkin_time = "09:00"
        card.status = "normal"
        card.card_state = "completed"
        Clock.tick()
        assert card.card_state == "completed"

    def test_expand_collapse_toggle(self) -> None:
        """测试展开/折叠切换。"""
        card = PeriodCard(period_name="morning")
        card.card_state = "collapsed"
        Clock.tick()
        assert card.card_state == "collapsed"

        card.card_state = "expanded"
        Clock.tick()
        assert card.card_state == "expanded"

        card.card_state = "collapsed"
        Clock.tick()
        assert card.card_state == "collapsed"

    def test_checkin_button_callback(self) -> None:
        """测试签到按钮回调。"""
        callback_called = []

        def on_checkin(period: str) -> None:
            callback_called.append(period)

        card = PeriodCard(
            period_name="morning",
            on_checkin=on_checkin,
            is_current=True,
        )
        card.card_state = "expanded"
        Clock.tick()

        # 模拟点击签到按钮
        card._on_action()
        assert len(callback_called) == 1
        assert callback_called[0] == "morning"

    def test_checkout_button_callback(self) -> None:
        """测试签退按钮回调。"""
        callback_called = []

        def on_checkout(period: str) -> None:
            callback_called.append(period)

        card = PeriodCard(
            period_name="morning",
            on_checkout=on_checkout,
            is_current=True,
        )
        card.card_state = "expanded"
        card.has_checked_in = True  # 已签到状态
        Clock.tick()

        # 此时按钮文案应为 "签退"
        card._on_action()
        assert len(callback_called) == 1
        assert callback_called[0] == "morning"

    def test_period_labels(self) -> None:
        """测试不同时段的标签显示。"""
        morning_card = PeriodCard(period_name="morning")
        afternoon_card = PeriodCard(period_name="afternoon")
        evening_card = PeriodCard(period_name="evening")

        assert morning_card._period_label == "上午"
        assert afternoon_card._period_label == "下午"
        assert evening_card._period_label == "晚上"

    def test_leave_button_enabled(self) -> None:
        """测试请假按钮启用/禁用。"""
        card = PeriodCard(period_name="morning", is_current=True)
        card.card_state = "expanded"
        card.leave_enabled = True
        Clock.tick()
        assert card._leave_enabled is True
        assert card._leave_btn.disabled is False

        card.leave_enabled = False
        Clock.tick()
        assert card._leave_enabled is False
        assert card._leave_btn.disabled is True


# ── StatusBox Tests ──────────────────────────────────────


class TestStatusBox:
    """测试 StatusBox 状态显示。"""

    @staticmethod
    def _make_period_status(
        period: str,
        status: str = "pending",
        checkin_time: str | None = None,
        checkout_time: str | None = None,
        is_late: bool = False,
        is_early_leave: bool = False,
    ) -> Any:
        """创建模拟 PeriodStatus。"""
        from types import SimpleNamespace
        return SimpleNamespace(
            period=period,
            status=status,
            checkin_time=checkin_time,
            checkout_time=checkout_time,
            checkout_type="manual",
            is_late=is_late,
            is_early_leave=is_early_leave,
        )

    @staticmethod
    def _make_day_status(periods: list[Any]) -> Any:
        """创建模拟 DayStatus。"""
        from types import SimpleNamespace
        return SimpleNamespace(
            date="2026-06-01",
            periods=periods,
            is_shooting_day=False,
            is_work_day=True,
            streak=12,
        )

    def test_pending_status(self) -> None:
        """测试待签到状态文案。"""
        box = StatusBox()
        day_status = self._make_day_status([
            self._make_period_status("morning", "pending"),
            self._make_period_status("afternoon", "pending"),
            self._make_period_status("evening", "pending"),
        ])
        box.update_status(day_status)

        morning_info = {"status_w": box._status_widgets["morning"]}
        assert "等待签到" in morning_info["status_w"].text

    def test_normal_status(self) -> None:
        """测试正常签到状态文案。"""
        box = StatusBox()
        day_status = self._make_day_status([
            self._make_period_status("morning", "normal", "09:00", "12:00"),
            self._make_period_status("afternoon", "pending"),
            self._make_period_status("evening", "pending"),
        ])
        box.update_status(day_status)

        morning_info = {"status_w": box._status_widgets["morning"]}
        assert "正常签到" in morning_info["status_w"].text
        assert "09:00" in morning_info["status_w"].text

    def test_late_status(self) -> None:
        """测试迟到状态。"""
        box = StatusBox()
        day_status = self._make_day_status([
            self._make_period_status("morning", "late", "09:15"),
            self._make_period_status("afternoon", "pending"),
            self._make_period_status("evening", "pending"),
        ])
        box.update_status(day_status)

        morning_info = {"status_w": box._status_widgets["morning"]}
        assert "迟到" in morning_info["status_w"].text

    def test_late_and_early_leave_status(self) -> None:
        """既迟到又早退：service 把 status 压成 late，但 is_early_leave 标志位为真，
        汇总栏应同时显示「迟到」和「早退」，不丢任何一个。"""
        box = StatusBox()
        day_status = self._make_day_status([
            self._make_period_status(
                "morning", "late", "09:15", "11:30",
                is_late=True, is_early_leave=True,
            ),
            self._make_period_status("afternoon", "pending"),
            self._make_period_status("evening", "pending"),
        ])
        box.update_status(day_status)

        text = box._status_widgets["morning"].text
        assert "迟到" in text, f"应含迟到: {text!r}"
        assert "早退" in text, f"应含早退: {text!r}"
        assert "09:15" in text and "11:30" in text

    def test_leave_status(self) -> None:
        """测试请假状态。"""
        box = StatusBox()
        day_status = self._make_day_status([
            self._make_period_status("morning", "leave"),
            self._make_period_status("afternoon", "pending"),
            self._make_period_status("evening", "pending"),
        ])
        box.update_status(day_status)

        morning_info = {"status_w": box._status_widgets["morning"]}
        assert "已请假" in morning_info["status_w"].text

    def test_absent_status(self) -> None:
        """测试旷工状态。"""
        box = StatusBox()
        day_status = self._make_day_status([
            self._make_period_status("morning", "absent"),
            self._make_period_status("afternoon", "pending"),
            self._make_period_status("evening", "pending"),
        ])
        box.update_status(day_status)

        morning_info = {"status_w": box._status_widgets["morning"]}
        assert "未签到" in morning_info["status_w"].text

    def test_shooting_status(self) -> None:
        """测试拍摄日状态。"""
        box = StatusBox()
        day_status = self._make_day_status([
            self._make_period_status("morning", "shooting"),
            self._make_period_status("afternoon", "shooting"),
            self._make_period_status("evening", "pending"),
        ])
        box.update_status(day_status)

        morning_info = {"status_w": box._status_widgets["morning"]}
        assert "拍摄" in morning_info["status_w"].text

    def test_color_mapping(self) -> None:
        """测试状态颜色映射正确。"""
        box = StatusBox()

        # 正常 → 天空蓝色
        day_status = self._make_day_status([
            self._make_period_status("morning", "normal", "09:00"),
            self._make_period_status("afternoon", "pending"),
            self._make_period_status("evening", "pending"),
        ])
        box.update_status(day_status)
        morning_info = {"status_w": box._status_widgets["morning"]}
        normal_color = SEMANTIC_COLORS["normal"]["icon"]
        expected = list(box._to_rgba(normal_color))
        assert list(morning_info["status_w"].color) == expected

    def test_working_status(self) -> None:
        """测试工作中状态（已签到未签退）。"""
        box = StatusBox()
        day_status = self._make_day_status([
            self._make_period_status("morning", "normal", "09:00"),
            self._make_period_status("afternoon", "pending"),
            self._make_period_status("evening", "pending"),
        ])
        # morning 有 checkin_time 但无 checkout_time → 工作中
        box.update_status(day_status)
        morning_info = {"status_w": box._status_widgets["morning"]}
        # 正常的 normal 状态已签到未签退显示完整信息
        assert "09:00" in morning_info["status_w"].text

    def test_absent_morning_status(self) -> None:
        """测试上午旷工状态。"""
        box = StatusBox()
        day_status = self._make_day_status([
            self._make_period_status("morning", "absent_morning"),
            self._make_period_status("afternoon", "pending"),
            self._make_period_status("evening", "pending"),
        ])
        box.update_status(day_status)
        morning_info = {"status_w": box._status_widgets["morning"]}
        assert "未签到" in morning_info["status_w"].text


# ── TaskInlineList Tests ─────────────────────────────────


class TestTaskInlineList:
    """测试任务清单组件。"""

    def test_task_list_rendering(self) -> None:
        """测试任务列表渲染。"""
        tasks = [
            {"id": 1, "desc": "任务1", "done": False},
            {"id": 2, "desc": "任务2", "done": True},
        ]
        task_list = TaskInlineList(tasks=tasks)
        task_list.set_tasks(tasks)
        assert len(task_list._tasks) == 2

    def test_checkbox_callback(self) -> None:
        """测试勾选回调。"""
        callback_args = []

        def on_check(task_id: int, checked: bool) -> None:
            callback_args.append((task_id, checked))

        tasks = [
            {"id": 1, "desc": "任务1", "done": False},
        ]
        task_list = TaskInlineList(tasks=tasks, on_check=on_check)
        task_list.set_tasks(tasks)
        assert len(task_list._checkboxes) == 1

        # 触发勾选回调
        task_list._on_check(1, True)
        assert len(callback_args) == 1
        assert callback_args[0] == (1, True)


# ── CheckinScreen Integration Tests ──────────────────────


class TestCheckinScreen:
    """测试 CheckinScreen 完整打卡流程。"""

    def test_screen_creation(self, mock_checkin_service: MagicMock,
                             mock_promise_service: MagicMock,
                             mock_motivation_service: MagicMock,
                             mock_report_service: MagicMock,
                             mock_shooting_service: MagicMock) -> None:
        """测试屏幕创建。"""
        screen = CheckinScreen(
            checkin_service=mock_checkin_service,
            promise_service=mock_promise_service,
            motivation_service=mock_motivation_service,
            report_service=mock_report_service,
            shooting_service=mock_shooting_service,
        )
        Clock.tick()
        assert screen._date_header is not None
        assert screen._streak_label is not None
        assert len(screen._period_cards) == 3
        assert screen._status_box is not None
        assert screen._task_list is not None
        assert screen._report_btn is not None

    def test_period_cards_loaded(self, mock_checkin_service: MagicMock,
                                  mock_promise_service: MagicMock,
                                  mock_motivation_service: MagicMock,
                                  mock_report_service: MagicMock,
                                  mock_shooting_service: MagicMock) -> None:
        """测试三时段卡片加载。"""
        screen = CheckinScreen(
            checkin_service=mock_checkin_service,
            promise_service=mock_promise_service,
            motivation_service=mock_motivation_service,
            report_service=mock_report_service,
            shooting_service=mock_shooting_service,
        )
        Clock.tick()
        assert "morning" in screen._period_cards
        assert "afternoon" in screen._period_cards
        assert "evening" in screen._period_cards

    def test_date_header_format(self, mock_checkin_service: MagicMock,
                                 mock_promise_service: MagicMock,
                                 mock_motivation_service: MagicMock,
                                 mock_report_service: MagicMock,
                                 mock_shooting_service: MagicMock) -> None:
        """测试日期头部格式。"""
        # 设置模拟时钟
        from app.utils.clock import SimulatedClock, set_clock
        sim_clock = SimulatedClock(start_time=datetime(2026, 6, 1, 8, 0, 0))
        set_clock(sim_clock)

        screen = CheckinScreen(
            checkin_service=mock_checkin_service,
            promise_service=mock_promise_service,
            motivation_service=mock_motivation_service,
            report_service=mock_report_service,
            shooting_service=mock_shooting_service,
        )
        Clock.tick()
        # 2026年6月1日 is a Monday (周一)
        assert "2026" in screen._date_header.text

    def test_streak_display(self, mock_checkin_service: MagicMock,
                             mock_promise_service: MagicMock,
                             mock_motivation_service: MagicMock,
                             mock_report_service: MagicMock,
                             mock_shooting_service: MagicMock) -> None:
        """测试连续出勤天数显示。"""
        screen = CheckinScreen(
            checkin_service=mock_checkin_service,
            promise_service=mock_promise_service,
            motivation_service=mock_motivation_service,
            report_service=mock_report_service,
            shooting_service=mock_shooting_service,
        )
        Clock.tick()
        assert "12" in screen._streak_label.text

    def test_morning_checkin_flow(self, mock_checkin_service: MagicMock,
                                   mock_promise_service: MagicMock,
                                   mock_motivation_service: MagicMock,
                                   mock_report_service: MagicMock,
                                   mock_shooting_service: MagicMock) -> None:
        """测试上午签到流程。"""
        screen = CheckinScreen(
            checkin_service=mock_checkin_service,
            promise_service=mock_promise_service,
            motivation_service=mock_motivation_service,
            report_service=mock_report_service,
            shooting_service=mock_shooting_service,
        )
        Clock.tick()

        # 执行上午签到
        screen._do_checkin("morning")
        Clock.tick()
        assert mock_checkin_service.check_in.called

    def test_refresh_leaves_fresh_success_panel_alone(self, mock_checkin_service: MagicMock,
                                                       mock_promise_service: MagicMock,
                                                       mock_motivation_service: MagicMock,
                                                       mock_report_service: MagicMock,
                                                       mock_shooting_service: MagicMock) -> None:
        """回归(真机): SoloistApp.on_resume() 在相机 Intent 返回后几乎与
        CheckinSuccessPanel 刚创建同一瞬间触发, 调的正是 refresh()。refresh()
        如果无条件 force-dismiss 任何 _active_success_panel, 就会把自己刚
        打开的庆祝面板秒杀 —— 签到按钮状态是对了, 但用户再也看不到动画。

        refresh() 必须只解挂"确实过期"(is_overdue()为真)的面板, 刚打开的
        面板应该被放过。"""
        screen = CheckinScreen(
            checkin_service=mock_checkin_service,
            promise_service=mock_promise_service,
            motivation_service=mock_motivation_service,
            report_service=mock_report_service,
            shooting_service=mock_shooting_service,
        )
        Clock.tick()

        fresh_panel = MagicMock()
        fresh_panel.is_overdue.return_value = False
        screen._active_success_panel = fresh_panel

        screen.refresh()

        fresh_panel._auto_dismiss.assert_not_called()
        assert screen._active_success_panel is fresh_panel

    def test_refresh_dismisses_overdue_success_panel(self, mock_checkin_service: MagicMock,
                                                      mock_promise_service: MagicMock,
                                                      mock_motivation_service: MagicMock,
                                                      mock_report_service: MagicMock,
                                                      mock_shooting_service: MagicMock) -> None:
        """回归防复发: 面板真卡住(过期未消失)时, refresh() 仍必须强制解挂 ——
        这是原始"签到后按钮卡住需切 Tab"bug 的兜底修复, 不能被上面那条
        新增的"放过刚打开面板"逻辑连带削弱。"""
        screen = CheckinScreen(
            checkin_service=mock_checkin_service,
            promise_service=mock_promise_service,
            motivation_service=mock_motivation_service,
            report_service=mock_report_service,
            shooting_service=mock_shooting_service,
        )
        Clock.tick()

        stale_panel = MagicMock()
        stale_panel.is_overdue.return_value = True
        screen._active_success_panel = stale_panel

        screen.refresh()

        stale_panel._auto_dismiss.assert_called_once()
        assert screen._active_success_panel is None

    def test_checkin_advances_flow_synchronously(self, mock_checkin_service: MagicMock,
                                                  mock_promise_service: MagicMock,
                                                  mock_motivation_service: MagicMock,
                                                  mock_report_service: MagicMock,
                                                  mock_shooting_service: MagicMock) -> None:
        """回归(真机): 相机 Intent 返回前台后事件循环靠输入驱动, Clock 长延迟
        回调(6s 兜底 / 面板 4.5s dismiss / 弹窗 0.3s)在下次触摸前不触发。故签到
        后的"刷新卡片 + 弹男友奖励框"必须在 _finish_checkin 里同步完成, 不能
        挂在 Clock 回调上 —— 否则卡片不翻面、承诺框不弹, 必须切 tab 才恢复。

        断言: 不推进 Clock, _finish_checkin 返回时承诺弹窗已触发、状态已重刷。"""
        screen = CheckinScreen(
            checkin_service=mock_checkin_service,
            promise_service=mock_promise_service,
            motivation_service=mock_motivation_service,
            report_service=mock_report_service,
            shooting_service=mock_shooting_service,
        )
        Clock.tick()
        assert screen._promise_shown is False, "尚未签到, 承诺弹窗不应已触发"
        calls_before = mock_checkin_service.get_today_status.call_count

        # 模拟相机 on_done 回调直接落到 _finish_checkin; 关键: 全程不推进 Clock
        screen._finish_checkin("morning", None)

        assert screen._promise_shown is True, "签到后男友奖励弹窗未同步弹出(仍依赖 Clock)"
        assert mock_checkin_service.get_today_status.call_count > calls_before, (
            "签到后未同步重刷状态(卡片不会翻面, 仍依赖 Clock)"
        )

    def test_checkout_flow(self, mock_checkin_service: MagicMock,
                            mock_promise_service: MagicMock,
                            mock_motivation_service: MagicMock,
                            mock_report_service: MagicMock,
                            mock_shooting_service: MagicMock) -> None:
        """测试签退流程。"""
        screen = CheckinScreen(
            checkin_service=mock_checkin_service,
            promise_service=mock_promise_service,
            motivation_service=mock_motivation_service,
            report_service=mock_report_service,
            shooting_service=mock_shooting_service,
        )
        Clock.tick()

        # 签退
        screen._on_checkout("morning")
        Clock.tick()
        assert mock_checkin_service.check_out.called

    def test_leave_dialog(self, mock_checkin_service: MagicMock,
                           mock_promise_service: MagicMock,
                           mock_motivation_service: MagicMock,
                           mock_report_service: MagicMock,
                           mock_shooting_service: MagicMock) -> None:
        """测试请假流程。"""
        from app.utils.clock import SimulatedClock, set_clock
        sim_clock = SimulatedClock(start_time=datetime(2026, 6, 1, 8, 0, 0))
        set_clock(sim_clock)

        screen = CheckinScreen(
            checkin_service=mock_checkin_service,
            promise_service=mock_promise_service,
            motivation_service=mock_motivation_service,
            report_service=mock_report_service,
            shooting_service=mock_shooting_service,
        )
        Clock.tick()

        screen._on_leave("morning")
        Clock.tick()
        assert mock_checkin_service.apply_leave.called
        mock_checkin_service.apply_leave.assert_called_with("2026-06-01", "morning")

    def test_report_button_appears(self, mock_checkin_service: MagicMock,
                                    mock_promise_service: MagicMock,
                                    mock_motivation_service: MagicMock,
                                    mock_report_service: MagicMock,
                                    mock_shooting_service: MagicMock) -> None:
        """测试战报按钮显示。"""
        # 模拟所有时段都完成
        class MockPeriodStatus:
            def __init__(self, period: str, status: str = "normal",
                         checkin_time: str | None = "09:00",
                         checkout_time: str | None = "18:00") -> None:
                self.period = period
                self.status = status
                self.checkin_time = checkin_time
                self.checkout_time = checkout_time
                self.checkout_type = "manual"

        class MockDayStatus:
            def __init__(self) -> None:
                self.date = "2026-06-01"
                self.is_work_day = True
                self.is_shooting_day = False
                self.periods = [
                    MockPeriodStatus("morning", "normal", "09:00", "12:00"),
                    MockPeriodStatus("afternoon", "normal", "14:00", "18:00"),
                    MockPeriodStatus("evening", "pending"),
                ]

        mock_checkin_service.get_today_status.return_value = MockDayStatus()

        screen = CheckinScreen(
            checkin_service=mock_checkin_service,
            promise_service=mock_promise_service,
            motivation_service=mock_motivation_service,
            report_service=mock_report_service,
            shooting_service=mock_shooting_service,
        )
        Clock.tick()

        screen._check_all_completed()
        # 战报按钮应该可见且可用
        assert screen._report_btn.opacity == 1.0
        assert not screen._report_btn.disabled
