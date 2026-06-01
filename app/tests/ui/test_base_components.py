"""测试基础 UI 组件 — 每个组件的核心交互行为。"""

from __future__ import annotations

from app.ui.components.collapsible_group import CollapsibleGroup
from app.ui.components.mascot_bubble import MascotBubble
from app.ui.components.pixel_button import PixelButton
from app.ui.components.pixel_checkbox import PixelCheckbox
from app.ui.components.pixel_dialog import ConfirmDialog
from app.ui.components.pixel_input import PixelInput
from app.ui.components.pixel_stepper import PixelStepper


class TestPixelButton:
    """1.7〜1.8 PixelButton 测试"""

    def test_create_button_with_text(self) -> None:
        btn = PixelButton(text="签到")
        assert btn.text == "签到"
        assert btn.height == 48
        assert not btn._is_pressed

    def test_button_size_modes(self) -> None:
        normal = PixelButton(text="N", size_mode="normal")
        large = PixelButton(text="L", size_mode="large")
        small = PixelButton(text="S", size_mode="small")
        assert normal.height == 48
        assert large.height == 64
        assert small.height == 36

    def test_button_press_callback(self) -> None:
        pressed: list[str] = []

        def on_press() -> None:
            pressed.append("ok")

        btn = PixelButton(text="Test", on_press=on_press)
        btn.dispatch("on_press")
        assert pressed == ["ok"]

    def test_button_disabled_state(self) -> None:
        btn = PixelButton(text="Test", disabled=True)
        assert btn.disabled
        assert btn.opacity == 0.5

    def test_button_disabled_ignores_touch(self) -> None:
        """禁用的按钮不应在 touch_down 时改变状态。"""
        btn = PixelButton(text="Test", disabled=True)
        btn.size = (100, 48)
        btn.pos = (0, 0)
        # 直接验证: 禁用的按钮 on_touch_down 返回 False
        # 创建最小化的 mock touch
        class MockTouch:
            pos = (50, 24)
            is_mouse_scrolling = False
        btn.on_touch_down(MockTouch())
        assert not btn._is_pressed

    def test_set_color_updates_visual(self) -> None:
        btn = PixelButton(text="Test", color="#FF6B8A")
        assert btn._btn_color == "#FF6B8A"
        btn.set_color("#50E8B0")
        assert btn._btn_color == "#50E8B0"

    def test_default_color_is_primary_yellow(self) -> None:
        from app.ui.tokens import PRIMARY_YELLOW
        btn = PixelButton(text="Test")
        assert btn._btn_color == PRIMARY_YELLOW

    def test_redraw_draws_canvas_instructions(self) -> None:
        btn = PixelButton(text="Test")
        btn.size = (100, 48)
        btn.pos = (0, 0)
        btn._redraw()
        # canvas.before should be populated after redraw
        assert len(btn.canvas.before.children) > 0


class TestPixelInput:
    """1.9 PixelInput 测试"""

    def test_create_input_with_hint(self) -> None:
        inp = PixelInput(hint_text="请输入...")
        assert inp.hint_text == "请输入..."

    def test_value_property(self) -> None:
        inp = PixelInput(value="hello")
        assert inp.value == "hello"
        inp.value = "world"
        assert inp.value == "world"

    def test_password_mode(self) -> None:
        inp = PixelInput(password=True, value="secret")
        assert inp.password
        assert inp.text == "secret"

    def test_on_change_callback(self) -> None:
        changes: list[str] = []

        def on_change(v: str) -> None:
            changes.append(v)

        inp = PixelInput(on_change=on_change)
        # 手动触发 _on_text_change 来验证回调链路
        inp._on_text_change(inp, "hello")
        assert len(changes) > 0
        assert changes[0] == "hello"

    def test_inner_border_is_drawn(self) -> None:
        inp = PixelInput()
        inp.size = (200, 48)
        inp.pos = (0, 0)
        inp._redraw()
        assert len(inp.canvas.before.children) > 0


