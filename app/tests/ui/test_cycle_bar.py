"""CycleBar — 周期历史条颜色应反映该周期是否被罚款。"""

from __future__ import annotations

from app.models.history import CycleSummary
from app.ui.components.cycle_bar import _CYCLE_GREEN, _CYCLE_RED, CycleBar


def _cycle(penalty: float = 0.0, net: float = 100.0, other_income: float = 0.0) -> CycleSummary:
    return CycleSummary(
        week_start="2026-06-01", week_end="2026-06-07", status="settled",
        total_tasks=3, completed_tasks=3, penalty=penalty, net=net,
        other_income=other_income,
    )


def test_no_penalty_cycle_uses_green_dots() -> None:
    bar = CycleBar(cycle=_cycle(penalty=0.0))
    assert bar._dot_color() == _CYCLE_GREEN


def test_penalized_cycle_uses_red_dots() -> None:
    """真机反馈: 明明这周被罚款了, 历史页却还显示 7 个绿格子(正常完成的样子)。

    根因: CycleBar._redraw() 画 7 个格子的颜色是硬编码的 _CYCLE_GREEN,
    完全没看 cycle.penalty, 无论是否罚款都画绿色。
    """
    bar = CycleBar(cycle=_cycle(penalty=50.0))
    assert bar._dot_color() == _CYCLE_RED


def test_other_income_shows_combined_total_line() -> None:
    """周期有其他收入(如拍摄日奖励)时, 显示一行"对赌+其他收入"的合计,
    不需要用户自己心算两个数字。"""
    bar = CycleBar(cycle=_cycle(net=50.0, other_income=30.0))
    assert bar._total_label.opacity == 1
    assert "80" in bar._total_label.text


def test_no_other_income_hides_total_line() -> None:
    """没有其他收入时不显示合计行, 避免多余文字(和 net 数字重复)。"""
    bar = CycleBar(cycle=_cycle(net=50.0, other_income=0.0))
    assert bar._total_label.opacity == 0


def test_negative_combined_total_shows_correct_sign() -> None:
    bar = CycleBar(cycle=_cycle(net=-50.0, other_income=30.0))
    assert bar._total_label.opacity == 1
    assert "-20" in bar._total_label.text
