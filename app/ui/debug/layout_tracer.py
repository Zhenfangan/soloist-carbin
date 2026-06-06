"""Widget 树打印工具 — 递归输出 widget 的 pos / size / size_hint / pos_hint。

用法:
    from kivy.app import App
    from app.ui.debug.layout_tracer import trace_layout

    root = App.get_running_app().root
    Logger.info(trace_layout(root, label="dev_panel dump"))

输出示例 (缩进在 `[LAY]` 之前, 便于按缩进定位深度):
    [LAY] dev_panel dump
    [LAY] BoxLayout: pos=(0.0, 0.0) size=(420, 750) size_hint=(1, None) pos_hint={}
      [LAY] WeekSummaryHeader: pos=(8.0, 670.0) size=(404, 60) size_hint=(1, None) pos_hint={}
        [LAY] Label: pos=(20, 690) size=(384, 40) size_hint=(None, None) pos_hint={'center_x': 0.5}
"""

from __future__ import annotations

from typing import Any


def trace_layout(widget: Any, label: str = "") -> str:
    """递归打印 widget 树, 返回多行字符串。

    Args:
        widget: Kivy widget 根节点。
        label: 可选标签, 输出在头部。

    Returns:
        多行字符串, 每行 `[LAY]` 前缀, 含类名 / pos / size / size_hint / pos_hint。
        子 widget 缩进 2 空格 (按嵌套深度递增)。
    """
    lines: list[str] = []
    if label:
        lines.append(f"[LAY] {label}")
    _trace_recursive(widget, depth=0, lines=lines)
    return "\n".join(lines)


def _trace_recursive(
    widget: Any,
    depth: int,
    lines: list[str],
    visited: set[int] | None = None,
) -> None:
    """内部递归。每个 widget 一行, children 缩进 +2 空格。visited 用 id() 防 cycle。"""
    if visited is None:
        visited = set()
    if id(widget) in visited:
        indent = "  " * depth
        cls_name = type(widget).__name__
        lines.append(f"{indent}[LAY] <CYCLE -> {cls_name}>")
        return
    visited.add(id(widget))

    indent = "  " * depth
    cls_name = type(widget).__name__
    # Kivy 的 pos/size 是 ObservableList, repr 形如 [10, 20]。
    # 转 tuple 让输出更紧凑、也兼容 `pos=(...)` 风格断言。
    pos = _to_tuple(getattr(widget, "pos", None))
    size = _to_tuple(getattr(widget, "size", None))
    size_hint = _to_tuple(getattr(widget, "size_hint", None))
    pos_hint = getattr(widget, "pos_hint", None)

    # 若有 text 属性 (Label/Button 等), 附在末尾, 便于在 trace 中定位具体节点。
    text = getattr(widget, "text", None)
    text_suffix = f" text={text!r}" if text else ""

    lines.append(
        f"{indent}[LAY] {cls_name}: pos={pos} size={size} "
        f"size_hint={size_hint} pos_hint={pos_hint}{text_suffix}"
    )

    children = getattr(widget, "children", None)
    if children:
        # Kivy children 列表是逆序的 (后加的在前), 倒一下保持视觉顺序
        for child in reversed(children):
            _trace_recursive(child, depth + 1, lines, visited)


def _to_tuple(value: Any) -> Any:
    """把 Kivy 的 ObservableList 转成 tuple, 其它类型原样返回。"""
    if isinstance(value, list):
        return tuple(value)
    return value
