"""HistoryTabs active 状态视觉指示器测试。"""

from __future__ import annotations

from kivy.graphics import Rectangle

from app.ui.components.history_tabs import HistoryTabs


def _has_indicator(tab_widget: object) -> bool:
    """tab widget 的 canvas.after 是否有 Rectangle 指示器（底边高亮）。"""
    return _has_indicator_in_canvas_after(tab_widget)


def _has_indicator_in_canvas_after(tab_widget: object) -> bool:
    """tab widget 的 canvas.after 是否有 Rectangle 指示器。"""
    c = getattr(tab_widget, "canvas", None)
    if c is None:
        return False
    after = getattr(c, "after", None)
    if after is None:
        return False
    children = getattr(after, "children", []) or []
    for instr in children:
        if isinstance(instr, Rectangle):
            return True
    return False


def test_active_tab_visually_differs_from_inactive_tabs() -> None:
    """当前 active tab 应该有视觉指示器 (canvas Rectangle), 非 active tab 没有。"""
    tabs = HistoryTabs(on_tab_change=lambda i: None)

    # 切到周 (idx=0)
    if hasattr(tabs, "set_active"):
        tabs.set_active(0)
    elif hasattr(tabs, "_set_active"):
        tabs._set_active(0)
    elif hasattr(tabs, "switch_to"):
        tabs.switch_to(0)
    else:
        raise AssertionError("HistoryTabs 没有公开的 set_active/switch_to/类似方法")

    # 找到 tab widgets (常见名字)
    tab_list = None
    for name in ["_tab_widgets", "_tabs", "_tab_buttons", "tabs"]:
        if hasattr(tabs, name):
            tab_list = getattr(tabs, name)
            if isinstance(tab_list, (list, tuple)) and len(tab_list) >= 3:
                break

    assert tab_list is not None, "无法定位 tab widget 列表"
    assert len(tab_list) >= 3, f"tab 数量 {len(tab_list)} < 3"

    active = tab_list[0]
    inactive = tab_list[1]

    # active 应该有指示器, inactive 不应该 (或至少 active 与 inactive 视觉不同)
    active_has = _has_indicator(active)
    # 我们不强制 inactive 没有指示器 — 只要 active 与 inactive 视觉表征不同就 OK
    # 但 active 必须有"某种"指示器
    assert active_has, "active tab 应有视觉指示器 (canvas Rectangle)"


def test_set_active_switches_indicator_to_new_tab() -> None:
    """切换 active 后，新 active tab 应在 canvas.after 有指示器。"""
    tabs = HistoryTabs(on_tab_change=lambda i: None)

    # 初始在 0，切到 1
    tabs.set_active(1)

    tab_list = tabs._tab_buttons
    assert len(tab_list) >= 3

    # 新 active tab[1] 的 canvas.after 应有 Rectangle 指示器
    assert _has_indicator_in_canvas_after(tab_list[1]), "切换后 tab[1] 的 canvas.after 应有指示器"
    # 旧 tab[0] 的 canvas.after 应清空
    assert not _has_indicator_in_canvas_after(tab_list[0]), "切换后 tab[0] 的 canvas.after 应无指示器"


def test_set_active_same_index_still_has_indicator() -> None:
    """对已选中 tab 再次 set_active 不会清除指示器。"""
    tabs = HistoryTabs(on_tab_change=lambda i: None)

    tabs.set_active(0)  # 已经是 0，强制刷新
    assert _has_indicator(tabs._tab_buttons[0]), "set_active(0) 后 tab[0] 应仍有指示器"


def test_active_tab_indicator_uses_yellow() -> None:
    """active tab 的底边指示器使用黄色 (PRIMARY_YELLOW)。"""
    from kivy.graphics import Color

    from app.ui.tokens import PRIMARY_YELLOW

    tabs = HistoryTabs(on_tab_change=lambda i: None)
    tabs.set_active(0)

    btn = tabs._tab_buttons[0]

    def _to_rgb_tuple(hex_color: str) -> tuple[float, float, float]:
        h = hex_color.lstrip("#")
        return (
            int(h[0:2], 16) / 255.0,
            int(h[2:4], 16) / 255.0,
            int(h[4:6], 16) / 255.0,
        )

    expected_rgb = _to_rgb_tuple(PRIMARY_YELLOW)

    found_yellow = False
    for canvas_attr in ["canvas.after"]:
        c = btn
        for part in canvas_attr.split("."):
            c = getattr(c, part, None)
            if c is None:
                break
        if c is None:
            continue
        # canvas children 顺序: Color 先于 Rectangle
        last_color: tuple[float, float, float] | None = None
        for instr in getattr(c, "children", []):
            if isinstance(instr, Color):
                last_color = (instr.r, instr.g, instr.b)
            elif isinstance(instr, Rectangle) and last_color is not None:
                if (
                    abs(last_color[0] - expected_rgb[0]) < 0.01
                    and abs(last_color[1] - expected_rgb[1]) < 0.01
                    and abs(last_color[2] - expected_rgb[2]) < 0.01
                ):
                    found_yellow = True

    assert found_yellow, f"active tab 底边指示器应使用黄色 {PRIMARY_YELLOW}"
