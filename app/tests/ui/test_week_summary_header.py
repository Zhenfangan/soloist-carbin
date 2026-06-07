"""测试 WeekSummaryHeader 布局修复 — 无文字重叠, 高度 72。"""
from app.ui.components.week_summary_header import WeekSummaryHeader


def test_height_is_72() -> None:
    """WeekSummaryHeader 默认高度应为 72 (从 96 缩减)。"""
    header = WeekSummaryHeader()
    assert header.height == 72, f"期望 height=72, 实际 {header.height}"


def test_labels_no_horizontal_overlap() -> None:
    """reward_label 右边界不应侵入 rate_label 左边界。"""
    header = WeekSummaryHeader()
    # 设一个合理的宽度来触发 _reposition_labels
    header.width = 420
    header.height = 72
    # 触发 reposition
    header._reposition_labels()

    reward_right = header._reward_label.x + header._reward_label.width
    rate_left = header._rate_label.x

    assert reward_right <= rate_left, (
        f"reward_label 右边界 {reward_right:.0f} 侵入 rate_label 左边界 {rate_left:.0f}"
    )
