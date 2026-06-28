"""测试 CheckinScreen 签到/签退后刷新 PeriodCard 状态 (B10+B11)。

共同根因：_refresh_status() 只更新了 StatusBox 而没有更新 PeriodCard。
修复后，_refresh_status() 会对每个 PeriodCard 调用 set_status_from_period()。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from kivy.clock import Clock

from app.ui.screens.checkin_screen import CheckinScreen


def _make_period_status(
    period: str,
    status: str = "pending",
    checkin_time: str | None = None,
    checkout_time: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        period=period,
        status=status,
        checkin_time=checkin_time,
        checkout_time=checkout_time,
        checkout_type="manual",
    )


def _make_day_status(periods: list) -> SimpleNamespace:
    return SimpleNamespace(
        date="2026-06-07",
        periods=periods,
        is_shooting_day=False,
        is_work_day=True,
    )


class TestCheckinScreenRefresh:
    """测试 checkin/checkout 后 _refresh_status 正确刷新所有 PeriodCard。"""

    @pytest.fixture
    def services(self) -> tuple:
        """创建全部 mock 服务。"""
        checkin_svc = MagicMock()
        promise_svc = MagicMock()
        motivation_svc = MagicMock()
        report_svc = MagicMock()
        shooting_svc = MagicMock()

        # 默认返回值
        promise_svc.get_today_promise.return_value = None
        motivation_svc.get_current_streak.return_value = 5
        report_svc.generate_and_save.return_value = "<html/>"

        # get_today_status 初始返回全部 pending
        checkin_svc.get_today_status.return_value = _make_day_status([
            _make_period_status("morning", "pending"),
            _make_period_status("afternoon", "pending"),
            _make_period_status("evening", "pending"),
        ])

        # checkin / checkout 返回值
        checkin_svc.check_in.return_value = SimpleNamespace(
            record_id=1, period="morning", checkin_time="09:00", checkout_time=None,
        )
        checkin_svc.check_out.return_value = SimpleNamespace(
            record_id=1, period="morning", checkin_time="09:00", checkout_time="12:00",
        )
        checkin_svc.get_period_end_time.return_value = None
        checkin_svc.mark_absent.return_value = None

        return checkin_svc, promise_svc, motivation_svc, report_svc, shooting_svc

    @pytest.fixture
    def screen(self, services) -> CheckinScreen:
        """创建 CheckinScreen 实例。"""
        checkin_svc, promise_svc, motivation_svc, report_svc, shooting_svc = services
        screen = CheckinScreen(
            checkin_service=checkin_svc,
            promise_service=promise_svc,
            motivation_service=motivation_svc,
            report_service=report_svc,
            shooting_service=shooting_svc,
        )
        Clock.tick()
        return screen

    def test_refresh_status_calls_set_status_from_period_on_all_cards(
        self, screen, services
    ) -> None:
        """_refresh_status 应对每个 PeriodCard 调用 set_status_from_period。"""
        checkin_svc = services[0]

        # 替换卡片为 mock 以便验证 set_status_from_period 调用
        mock_morning = MagicMock()
        mock_afternoon = MagicMock()
        mock_evening = MagicMock()
        screen._period_cards = {
            "morning": mock_morning,
            "afternoon": mock_afternoon,
            "evening": mock_evening,
        }

        # 设置 get_today_status 返回签到后的状态
        checkin_svc.get_today_status.return_value = _make_day_status([
            _make_period_status("morning", "normal", "09:00", None),
            _make_period_status("afternoon", "pending"),
            _make_period_status("evening", "pending"),
        ])

        screen._refresh_status()

        # 验证每个卡片都被调用了 set_status_from_period
        mock_morning.set_status_from_period.assert_called_once()
        mock_afternoon.set_status_from_period.assert_called_once()
        mock_evening.set_status_from_period.assert_called_once()

        # 验证传入参数正确：morning 应为 normal + checkin_time
        called_ps = mock_morning.set_status_from_period.call_args[0][0]
        assert called_ps.status == "normal"
        assert called_ps.checkin_time == "09:00"

    def test_refresh_status_updates_status_box(self, screen, services) -> None:
        """_refresh_status 应更新 StatusBox。"""
        checkin_svc = services[0]
        screen._status_box = MagicMock()

        checkin_svc.get_today_status.return_value = _make_day_status([
            _make_period_status("morning", "normal", "09:00", "12:00"),
            _make_period_status("afternoon", "pending"),
            _make_period_status("evening", "pending"),
        ])

        screen._refresh_status()

        screen._status_box.update_status.assert_called_once()

    def test_checkin_triggers_get_today_status(self, screen, services) -> None:
        """签到后 _refresh_status 应调用 get_today_status 刷新数据。"""
        checkin_svc = services[0]
        checkin_svc.get_today_status.reset_mock()

        screen._do_checkin("morning")
        # 手动触发 refresh（实际由 panel dismiss 回调触发）
        screen._refresh_status()

        assert checkin_svc.get_today_status.called

    def test_checkout_triggers_get_today_status(self, screen, services) -> None:
        """签退后 _refresh_status 应调用 get_today_status 刷新数据。"""
        checkin_svc = services[0]
        checkin_svc.get_today_status.reset_mock()

        # _on_checkout 需要 get_period_end_time 返回 None 才跳过确认框
        screen._on_checkout("morning")
        screen._refresh_status()

        assert checkin_svc.get_today_status.called
