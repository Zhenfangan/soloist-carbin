"""BetTaskItem 渲染回归测试 — 验证 task_desc 在 widget 中作为 Label text 可见。"""

from __future__ import annotations

from kivy.uix.label import Label

from app.models.ledger import BetTask
from app.ui.components.bet_task_item import BetTaskItem


def test_bet_task_item_displays_task_desc() -> None:
    """BetTaskItem 应在某个 Label.text 里包含 task_desc 值。"""
    task = BetTask(
        week_start="2026-06-01",
        task_desc="测试任务",
        target_qty=3,
        current_qty=1,
        is_completed=0,
        id=42,
    )
    item = BetTaskItem(task=task)

    # 递归收集所有 Label
    def collect_labels(widget: object) -> list[Label]:
        labels = [widget] if isinstance(widget, Label) else []
        for child in getattr(widget, "children", []):
            labels.extend(collect_labels(child))
        return labels

    labels = collect_labels(item)
    desc_label = next((l for l in labels if "测试任务" in l.text), None)
    assert desc_label is not None, (
        f"未找到包含 '测试任务' 的 Label, 所有 Label texts: "
        f"{[l.text for l in labels]}"
    )
