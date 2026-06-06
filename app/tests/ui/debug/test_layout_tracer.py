"""layout_tracer 单元测试 — 验证输出格式 + 递归。"""

from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button


class TestTraceLayout:
    """验证 trace_layout 返回字符串包含 widget 关键信息。"""

    def test_trace_single_widget_includes_class_pos_size(self) -> None:
        """单 widget 输出含类名、pos、size。"""
        from app.ui.debug.layout_tracer import trace_layout

        btn = Button(text="Hi")
        btn.size = (100, 48)
        btn.pos = (10, 20)

        output = trace_layout(btn)

        assert "Button" in output
        assert "pos=(10" in output or "pos=(10.0" in output
        assert "size=(100" in output or "size=(100.0" in output

    def test_trace_includes_size_hint_pos_hint(self) -> None:
        """输出含 size_hint 和 pos_hint。"""
        from app.ui.debug.layout_tracer import trace_layout

        btn = Button(text="Hi", size_hint=(None, None), pos_hint={"center_x": 0.5})

        output = trace_layout(btn)

        assert "size_hint" in output
        assert "pos_hint" in output

    def test_trace_recurses_into_children(self) -> None:
        """容器输出含其子 widget 的 trace。"""
        from app.ui.debug.layout_tracer import trace_layout

        layout = BoxLayout(orientation="vertical")
        child_a = Button(text="A")
        child_b = Button(text="B")
        layout.add_widget(child_a)
        layout.add_widget(child_b)

        output = trace_layout(layout)

        assert "BoxLayout" in output
        assert "Button" in output
        # 至少两个 Button 实例 (text A 和 B)
        assert output.count("Button") >= 2

    def test_trace_uses_indentation_for_depth(self) -> None:
        """嵌套 widget 使用缩进区分层级。"""
        from app.ui.debug.layout_tracer import trace_layout

        outer = BoxLayout()
        inner = BoxLayout()
        leaf = Button(text="leaf")
        inner.add_widget(leaf)
        outer.add_widget(inner)

        output = trace_layout(outer)
        lines = output.split("\n")

        # 找到 leaf 那一行
        leaf_lines = [line for line in lines if "leaf" in line]
        assert len(leaf_lines) >= 1
        # leaf 应缩进多于 outer (出现至少 2 层缩进, 每层用 2 个空格)
        assert leaf_lines[0].startswith("    "), (
            f"leaf 应缩进至少 4 空格, got: {leaf_lines[0]!r}"
        )

    def test_trace_accepts_label_parameter(self) -> None:
        """label 参数输出在头部。"""
        from app.ui.debug.layout_tracer import trace_layout

        btn = Button(text="x")
        output = trace_layout(btn, label="MyTrace")

        assert "MyTrace" in output

    def test_trace_handles_cycle_without_recursion_error(self) -> None:
        """循环引用不应导致 RecursionError, 应输出 <CYCLE -> ClassName>."""
        from app.ui.debug.layout_tracer import trace_layout

        outer = BoxLayout()
        inner = BoxLayout()
        outer.add_widget(inner)
        # 制造循环: 直接操纵 children list 绕过 Kivy add_widget 的 parent 递归
        # (add_widget 自身会在 cycle 时栈溢出, 我们只测 trace_layout 的健壮性)
        inner.children.append(outer)

        # 不应抛 RecursionError
        output = trace_layout(outer)

        assert "<CYCLE" in output
        assert "BoxLayout" in output
