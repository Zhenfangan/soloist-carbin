"""测试 WeekSummaryHeader 布局修复 — 无文字重叠, 高度 144。"""
from app.ui.components.week_summary_header import WeekSummaryHeader


def test_height_is_144() -> None:
    """WeekSummaryHeader 默认高度应为 144。"""
    header = WeekSummaryHeader()
    assert header.height == 144, f"期望 height=144, 实际 {header.height}"


def test_labels_no_vertical_overlap() -> None:
    """三行文字垂直堆叠,不应互相重叠。
    布局: completed_label(上) > rate_label(中) > reward_label(下)。
    """
    header = WeekSummaryHeader()
    header.width = 420
    header.height = 144
    header._reposition_labels()

    # completed_label 在 rate_label 上方,不重叠
    assert header._completed_label.y >= header._rate_label.y + header._rate_label.height, (
        f"completed_label 底部 {header._completed_label.y:.0f} < "
        f"rate_label 顶部 {header._rate_label.y + header._rate_label.height:.0f}"
    )
    # rate_label 在 reward_label 上方,不重叠
    assert header._rate_label.y >= header._reward_label.y + header._reward_label.height, (
        f"rate_label 底部 {header._rate_label.y:.0f} < "
        f"reward_label 顶部 {header._reward_label.y + header._reward_label.height:.0f}"
    )
