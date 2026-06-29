"""考勤模块服务层 — 打卡/签退/请假/状态判定"""

from __future__ import annotations

from typing import Any

from app.models.checkin import Checkin, CheckinResult, DayStatus, PeriodStatus
from app.repositories.checkin_repo import CheckinRepo
from app.repositories.settings_repo import SettingsRepo
from app.services.event_bus import EventType, get_event_bus
from app.utils.clock import get_clock
from app.utils.config import (
    CHECKOUT_TYPE_AUTO,
    CHECKOUT_TYPE_MANUAL,
    STATUS_ABSENT_AFTERNOON,
    STATUS_ABSENT_MORNING,
    STATUS_EARLY_LEAVE,
    STATUS_LATE,
    STATUS_LEAVE,
    STATUS_NORMAL,
    STATUS_PENDING,
    STATUS_SHOOTING,
)

# 时段 → 设置键
_PERIOD_START_KEY = {
    "morning": "morning_start",
    "afternoon": "afternoon_start",
    "evening": "",  # 晚间弹性
}
_PERIOD_END_KEY = {
    "morning": "morning_end",
    "afternoon": "afternoon_end",
    "evening": "",  # 晚间弹性
}

LEAVE_SCOPE_MORNING = "morning"
LEAVE_SCOPE_AFTERNOON = "afternoon"
LEAVE_SCOPE_ALL_DAY = "all_day"

ALL_PERIODS = ["morning", "afternoon", "evening"]


