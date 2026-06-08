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


def test_long_status_text_does_not_overflow_row() -> None:
    """长状态文字应该被 shorten 截断, text_size 同步 width-4 buffer。"""
    from app.ui.components.status_box import StatusBox

    box = StatusBox()
    box.size = (380, 130)
    box.do_layout()

    status_w = box._status_widgets["evening"]
    status_w.text = "正常签到 16:12:41 / 签退 12:42 / 拍摄完成"

    # 显式设置 width 触发 _bind_text_size
    status_w.width = 280

    # 验证 bind 把 text_size[0] 设成了 width - 4 (= 276) 而不是 None / width
    assert status_w.text_size[0] == 276, (
        f"text_size[0] 应为 width-4=276, 实际 {status_w.text_size[0]}"
    )

    # 验证 shorten 配置
    assert status_w.shorten is True
    assert status_w.shorten_from == "right"


def test_each_row_has_independent_bind() -> None:
    """每个 row 的 status_w 应独立响应 width 变化。"""
    from app.ui.components.status_box import StatusBox

    box = StatusBox()
    morning_w = box._status_widgets["morning"]
    evening_w = box._status_widgets["evening"]

    # 使用与默认值不同的 width 确保 bind 触发 (Kivy 只在值变化时触发)
    morning_w.width = 200
    evening_w.width = 150

    assert morning_w.text_size[0] == 196, "morning text_size 应基于自身 width"
    assert evening_w.text_size[0] == 146, "evening text_size 应基于自身 width"
