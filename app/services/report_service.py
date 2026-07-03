"""战报模块服务层"""

from __future__ import annotations

import json
import random

from app.models.report import PeriodDetail, PromiseDetail, ReportData
from app.repositories.checkin_repo import CheckinRepo
from app.repositories.ledger_repo import LedgerRepo
from app.repositories.settings_repo import SettingsRepo
from app.repositories.shooting_repo import ShootingRepo
from app.services.event_bus import EventType, get_event_bus

ENCOURAGEMENTS = [
    "每个努力的日子都值得被记住，继续加油！",
    "自律是通往自由最快的路。",
    "今天辛苦啦，明天会更好！",
    "一点点进步，积累起来就是巨大的改变。",
    "坚持下去，你就是自己的光。",
]

DAILY_REPORT_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body { font-family: sans-serif; padding: 16px; max-width: 400px; margin: 0 auto; }
.header { text-align: center; margin-bottom: 16px; }
.date { font-size: 18px; font-weight: bold; }
.section { margin: 12px 0; padding: 8px; border-radius: 8px; background: #fafafa; }
.period { display: flex; justify-content: space-between; padding: 4px 0; }
.status-normal { color: #27ae60; }
.status-late { color: #f39c12; }
.status-early_leave { color: #e67e22; }
.status-absent { color: #e74c3c; }
.status-leave { color: #3498db; }
.status-shooting { color: #e67e22; }
.penalty { color: #e74c3c; }
.reward { color: #27ae60; }
.encourage { text-align: center; font-size: 14px; color: #666; margin-top: 16px; }
.promise { background: #ffeaa7; padding: 8px; border-radius: 4px; }
.overtime { background: #fab1a0; padding: 8px; border-radius: 4px; text-align: center; }
</style></head><body>
<div class="header">
  <div class="date">{{ data.date }}</div>
  <div>{% if data.is_shooting_day %}📸 拍摄日{% else %}💼 办公日{% endif %}</div>
</div>

<div class="section">
  <b>打卡详情</b>
  {% for p in data.periods %}
  <div class="period">
    <span>{% if p.period == "morning" %}上午{% elif p.period == "afternoon" %}下午{% else %}晚上(加班){% endif %}</span>
    <span>
      {% if p.checkin_time %}{{ p.checkin_time }}{% else %}--{% endif %}
      ~
      {% if p.checkout_time %}{{ p.checkout_time }}{% else %}--{% endif %}
    </span>
    <span class="status-{{ p.status }}">{{ p.status_label }}</span>
  </div>
  {% endfor %}
</div>

<div class="section">
  <b>奖惩汇总</b>
  <p>罚款: <span class="penalty">{{ data.penalty_total }}</span></p>
  <p>奖励: <span class="reward">{{ data.reward_total }}</span></p>
  <p>净额: {{ data.net_amount }}</p>
</div>

<div class="section">
  <b>工作时长</b>
  <p>总计: {{ "%.1f"|format(data.total_work_hours) }}h</p>
  {% if data.overtime_hours > 0 %}<p>加班: {{ "%.1f"|format(data.overtime_hours) }}h</p>{% endif %}
</div>

{% if data.total_work_hours >= data.threshold_hours %}
<div class="overtime">
  ✨ 今天工作超过 {{ "%.0f"|format(data.threshold_hours) }} 小时，太棒了！给自己一个大大的赞！✨
</div>
{% endif %}

{% if data.promise %}
<div class="promise">
  🎁 男友承诺: {{ data.promise.reward_desc }} ×{{ data.promise.reward_qty }}
  {% if data.promise.fulfilled %}(已兑现 ✅){% else %}(未达标 ⏳){% endif %}
</div>
{% endif %}

{% if data.completed_tasks %}
<div class="section">
  <b>完成的任务</b>
  {% for task in data.completed_tasks %}
  <div>✅ {{ task }}</div>
  {% endfor %}
</div>
{% endif %}

<div class="encourage">{{ data.encouragement }}</div>
</body></html>"""

SHOOTING_REPORT_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body { font-family: sans-serif; padding: 16px; max-width: 400px; margin: 0 auto; }
.header { text-align: center; margin-bottom: 16px; }
.date { font-size: 18px; font-weight: bold; }
.section { margin: 12px 0; padding: 8px; border-radius: 8px; background: #fafafa; }
.encourage { text-align: center; font-size: 14px; color: #666; margin-top: 16px; }
</style></head><body>
<div class="header">
  <div class="date">{{ data.date }}</div>
  <div>📸 拍摄日</div>
</div>

<div class="section">
  <b>拍摄日奖励</b>
  <p>✨ 今日拍摄奖励已计入账本</p>
</div>

{% if data.shooting_reflection %}
<div class="section">
  <b>拍摄复盘</b>
  {% if data.shooting_content %}<p>内容：{{ data.shooting_content }}</p>{% endif %}
  {% if data.shooting_location %}<p>地点：{{ data.shooting_location }}</p>{% endif %}
  <p>{{ data.shooting_reflection }}</p>
</div>
{% endif %}

{% if data.completed_tasks %}
<div class="section">
  <b>完成的任务</b>
  {% for task in data.completed_tasks %}
  <div>✅ {{ task }}</div>
  {% endfor %}
</div>
{% endif %}

<div class="encourage">{{ data.encouragement }}</div>
</body></html>"""


class ReportService:
    """战报生成服务"""

    def __init__(
        self,
        checkin_repo: CheckinRepo,
        ledger_repo: LedgerRepo,
        shooting_repo: ShootingRepo,
        settings_repo: SettingsRepo | None = None,
    ) -> None:
        self._checkin_repo = checkin_repo
        self._ledger_repo = ledger_repo
        self._shooting_repo = shooting_repo
        self._settings_repo = settings_repo

        get_event_bus().subscribe(EventType.DAY_CLOSED, self._on_day_closed)

    def collect_data(self, date: str) -> ReportData:
        """从各 Repository 收集当天数据"""
        records = self._checkin_repo.get_all_by_date(date)
        is_shooting = any(r.is_shooting for r in records)

        # 拍摄日复盘数据
        shooting_content = ""
        shooting_location = ""
        shooting_reflection = ""
        if is_shooting:
            refl = self._shooting_repo.get_reflection(date)
            if refl:
                shooting_content = refl.content or ""
                shooting_location = refl.location or ""
                shooting_reflection = refl.summary or refl.thoughts or ""

        status_labels = {
            "pending": "待判定", "normal": "正常", "late": "迟到",
            "early_leave": "早退", "absent_morning": "旷工(上午)",
            "absent_afternoon": "旷工(下午)", "leave": "请假", "shooting": "拍摄日",
        }

        periods = []
        total_hours = 0.0
        for r in records:
            periods.append(PeriodDetail(
                period=r.period,
                checkin_time=r.checkin_time,
                checkout_time=r.checkout_time,
                status=r.status or "pending",
                status_label=status_labels.get(r.status or "pending", "未知"),
            ))
            if r.checkin_time and r.checkout_time:
                ci = self._time_to_minutes(r.checkin_time)
                co = self._time_to_minutes(r.checkout_time)
                diff = co - ci
                if diff > 0:
                    total_hours += diff / 60.0

        # Standard work hours
        overtime = max(0.0, total_hours - 8.0)

        # Ledger entries
        entries = self._ledger_repo.get_by_date(date)
        penalty_total = sum(e.amount for e in entries if e.amount < 0)
        reward_total = sum(e.amount for e in entries if e.amount > 0)
        net = reward_total + penalty_total

        # Boyfriend promise
        promise_data = None
        promise = self._ledger_repo.get_promise(date)
        if promise:
            promise_data = PromiseDetail(
                reward_desc=promise.reward_desc,
                reward_qty=promise.reward_qty,
                fulfilled=promise.fulfilled == 1,
            )

        # Completed tasks
        from app.repositories.base import BaseRepo
        class TaskRepo(BaseRepo):
            def get_completed(self, date: str) -> list[str]:
                rows = self._fetch_all(
                    "SELECT content FROM task_items WHERE task_date = ? AND is_completed = 1 ORDER BY sort_order",
                    (date,),
                )
                return [r["content"] for r in rows]
        task_repo = TaskRepo()
        completed_tasks = task_repo.get_completed(date)

        threshold = 8.0
        if self._settings_repo:
            raw = self._settings_repo.get("boyfriend_hour_threshold")
            if raw:
                try:
                    threshold = float(raw)
                except ValueError:
                    pass

        return ReportData(
            date=date,
            is_shooting_day=is_shooting,
            periods=periods,
            penalty_total=penalty_total,
            reward_total=reward_total,
            net_amount=net,
            total_work_hours=total_hours,
            overtime_hours=overtime,
            promise=promise_data,
            completed_tasks=completed_tasks,
            encouragement=self._pick_encouragement(date),
            threshold_hours=threshold,
            shooting_content=shooting_content,
            shooting_location=shooting_location,
            shooting_reflection=shooting_reflection,
        )

    def generate_html(self, data: ReportData) -> str:
        """Jinja2 渲染 HTML。移动端不走此路径(战报用 Kivy FBO 长图导出),
        故惰性导入 jinja2, 避免安卓打包未含该依赖时在 import 阶段直接崩溃。"""
        from jinja2 import Template
        template_src = SHOOTING_REPORT_TEMPLATE if data.is_shooting_day else DAILY_REPORT_TEMPLATE
        return Template(template_src).render(data=data)

    def generate_and_save(self, date: str) -> str:
        """一键生成战报 HTML（截图逻辑在 Android 层实现）"""
        data = self.collect_data(date)
        html = self.generate_html(data)
        get_event_bus().publish(EventType.REPORT_GENERATED, {"date": date})
        return html

    def _on_day_closed(self, event_type: EventType, payload: dict[str, object]) -> None:
        date = str(payload.get("date", ""))
        if date:
            self.generate_and_save(date)

    def _read_user_encouragements(self) -> list[str]:
        """从 settings_repo 直接读 encouragements_user 并 JSON 解析；失败兜底为空"""
        if not self._settings_repo:
            return []
        raw = self._settings_repo.get("encouragements_user")
        if not raw:
            return []
        try:
            items = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if not isinstance(items, list):
            return []
        return [s for s in items if isinstance(s, str) and s.strip()]

    def _pick_encouragement(self, date: str) -> str:  # noqa: ARG002
        user_items = self._read_user_encouragements()
        pool = user_items if user_items else ENCOURAGEMENTS
        return random.choice(pool)

    @staticmethod
    def _time_to_minutes(time_str: str) -> int:
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])
