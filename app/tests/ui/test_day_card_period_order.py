"""DayCard 时段渲染顺序回归测试 — 必须 上午 → 下午 → 晚上。"""

from __future__ import annotations

from app.models.history import DayCard as DayCardModel, PeriodSummary
from app.ui.components.day_card import DayCard


def test_day_card_renders_periods_in_fixed_order() -> None:
    """无论输入数据顺序如何, 渲染必须按 上午→下午→晚上。"""
    # 故意打乱顺序: evening → morning → afternoon
    model = DayCardModel(
        date="2026-06-04",
        periods=[
            PeriodSummary(period="evening", status="normal"),
            PeriodSummary(period="morning", status="normal"),
            PeriodSummary(period="afternoon", status="late"),
        ],
    )
    card = DayCard(day_summary=model)

    # _status_label.text 包含全部时段文字, 按渲染顺序拼接
    status_text = card._status_label.text

    morning_idx = status_text.find("上午")
    afternoon_idx = status_text.find("下午")
    evening_idx = status_text.find("晚上")

    assert morning_idx != -1, f"未找到上午, 实际 text: {status_text!r}"
    assert afternoon_idx != -1, f"未找到下午, 实际 text: {status_text!r}"
    assert evening_idx != -1, f"未找到晚上, 实际 text: {status_text!r}"
    assert morning_idx < afternoon_idx < evening_idx, (
        f"顺序错乱: 上午@{morning_idx} 下午@{afternoon_idx} 晚上@{evening_idx}, "
        f"全部 text: {status_text!r}"
    )
