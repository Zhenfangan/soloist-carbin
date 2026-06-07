"""测试 StatusBox status_w 有 text_size 防文字溢出。"""
from app.ui.components.status_box import StatusBox


def test_status_w_has_text_size_after_width_set() -> None:
    """实例化 StatusBox, 设 width=400, 校验 status_w text_size 被设置。"""
    box = StatusBox()
    box.width = 400
    # 触发 _redraw / _update_status_text_sizes
    box._update_status_text_sizes()

    # 检查每个 period 行的 status_w
    for row_info in box._period_rows:
        status_w = row_info["status_w"]
        assert status_w.text_size[0] > 0, (
            f"status_w.text_size 未设置: {status_w.text_size}"
        )


def test_row_height_is_28() -> None:
    """每行高度应为 28 (从 24 增加)。"""
    box = StatusBox()
    for row_info in box._period_rows:
        row = row_info["row"]
        assert row.height == 28, f"期望 row height=28, 实际 {row.height}"
