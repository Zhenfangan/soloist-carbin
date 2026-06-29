"""设置模块服务层"""

from __future__ import annotations

import json

from kivy.logger import Logger

from app.repositories.settings_repo import SettingsRepo
from app.services.event_bus import EventType, get_event_bus

ONBOARDING_KEY = "_onboarding_completed"


class SettingsService:
    """全部可配置参数管理 + 首次引导"""

    DEFAULTS: dict[str, str] = {
        "morning_start": "09:00",
        "morning_end": "12:00",
        "afternoon_start": "14:00",
        "afternoon_end": "18:00",
        "late_penalty": "10",
        "early_leave_penalty": "10",
        "absent_penalty": "50",
        "full_attendance_bonus": "100",
        "bet_base_reward": "50",
        "bet_extra_reward": "30",
        "bet_penalty": "50",
        "bet_late_fee_per_day": "10",
        "work_days": "1,2,3,4,5",
        "shooting_reward": "30",
        "boyfriend_hour_threshold": "8",
        "ntfy_enabled": "0",
        "ntfy_topic": "",
        "ntfy_server": "https://ntfy.sh",
        "user_nickname": "",
        "encouragements_user": "[]",
    }

    def __init__(self, settings_repo: SettingsRepo) -> None:
        self._repo = settings_repo

    def get(self, key: str) -> str:
        """读取单个设置项，未设时返回默认值"""
        val = self._repo.get(key)
        if val is not None:
            return val
        return self.DEFAULTS.get(key, "")

    def set(self, key: str, value: str) -> None:
        """写入单个设置项，发布 SETTINGS_CHANGED 事件"""
        self._repo.set(key, value)
        get_event_bus().publish(EventType.SETTINGS_CHANGED, {"key": key, "value": value})

    def get_all(self) -> dict[str, str]:
        """返回所有设置项（默认值 + 已保存值合并）"""
        result = dict(self.DEFAULTS)
        saved = self._repo.get_all()
        result.update(saved)
        return result

    def batch_set(self, settings: dict[str, str]) -> None:
        """批量写入（首次引导使用）"""
        self._repo.batch_set(settings)
        get_event_bus().publish(EventType.SETTINGS_CHANGED, settings)

    def is_first_launch(self) -> bool:
        """检查是否首次启动"""
        return self._repo.get(ONBOARDING_KEY) is None

    def complete_onboarding(self) -> None:
        """标记引导完成"""
        self._repo.set(ONBOARDING_KEY, "1")

    def get_work_days(self) -> list[int]:
        """解析工作日设置为整数列表"""
        val = self.get("work_days")
        if not val:
            return [1, 2, 3, 4, 5]
        return [int(x.strip()) for x in val.split(",") if x.strip()]

    def is_work_day(self, weekday: int) -> bool:
        """判断指定星期几是否为工作日 (1=周一, 7=周日)"""
        return weekday in self.get_work_days()

    def get_user_encouragements(self) -> list[str]:
        """读取用户自定义激励语录，JSON 解析失败或类型异常时返回空列表"""
        raw = self.get("encouragements_user")
        if not raw:
            return []
        try:
            items = json.loads(raw)
        except json.JSONDecodeError:
            Logger.warning(
                "SettingsService: encouragements_user JSON decode failed: %r", raw
            )
            return []
        if not isinstance(items, list):
            return []
        return [s for s in items if isinstance(s, str) and s.strip()]

    def set_user_encouragements(self, items: list[str]) -> None:
        """写入用户自定义激励语录，自动 JSON 编码并发布 SETTINGS_CHANGED 事件"""
        encoded = json.dumps(items, ensure_ascii=False)
        self.set("encouragements_user", encoded)

    def get_user_nickname(self) -> str:
        """获取用户自定义称呼，空字符串表示未设置"""
        return self.get("user_nickname") or ""

    def set_user_nickname(self, nickname: str) -> None:
        """设置用户自定义称呼"""
        self.set("user_nickname", nickname.strip())

    def format_nickname(self, template: str) -> str:
        """将模板中的 {称呼} 替换为用户昵称，未设置则去掉占位符"""
        nickname = self.get_user_nickname()
        if nickname:
            return template.replace("{称呼}", nickname)
        # 去掉占位符及紧随的标点空格，保留干净文本
        import re
        return re.sub(r"\{称呼\}[，,。.]?\s*", "", template).strip()