class TestConfirmDialog:
    """1.10 ConfirmDialog 测试"""

    def test_create_dialog(self) -> None:
        dlg = ConfirmDialog(title="测试", message="这是一条消息")
        assert dlg.auto_dismiss

    def test_confirm_callback(self) -> None:
        confirmed: list[str] = []

        def on_confirm() -> None:
            confirmed.append("confirmed")

        dlg = ConfirmDialog(title="T", message="M", on_confirm=on_confirm)
        dlg._handle_confirm()
        assert confirmed == ["confirmed"]

    def test_cancel_callback(self) -> None:
        cancelled: list[str] = []

        def on_cancel() -> None:
            cancelled.append("cancelled")

        dlg = ConfirmDialog(title="T", message="M", on_cancel=on_cancel)
        dlg._handle_cancel()
        assert cancelled == ["cancelled"]

    def test_dialog_widget_tree(self) -> None:
        """验证对话框有正确的 widget 树结构。"""
        dlg = ConfirmDialog(title="T", message="M")
        # 根节点下应该有内容
        assert len(dlg.children) > 0


class TestCollapsibleGroup:
    """1.11 CollapsibleGroup 测试"""

    def test_initial_state_expanded(self) -> None:
        group = CollapsibleGroup(title="设置组")
        assert not group.collapsed
        assert group._arrow_label.text == "▼"

    def test_initial_state_collapsed(self) -> None:
        group = CollapsibleGroup(title="设置组", collapsed=True)
        assert group.collapsed
        assert group._arrow_label.text == "▶"

    def test_toggle_expand_collapse(self) -> None:
        group = CollapsibleGroup(title="设置组")
        assert not group.collapsed
        group.toggle()
        assert group.collapsed
        group.toggle()  # type: ignore[unreachable]
        assert not group.collapsed

    def test_expand_method(self) -> None:
        group = CollapsibleGroup(title="设置组", collapsed=True)
        assert group.collapsed
        group.expand()
        assert not group.collapsed

    def test_collapse_method(self) -> None:
        group = CollapsibleGroup(title="设置组")
        assert not group.collapsed
        group.collapse()
        assert group.collapsed


class TestPixelCheckbox:
    """1.13 PixelCheckbox 测试"""

    def test_initial_state_unchecked(self) -> None:
        cb = PixelCheckbox(label="任务项")
        assert not cb.checked

    def test_initial_state_checked(self) -> None:
        cb = PixelCheckbox(checked=True, label="任务项")
        assert cb.checked

    def test_toggle(self) -> None:
        cb = PixelCheckbox(label="任务项")
        assert not cb.checked
        cb.toggle()
        assert cb.checked
        cb.toggle()  # type: ignore[unreachable]
        assert not cb.checked

    def test_on_toggle_callback(self) -> None:
        states: list[bool] = []

        def on_toggle(v: bool) -> None:
            states.append(v)

        cb = PixelCheckbox(label="任务项", on_toggle=on_toggle)
        cb.toggle()
        assert states == [True]
        cb.toggle()
        assert states == [True, False]


class TestPixelStepper:
    """1.14 PixelStepper 测试"""

    def test_initial_value(self) -> None:
        stepper = PixelStepper(value=5)
        assert stepper.value == 5

    def test_increment(self) -> None:
        stepper = PixelStepper(value=0)
        stepper._increment()
        assert stepper.value == 1

    def test_decrement(self) -> None:
        stepper = PixelStepper(value=5)
        stepper._decrement()
        assert stepper.value == 4

    def test_min_value_boundary(self) -> None:
        stepper = PixelStepper(value=0, min_value=0)
        stepper._decrement()
        assert stepper.value == 0

    def test_max_value_boundary(self) -> None:
        stepper = PixelStepper(value=99, max_value=99)
        stepper._increment()
        assert stepper.value == 99

    def test_on_change_callback(self) -> None:
        values: list[int] = []

        def on_change(v: int) -> None:
            values.append(v)

        stepper = PixelStepper(value=0, on_change=on_change)
        stepper._increment()
        assert values == [1]


class TestMascotBubble:
    """1.12 MascotBubble 测试"""

    def test_create_with_defaults(self) -> None:
        bubble = MascotBubble()
        assert bubble._mascot_id == "dudu"
        assert bubble._message == ""

    def test_set_message(self) -> None:
        bubble = MascotBubble(message="今天加油！")
        assert bubble.message == "今天加油！"
        assert bubble._bubble_label.text == "今天加油！"

    def test_message_setter(self) -> None:
        bubble = MascotBubble()
        bubble.message = "新消息"
        assert bubble._bubble_label.text == "新消息"

    def test_set_mascot(self) -> None:
        bubble = MascotBubble(mascot_id="dudu")
        bubble.set_mascot("wangzai")
        assert bubble._mascot_id == "wangzai"
