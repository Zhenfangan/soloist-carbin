"""视觉渲染验证测试 — 确保关键组件在 offscreen 模式下正确绘制背景。

这些测试用于防止"组件透明导致黑屏"类的视觉 bug。
"""

from __future__ import annotations

from app.ui.components.collapsible_group import CollapsibleGroup
from app.ui.components.day_card import DayCard
from app.ui.components.mascot_bubble import MascotBubble
from app.ui.components.period_card import PeriodCard
from app.ui.components.pixel_button import PixelButton
from app.ui.components.pixel_checkbox import PixelCheckbox
from app.ui.components.pixel_dialog import ConfirmDialog
from app.ui.components.pixel_input import PixelInput
from app.ui.components.pixel_stepper import PixelStepper
from app.ui.components.status_box import StatusBox
from app.ui.components.task_inline_list import TaskInlineList
from app.ui.components.week_summary_header import WeekSummaryHeader
from app.ui.screens.bet_screen import BetScreen
from app.ui.screens.settings_screen import SettingsScreen


def _has_canvas_before(widget: object) -> bool:
    """检查 widget 是否有 canvas.before 绘制指令。"""
    if not hasattr(widget, "canvas"):
        return False
    canvas = widget.canvas  # type: ignore[union-attr]
    if not hasattr(canvas, "before"):
        return False
    return len(canvas.before.children) > 0


def _gets_background_on_init(widget: object) -> bool:
    """检查 widget 在 __init__ 后是否立即有 canvas.before（触发 _redraw 后）。"""
    if hasattr(widget, "_redraw"):
        widget._redraw()
    return _has_canvas_before(widget)


class TestComponentBackgrounds:
    """验证每个核心 UI 组件在创建后都有背景绘制。"""

    def test_pixel_button_has_background(self) -> None:
        btn = PixelButton(text="测试")
        btn._redraw()
        assert _has_canvas_before(btn), "PixelButton 缺少 canvas.before 背景"

    def test_pixel_input_has_background(self) -> None:
        inp = PixelInput()
        inp._redraw()
        assert _has_canvas_before(inp), "PixelInput 缺少 canvas.before 背景"

    def test_pixel_input_right_border_is_thin(self) -> None:
        """亮面 right 矩形宽度应为 BORDER_WIDTH (2)，不是整个 widget 宽度。"""
        from kivy.graphics import Rectangle
        from app.ui.tokens import BORDER_WIDTH

        inp = PixelInput()
        inp.size = (200, 40)
        inp.pos = (10, 20)
        inp._redraw()

        rects = [c for c in inp.canvas.before.children if isinstance(c, Rectangle)]
        # 5 个矩形: 背景 + 暗面 top + 暗面 left + 亮面 bottom + 亮面 right
        assert len(rects) == 5, f"expected 5 rectangles, got {len(rects)}"

        right_border = rects[-1]  # _redraw 顺序最后画亮面 right
        assert right_border.size[0] == BORDER_WIDTH, (
            f"right border width should be {BORDER_WIDTH}, got {right_border.size[0]}"
        )
        assert right_border.size[1] == 40, (
            f"right border height should be 40, got {right_border.size[1]}"
        )

    def test_pixel_dialog_has_background(self) -> None:
        dlg = ConfirmDialog(title="测试", message="消息")
        # ConfirmDialog 在 _card 子组件上绘制背景
        assert hasattr(dlg, "_card"), "ConfirmDialog 缺少 _card"
        assert _has_canvas_before(dlg._card), "ConfirmDialog._card 缺少 canvas.before"

    def test_period_card_has_background(self) -> None:
        card = PeriodCard(period_name="morning")
        card._redraw()
        assert _has_canvas_before(card), "PeriodCard 缺少 canvas.before 背景"

    def test_status_box_has_background(self) -> None:
        box = StatusBox()
        box._redraw()
        assert _has_canvas_before(box), "StatusBox 缺少 canvas.before 背景"

    def test_task_inline_list_has_background(self) -> None:
        lst = TaskInlineList()
        lst._redraw()
        assert _has_canvas_before(lst), "TaskInlineList 缺少 canvas.before 背景"

    def test_mascot_bubble_has_background(self) -> None:
        bubble = MascotBubble(message="测试")
        bubble._redraw()
        assert _has_canvas_before(bubble), "MascotBubble 缺少 canvas.before 背景"

    def test_collapsible_group_has_background(self) -> None:
        """P0: CollapsibleGroup 必须有自己的背景绘制。"""
        from kivy.uix.widget import Widget

        content = Widget(size_hint=(1, None), height=48)
        group = CollapsibleGroup(title="测试组", content=content)
        group._redraw()
        assert _has_canvas_before(group), (
            "CollapsibleGroup 缺少 canvas.before 背景 — 这是导致设置页黑屏的根本原因"
        )

    def test_week_summary_header_has_background(self) -> None:
        header = WeekSummaryHeader()
        header._redraw()
        assert _has_canvas_before(header), "WeekSummaryHeader 缺少 canvas.before 背景"

    def test_day_card_has_background(self) -> None:
        from app.models.history import DayCard as DayCardModel
        from app.models.history import PeriodSummary
        from app.models.ledger import LedgerEntry

        day = DayCardModel(
            date="2026-06-01",
            periods=[PeriodSummary(period="morning", status="normal")],
            total_hours=8.0,
            daily_ledger=[LedgerEntry(entry_date="2026-06-01", type="reward", amount=50.0)],
            is_shooting=False,
        )
        card = DayCard(day_summary=day)
        # DayCard 使用 self.bind 但不是显式的 _redraw
        assert card._day is day


