"""考勤奖惩服务"""

from __future__ import annotations

from datetime import timedelta

from app.models.ledger import LedgerEntry
from app.repositories.checkin_repo import CheckinRepo
from app.repositories.ledger_repo import LedgerRepo
from app.repositories.settings_repo import SettingsRepo
from app.services.event_bus import EventType, get_event_bus
from app.utils.clock import get_clock
from app.utils.config import (
    LEDGER_TYPE_ABSENT,
    LEDGER_TYPE_EARLY_LEAVE,
    LEDGER_TYPE_FULL_ATTENDANCE_BONUS,
    LEDGER_TYPE_LATE,
    STATUS_ABSENT_AFTERNOON,
    STATUS_ABSENT_MORNING,
    STATUS_EARLY_LEAVE,
    STATUS_LATE,
    STATUS_LEAVE,
)


class PenaltyService:
    """考勤奖惩计算"""

    def __init__(
        self,
        checkin_repo: CheckinRepo,
        ledger_repo: LedgerRepo,
        settings_repo: SettingsRepo,
    ) -> None:
        self._checkin_repo = checkin_repo
        self._ledger_repo = ledger_repo
        self._settings_repo = settings_repo

        bus = get_event_bus()
        bus.subscribe(EventType.ATTENDANCE_JUDGED, self._on_attendance_judged)
        bus.subscribe(EventType.DAY_FINISHED, self._on_day_finished)

    def calculate_daily(self, date: str) -> list[LedgerEntry]:
        """根据当天出勤判定结果计算奖惩流水"""
        records = self._checkin_repo.get_all_by_date(date)
        entries: list[LedgerEntry] = []

        for record in records:
            if not record.status:
                continue
            entry = self._entry_for_status(record.status, date, record.period)
            if entry:
                entries.append(entry)
                self._ledger_repo.insert(entry)

        return entries

    def calculate_weekly_full_attendance(self, week_start: str) -> LedgerEntry | None:
        """全勤判定：整周无迟到/早退/旷工/请假 → 奖励"""
        records = self._checkin_repo.get_all_by_week(week_start)

        bad_statuses = {
            STATUS_LATE, STATUS_EARLY_LEAVE,
            STATUS_ABSENT_MORNING, STATUS_ABSENT_AFTERNOON, STATUS_LEAVE,
        }

        for r in records:
            if r.status in bad_statuses:
                return None

        # Need at least some records to count
        if not records:
            return None

        bonus = float(self._get_setting("full_attendance_bonus"))
        clock = get_clock()
        # End date is Sunday (6 days after week start)
        week_start_dt = clock.now().replace(
            year=int(week_start[:4]),
            month=int(week_start[5:7]),
            day=int(week_start[8:10]),
        )
        end_date = (week_start_dt + timedelta(days=6)).strftime("%Y-%m-%d")

        entry = LedgerEntry(
            entry_date=end_date,
            week_start=week_start,
            type=LEDGER_TYPE_FULL_ATTENDANCE_BONUS,
            amount=bonus,
            description="全勤奖励",
        )
        self._ledger_repo.insert(entry)
        return entry

    def _entry_for_status(self, status: str, date: str, period: str) -> LedgerEntry | None:
        """根据状态生成单条流水"""
        period_label = "上午" if period == "morning" else "下午"
        penalty_map = {
            STATUS_LATE: (LEDGER_TYPE_LATE, "late_penalty", f"{period_label}迟到"),
            STATUS_EARLY_LEAVE: (LEDGER_TYPE_EARLY_LEAVE, "early_leave_penalty", f"{period_label}早退"),
            STATUS_ABSENT_MORNING: (LEDGER_TYPE_ABSENT, "absent_penalty", "上午旷工"),
            STATUS_ABSENT_AFTERNOON: (LEDGER_TYPE_ABSENT, "absent_penalty", "下午旷工"),
        }

        if status not in penalty_map:
            return None

        ledger_type, setting_key, desc = penalty_map[status]
        amount = -float(self._get_setting(setting_key))

        return LedgerEntry(
            entry_date=date,
            type=ledger_type,
            amount=amount,
            description=desc,
        )

    def _get_setting(self, key: str) -> str:
        val = self._settings_repo.get(key)
        if val is not None:
            return val
        from app.services.settings_service import SettingsService
        return SettingsService.DEFAULTS.get(key, "")

    def _on_attendance_judged(self, event_type: EventType, payload: dict[str, object]) -> None:
        date = str(payload.get("date", ""))
        if date:
            self.calculate_daily(date)

    def _on_day_finished(self, event_type: EventType, payload: dict[str, object]) -> None:
        date = str(payload.get("date", ""))
        if not date:
            return
        clock = get_clock()
        weekday = clock.now().weekday()  # 0=Monday
        if weekday == 6:  # Sunday
            week_start = self._get_week_start(date)
            self.calculate_weekly_full_attendance(week_start)

    @staticmethod
    def _get_week_start(date: str) -> str:
        from datetime import datetime
        dt = datetime.strptime(date, "%Y-%m-%d")
        weekday = dt.weekday()
        monday = dt - timedelta(days=weekday)
        return monday.strftime("%Y-%m-%d")
