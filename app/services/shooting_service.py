"""拍摄日模块服务层"""

from __future__ import annotations

import random

from app.models.shooting import ShootingDay, ShootingReflection
from app.repositories.shooting_repo import ShootingRepo
from app.services.event_bus import EventType, get_event_bus
from app.utils.clock import get_clock

TRANSITIONS_SMOOTH = ["顺利完成了", "高效地完成了", "顺畅地进行了"]
TRANSITIONS_NORMAL = ["进行了", "完成了", "执行了"]
TRANSITIONS_ROUGH = ["艰难地完成了", "克服困难完成了", "勉强完成了"]


class ShootingService:
    """拍摄日业务逻辑"""

    def __init__(self, shooting_repo: ShootingRepo) -> None:
        self._repo = shooting_repo

    def set_shooting_day(self, date: str, reward_desc: str = "") -> ShootingDay:
        """将某天设为拍摄日"""
        day = ShootingDay(shoot_date=date, reward_desc=reward_desc)
        saved = self._repo.set_shooting_day(day)
        get_event_bus().publish(
            EventType.SHOOTING_DAY_SET,
            {"date": date, "reward_desc": reward_desc},
        )
        return saved

    def cancel_shooting_day(self, date: str) -> bool:
        """取消拍摄日（仅当天上午打卡时间前可取消）"""
        clock = get_clock()
        today = clock.today_str()
        if date != today:
            return False
        current_time = clock.current_time_str()
        # Check morning start time
        from app.repositories.settings_repo import SettingsRepo
        settings = SettingsRepo()
        morning_start = settings.get("morning_start") or "09:00"
        if current_time >= morning_start:
            return False
        self._repo.cancel(date)
        return True

    def is_shooting_day(self, date: str) -> bool:
        day = self._repo.get_by_date(date)
        return day is not None and day.status == "active"

    @staticmethod
    def get_reflection_questions() -> list[str]:
        return [
            "拍摄内容是什么？",
            "拍摄地点在哪？",
            "拍摄是否顺利？",
            "有什么感想？",
        ]

    def submit_reflection(self, date: str, answers: dict[str, str]) -> ShootingReflection:
        summary = self._generate_summary(answers)
        ref = ShootingReflection(
            shoot_date=date,
            content=answers.get("content", ""),
            location=answers.get("location", ""),
            was_smooth=answers.get("smoothness", "normal"),
            thoughts=answers.get("thoughts", ""),
            summary=summary,
        )
        return self._repo.save_reflection(ref)

    def get_reflection(self, date: str) -> ShootingReflection | None:
        return self._repo.get_reflection(date)

    def _generate_summary(self, answers: dict[str, str]) -> str:
        smoothness = answers.get("smoothness", "normal")
        location = answers.get("location", "")
        content = answers.get("content", "")
        thoughts = answers.get("thoughts", "")

        if smoothness == "smooth":
            transition = random.choice(TRANSITIONS_SMOOTH)
        elif smoothness == "rough":
            transition = random.choice(TRANSITIONS_ROUGH)
        else:
            transition = random.choice(TRANSITIONS_NORMAL)

        parts = [f"今天在{location}{transition}{content}的拍摄"]
        if smoothness == "rough":
            parts.append("，遇到了一些挑战")
        if thoughts:
            parts.append(f"。{thoughts}")
        return "".join(parts)