class CheckinService:
    """考勤业务逻辑"""

    def __init__(self, checkin_repo: CheckinRepo, settings_repo: SettingsRepo,
                 shooting_service: Any = None) -> None:
        self._checkin_repo = checkin_repo
        self._settings_repo = settings_repo
        self._shooting_service = shooting_service

    # ── 打卡动作 ──────────────────────────────────────────

    def check_in(self, date: str, period: str, photo_path: str | None = None) -> CheckinResult:
        """执行签到，判定出勤状态。终态(请假/拍摄日)不可被签到覆盖。"""
        clock = get_clock()
        now_time = clock.current_time_str()

        # 防御: 已有终态记录时不允许签到覆盖
        existing = self._checkin_repo.get_by_date_period(date, period)
        if existing is not None and existing.status in (STATUS_LEAVE, STATUS_SHOOTING):
            return self._make_result(existing)

        record = Checkin(checkin_date=date, period=period, checkin_time=now_time, photo_path=photo_path)
        record = self._checkin_repo.upsert(record)

        status = self._judge_checkin_status(date, period, now_time)
        record.status = status
        record = self._checkin_repo.upsert(record)

        result = self._make_result(record)

        get_event_bus().publish(
            EventType.CHECK_IN_COMPLETED,
            {"date": date, "period": period, "checkin_time": now_time, "status": status},
        )
        get_event_bus().publish(
            EventType.ATTENDANCE_JUDGED,
            {"date": date, "period": period, "status": status},
        )

        return result

    def check_out(self, date: str, period: str, photo_path: str | None = None) -> CheckinResult:
        """执行签退，判定状态，检测是否当日所有时段完成"""
        clock = get_clock()
        now_time = clock.current_time_str()

        record = self._checkin_repo.get_by_date_period(date, period)
        if record is None:
            raise ValueError(f"尚未签到，无法签退: {date} {period}")
        record.checkout_time = now_time
        record.checkout_type = CHECKOUT_TYPE_MANUAL
        if photo_path is not None:
            record.photo_path = photo_path

        status = self._judge_checkout_status(date, period, now_time, record)
        record.status = status
        record = self._checkin_repo.upsert(record)

        result = self._make_result(record)

        get_event_bus().publish(
            EventType.CHECK_OUT_COMPLETED,
            {"date": date, "period": period, "checkout_time": now_time, "status": status},
        )

        if self._is_day_finished(date):
            get_event_bus().publish(EventType.DAY_FINISHED, {"date": date})

        return result

    # ── 请假 ──────────────────────────────────────────────

    def get_leave_options(self, date: str, current_time: str) -> list[str]:
        """返回当前可选的请假范围"""
        morning_start = self._get_setting("morning_start")
        afternoon_start = self._get_setting("afternoon_start")

        # 已过上午上班时间 → 不可请上午
        morning_passed = current_time >= morning_start
        afternoon_passed = current_time >= afternoon_start

        if not morning_passed:
            return [LEAVE_SCOPE_MORNING, LEAVE_SCOPE_AFTERNOON, LEAVE_SCOPE_ALL_DAY]
        if not afternoon_passed:
            return [LEAVE_SCOPE_AFTERNOON]
        return []

    def apply_leave(self, date: str, scope: str) -> list[CheckinResult]:
        """执行请假"""
        periods_to_leave: list[str] = []
        if scope == LEAVE_SCOPE_MORNING:
            periods_to_leave = ["morning"]
        elif scope == LEAVE_SCOPE_AFTERNOON:
            periods_to_leave = ["afternoon"]
        elif scope == LEAVE_SCOPE_ALL_DAY:
            periods_to_leave = ["morning", "afternoon"]

        results: list[CheckinResult] = []
        clock = get_clock()
        now_time = clock.current_time_str()

        for period in periods_to_leave:
            record = self._checkin_repo.get_by_date_period(date, period)
            if record is None:
                record = Checkin(checkin_date=date, period=period)
            record.status = STATUS_LEAVE
            record.checkin_time = record.checkin_time or now_time
            record.checkout_time = record.checkout_time or now_time
            record = self._checkin_repo.upsert(record)
            results.append(self._make_result(record))

            get_event_bus().publish(
                EventType.ATTENDANCE_JUDGED,
                {"date": date, "period": period, "status": STATUS_LEAVE},
            )

        return results

    # ── 状态查询 ──────────────────────────────────────────

    def get_today_status(self, date: str) -> DayStatus:
        """返回今日各时段状态快照"""
        records = self._checkin_repo.get_all_by_date(date)
        day = DayStatus(date=date)

        absent_statuses = {STATUS_ABSENT_MORNING, STATUS_ABSENT_AFTERNOON}

        for period in ALL_PERIODS:
            match = next((r for r in records if r.period == period), None)
            if match:
                status = match.status or STATUS_PENDING
                penalty: float | None = None
                if status in absent_statuses:
                    penalty = -abs(float(self._get_setting("absent_penalty") or "0"))
                day.periods.append(
                    PeriodStatus(
                        period=period,
                        status=status,
                        checkin_time=match.checkin_time,
                        checkout_time=match.checkout_time,
                        checkout_type=match.checkout_type,
                        penalty_amount=penalty,
                    )
                )
                if match.is_shooting:
                    day.is_shooting_day = True
            else:
                day.periods.append(PeriodStatus(period=period, status=STATUS_PENDING))

        return day

    # ── 旷工判定 ──────────────────────────────────────────

    def mark_absent(self, date: str) -> list[CheckinResult]:
        """检查并标记旷工时段（APP 前台时调用）"""
        clock = get_clock()
        now_time = clock.current_time_str()

        results: list[CheckinResult] = []

        for period, end_key in [
            ("morning", "morning_end"),
            ("afternoon", "afternoon_end"),
        ]:
            end = self._time_to_minutes(self._get_setting(end_key))
            current_min = self._time_to_minutes(now_time)

            # 只有过了时段结束时间还没签到，才判定旷工
            if current_min < end:
                # 时间倒退: 撤销之前误判的旷工
                record = self._checkin_repo.get_by_date_period(date, period)
                if record and record.status in (STATUS_ABSENT_MORNING, STATUS_ABSENT_AFTERNOON):
                    record.status = STATUS_PENDING
                    record.checkin_time = None
                    self._checkin_repo.upsert(record)
                    results.append(self._make_result(record))
                continue

            record = self._checkin_repo.get_by_date_period(date, period)
            if record and record.status in (STATUS_LEAVE, STATUS_SHOOTING):
                continue
            if record and record.checkin_time:
                continue
            if record and record.status in (STATUS_ABSENT_MORNING, STATUS_ABSENT_AFTERNOON):
                continue

            absent_status = (
                STATUS_ABSENT_MORNING if period == "morning" else STATUS_ABSENT_AFTERNOON
            )
            if record is None:
                record = Checkin(checkin_date=date, period=period, status=absent_status)
            else:
                record.status = absent_status
            record = self._checkin_repo.upsert(record)
            results.append(self._make_result(record))

            get_event_bus().publish(
                EventType.ATTENDANCE_JUDGED,
                {"date": date, "period": period, "status": absent_status},
            )

        return results

    # ── 忘记签退处理 ──────────────────────────────────────

    def auto_checkout(self, date: str) -> list[CheckinResult]:
        """自动签退：扫描有签到但无签退的时段，按设定下班时间自动签退"""
        unchecked = self._checkin_repo.get_unchecked_out(date)
        results: list[CheckinResult] = []

        for record in unchecked:
            end_key = _PERIOD_END_KEY.get(record.period, "")
            if not end_key:
                continue
            end_time = self._get_setting(end_key)
            record.checkout_time = end_time
            record.checkout_type = CHECKOUT_TYPE_AUTO
            record = self._checkin_repo.upsert(record)
            results.append(self._make_result(record))

        if results and self._is_day_finished(date):
            get_event_bus().publish(EventType.DAY_FINISHED, {"date": date})

        return results

    # ── 内部方法 ──────────────────────────────────────────

    def _judge_checkin_status(self, date: str, period: str, checkin_time: str) -> str:
        """判定签到状态 — 含时段窗口校验"""
        if self._is_shooting_day(date):
            return STATUS_SHOOTING
        if self._is_leave_day(date, period):
            return STATUS_LEAVE
        if period == "evening":
            return STATUS_NORMAL

        start_key = _PERIOD_START_KEY.get(period, "")
        if not start_key:
            return STATUS_NORMAL

        configured_start = self._get_setting(start_key)
        configured_end = self._get_setting(_PERIOD_END_KEY.get(period, ""))

        # 时段窗口已关闭 → 旷工
        if configured_end and self._time_to_minutes(checkin_time) > self._time_to_minutes(configured_end):
            return (
                STATUS_ABSENT_MORNING if period == "morning"
                else STATUS_ABSENT_AFTERNOON
            )

        # 时段窗口内 → 正常或迟到（空配置视为不限制）
        start_min = self._time_to_minutes(configured_start)
        if start_min == 0 or self._time_to_minutes(checkin_time) <= start_min:
            return STATUS_NORMAL
        return STATUS_LATE

    def _judge_checkout_status(
        self, date: str, period: str, checkout_time: str, checkin_record: Checkin | None = None
    ) -> str:
        """判定签退状态 — 保留签到阶段的迟到/旷工标记"""
        record = checkin_record or self._checkin_repo.get_by_date_period(date, period)
        if record and record.status in (STATUS_LEAVE, STATUS_SHOOTING):
            return record.status
        if self._is_shooting_day(date):
            return STATUS_SHOOTING
        if self._is_leave_day(date, period):
            return STATUS_LEAVE
        if period == "evening":
            return STATUS_NORMAL

        # 签到阶段的"坏"状态不被签退覆盖
        checkin_status = record.status if record else STATUS_PENDING
        preserved = (
            checkin_status
            if checkin_status in (STATUS_LATE, STATUS_ABSENT_MORNING, STATUS_ABSENT_AFTERNOON)
            else None
        )

        end_key = _PERIOD_END_KEY.get(period, "")
        if not end_key:
            return preserved or STATUS_NORMAL

        configured_end = self._get_setting(end_key)
        if self._time_to_minutes(checkout_time) >= self._time_to_minutes(configured_end):
            return preserved or STATUS_NORMAL
        return preserved or STATUS_EARLY_LEAVE

    def _is_shooting_day(self, date: str) -> bool:
        # 优先查 shooting_days 表
        if self._shooting_service is not None and self._shooting_service.is_shooting_day(date):
            return True
        # 回退兼容 checkins.is_shooting 字段
        records = self._checkin_repo.get_all_by_date(date)
        return any(r.is_shooting for r in records)

    def _is_leave_day(self, date: str, period: str) -> bool:
        record = self._checkin_repo.get_by_date_period(date, period)
        return record is not None and record.status == STATUS_LEAVE

    def _is_day_finished(self, date: str) -> bool:
        """检查当天所有非加班时段是否都已签退"""
        records = self._checkin_repo.get_all_by_date(date)
        checked_out = {
            r.period
            for r in records
            if r.checkout_time and r.period in ("morning", "afternoon")
        }
        leave_periods = {
            r.period for r in records if r.status == STATUS_LEAVE
        }
        required = {"morning", "afternoon"}
        return required <= (checked_out | leave_periods)

    def get_period_end_time(self, period: str) -> str:
        """返回时段结束时间字符串（HH:MM），晚间弹性时段返回空字符串。"""
        key = _PERIOD_END_KEY.get(period, "")
        return self._get_setting(key) if key else ""

    def _get_setting(self, key: str) -> str:
        val = self._settings_repo.get(key)
        if val is not None:
            return val
        from app.services.settings_service import SettingsService
        return SettingsService.DEFAULTS.get(key, "")

    @staticmethod
    def _time_to_minutes(time_str: str) -> int:
        if not time_str or ":" not in time_str:
            return 0
        parts = time_str.split(":")
        try:
            return int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            return 0

    def _make_result(self, record: Checkin) -> CheckinResult:
        labels: dict[str, str] = {
            STATUS_PENDING: "待判定",
            STATUS_NORMAL: "正常",
            STATUS_LATE: "迟到",
            STATUS_EARLY_LEAVE: "早退",
            STATUS_ABSENT_MORNING: "旷工(上午)",
            STATUS_ABSENT_AFTERNOON: "旷工(下午)",
            STATUS_LEAVE: "请假",
            STATUS_SHOOTING: "拍摄日",
        }
        return CheckinResult(
            date=record.checkin_date,
            period=record.period,
            checkin_time=record.checkin_time,
            checkout_time=record.checkout_time,
            checkout_type=record.checkout_type,
            status=record.status or STATUS_PENDING,
            status_label=labels.get(record.status or STATUS_PENDING, "未知"),
        )
