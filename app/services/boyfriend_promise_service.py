"""男友承诺服务"""

from __future__ import annotations

from typing import Any

from app.models.ledger import BoyfriendPromise, LedgerEntry
from app.repositories.ledger_repo import LedgerRepo
from app.repositories.settings_repo import SettingsRepo
from app.services.event_bus import EventType, get_event_bus
from app.utils.config import LEDGER_TYPE_BOYFRIEND_PROMISE


class BoyfriendPromiseService:
    """男友激励承诺管理"""

    def __init__(
        self,
        ledger_repo: LedgerRepo,
        settings_repo: SettingsRepo,
        checkin_repo: Any = None,
    ) -> None:
        self._ledger_repo = ledger_repo
        self._settings_repo = settings_repo
        self._checkin_repo = checkin_repo

        get_event_bus().subscribe(EventType.DAY_FINISHED, self._on_day_finished)

    def set_promise(self, date: str, reward_desc: str, reward_qty: int = 1) -> BoyfriendPromise:
        """设置当日承诺"""
        promise = BoyfriendPromise(
            promise_date=date,
            reward_desc=reward_desc,
            reward_qty=reward_qty,
        )
        saved = self._ledger_repo.upsert_promise(promise)
        get_event_bus().publish(
            EventType.PROMISE_SET,
            {"date": date, "reward_desc": reward_desc, "reward_qty": reward_qty},
        )
        return saved

    def check_fulfill(self, date: str, total_work_hours: float) -> bool:
        """检测工作时长是否达标"""
        threshold = float(self._get_setting("boyfriend_hour_threshold"))
        promise = self._ledger_repo.get_promise(date)

        if promise is None:
            return False
        if total_work_hours < threshold:
            return False

        promise.fulfilled = 1
        self._ledger_repo.upsert_promise(promise)

        entry = LedgerEntry(
            entry_date=date,
            type=LEDGER_TYPE_BOYFRIEND_PROMISE,
            amount=0,  # 男友承诺不计入虚拟账本金额
            reward_item=promise.reward_desc,
            reward_qty=promise.reward_qty,
            fulfilled=1,
            description=promise.reward_desc,
        )
        self._ledger_repo.insert(entry)
        return True

    def get_today_promise(self, date: str) -> BoyfriendPromise | None:
        """查询当天承诺"""
        return self._ledger_repo.get_promise(date)

    def calculate_total_hours(self, date: str) -> float:
        """计算当日总工作时长（小时）"""
        if self._checkin_repo is None:
            return 0.0
        records = self._checkin_repo.get_all_by_date(date)
        total = 0.0
        for r in records:
            if r.checkin_time and r.checkout_time:
                ci_mins = self._time_to_minutes(r.checkin_time)
                co_mins = self._time_to_minutes(r.checkout_time)
                diff = co_mins - ci_mins
                if diff > 0:
                    total += diff / 60.0
        return total

    def _get_setting(self, key: str) -> str:
        val = self._settings_repo.get(key)
        if val is not None:
            return val
        from app.services.settings_service import SettingsService
        return SettingsService.DEFAULTS.get(key, "")

    def _on_day_finished(self, event_type: EventType, payload: dict[str, object]) -> None:
        date = str(payload.get("date", ""))
        if date:
            hours = self.calculate_total_hours(date)
            self.check_fulfill(date, hours)

    @staticmethod
    def _time_to_minutes(time_str: str) -> int:
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])