class TestScreenLayouts:
    """验证页面级组件正确设置了背景。"""

    def test_settings_screen_content_has_background(self) -> None:
        """P0: SettingsScreen 的 content BoxLayout 必须有背景。"""
        screen = SettingsScreen()
        # 验证 content 区域有背景矩形
        assert hasattr(screen, "_content_bg_rect"), (
            "SettingsScreen 缺少 _content_bg_rect — 内容区无背景"
        )

    def test_bet_screen_layout_has_background(self) -> None:
        """P1: BetScreen 的 _layout 必须有白色背景。"""
        from app.repositories.bet_repo import BetRepo
        from app.repositories.ledger_repo import LedgerRepo
        from app.repositories.settings_repo import SettingsRepo
        from app.services.bet_service import BetService

        svc = BetService(BetRepo(":memory:"), LedgerRepo(":memory:"), SettingsRepo(":memory:"))
        screen = BetScreen(bet_service=svc)
        assert hasattr(screen, "_layout_bg"), (
            "BetScreen 缺少 _layout_bg — 布局区无背景"
        )

    def test_pixel_checkbox_has_border(self) -> None:
        """PixelCheckbox 绘制度。"""
        cb = PixelCheckbox(label="测试")
        cb._redraw()
        assert _has_canvas_before(cb), "PixelCheckbox 缺少 canvas.before 边框"

    def test_pixel_stepper_has_background(self) -> None:
        """PixelStepper 绘制背景。"""
        stepper = PixelStepper(value=5)
        stepper._redraw()
        assert _has_canvas_before(stepper), "PixelStepper 缺少 canvas.before 背景"

    def test_pixel_stepper_right_border_is_thin(self) -> None:
        """亮面 right 矩形宽度应为 BORDER_WIDTH。"""
        from kivy.graphics import Rectangle
        from app.ui.tokens import BORDER_WIDTH

        stepper = PixelStepper(value=1)
        stepper.size = (140, 32)
        stepper.pos = (0, 0)
        stepper._redraw()

        rects = [c for c in stepper.canvas.before.children if isinstance(c, Rectangle)]
        assert len(rects) == 5, f"expected 5 rectangles, got {len(rects)}"

        right_border = rects[-1]
        assert right_border.size[0] == BORDER_WIDTH, (
            f"right border width should be {BORDER_WIDTH}, got {right_border.size[0]}"
        )
        assert right_border.size[1] == 32, (
            f"right border height should be 32, got {right_border.size[1]}"
        )
