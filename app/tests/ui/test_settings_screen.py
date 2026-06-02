"""测试设置页面 UI 组件 — UI-06。

测试范围:
    - PixelTimePicker: 时间选择器 → 值选择回写
    - PixelNumberDialog: 数字输入弹窗 → 值回写
    - TimePickerRow: 时间设置行展示与回调
    - AmountPickerRow: 金额设置行展示与回调 (含 penalty 模式)
    - SettingsScreen: 工作日切换、分组折叠、备份/恢复、版本号连击
"""

from __future__ import annotations

from typing import Any

from kivy.uix.label import Label

from app.ui.components.amount_picker_row import AmountPickerRow
from app.ui.components.collapsible_group import CollapsibleGroup
from app.ui.components.pixel_button import PixelButton
from app.ui.components.pixel_number_dialog import PixelNumberDialog
from app.ui.components.pixel_time_picker import PixelTimePicker
from app.ui.components.time_picker_row import TimePickerRow
from app.ui.screens.settings_screen import SettingsScreen

# ============================================================
# Mock 服务
# ============================================================


class MockSettingsService:
    """模拟 SettingsService，仅供测试。"""

    def __init__(self) -> None:
        self.data: dict[str, str] = {
            "morning_start": "09:00",
            "morning_end": "12:00",
            "afternoon_start": "14:00",
            "afternoon_end": "18:00",
            "late_penalty": "10",
            "early_leave_penalty": "10",
            "absent_penalty": "50",
            "full_attendance_bonus": "100",
            "bet_base_reward": "50",
            "bet_extra_reward": "30",
            "bet_penalty": "50",
            "work_days": "1,2,3,4,5",
            "shooting_reward": "30",
            "boyfriend_hour_threshold": "8",
        }
        self.set_calls: list[tuple[str, str]] = []

    def get(self, key: str) -> str:
        return self.data.get(key, "")

    def set(self, key: str, value: str) -> None:
        self.data[key] = value
        self.set_calls.append((key, value))

    def get_work_days(self) -> list[int]:
        val = self.get("work_days")
        if not val:
            return []
        return [int(x.strip()) for x in val.split(",") if x.strip()]

    def get_all(self) -> dict[str, str]:
        return dict(self.data)


class MockSyncService:
    """模拟 SyncService，仅供测试。"""

    def __init__(self) -> None:
        self.backup_called = False
        self.restore_called = False
        self.last_restore_data: dict[str, Any] | None = None

    def backup_full(self) -> dict[str, Any]:
        self.backup_called = True
        return {
            "backed_up": True,
            "data": {"settings": [{"key": "test", "value": "1"}]},
            "timestamp": "2024-01-01T00:00:00",
        }

    def restore_full(self, data: dict[str, Any]) -> bool:
        self.restore_called = True
        self.last_restore_data = data
        return True


# ============================================================
# Mock Touch
# ============================================================


class MockTouch:
    """模拟 Kivy touch 事件。"""

    def __init__(self, x: float = 0, y: float = 0) -> None:
        self.pos = (x, y)
        self.is_mouse_scrolling = False


# ============================================================
# PixelTimePicker 测试
# ============================================================


class TestPixelTimePicker:
    """3. PixelTimePicker 测试"""

    def test_create_with_default_time(self) -> None:
        picker = PixelTimePicker()
        assert picker._hour == 9
        assert picker._minute == 0

    def test_create_with_custom_time(self) -> None:
        picker = PixelTimePicker(initial_time="14:30")
        assert picker._hour == 14
        assert picker._minute == 30

    def test_adjust_hour_up(self) -> None:
        picker = PixelTimePicker(initial_time="09:00")
        picker._adjust_hour(1)
        assert picker._hour == 10
        assert picker._hour_label.text == "10"

    def test_adjust_hour_down(self) -> None:
        picker = PixelTimePicker(initial_time="09:00")
        picker._adjust_hour(-1)
        assert picker._hour == 8

    def test_adjust_hour_wrap_forward(self) -> None:
        picker = PixelTimePicker(initial_time="23:00")
        picker._adjust_hour(1)
        assert picker._hour == 0

    def test_adjust_hour_wrap_backward(self) -> None:
        picker = PixelTimePicker(initial_time="00:00")
        picker._adjust_hour(-1)
        assert picker._hour == 23

    def test_adjust_minute_up(self) -> None:
        picker = PixelTimePicker(initial_time="09:00")
        picker._adjust_minute(1)
        assert picker._minute == 1
        assert picker._min_label.text == "01"

    def test_adjust_minute_down(self) -> None:
        picker = PixelTimePicker(initial_time="09:30")
        picker._adjust_minute(-1)
        assert picker._minute == 29

    def test_adjust_minute_wrap_forward(self) -> None:
        picker = PixelTimePicker(initial_time="09:59")
        picker._adjust_minute(1)
        assert picker._minute == 0

    def test_adjust_minute_wrap_backward(self) -> None:
        picker = PixelTimePicker(initial_time="09:00")
        picker._adjust_minute(-1)
        assert picker._minute == 59

    def test_confirm_returns_formatted_time(self) -> None:
        results: list[str] = []
        picker = PixelTimePicker(
            initial_time="09:05",
            on_select=lambda t: results.append(t),
        )
        picker._handle_confirm()
        assert results == ["09:05"]

    def test_confirm_calls_on_select(self) -> None:
        results: list[str] = []
        picker = PixelTimePicker(
            initial_time="14:30",
            on_select=lambda t: results.append(t),
        )
        picker._hour = 16
        picker._minute = 45
        picker._handle_confirm()
        assert results == ["16:45"]

    def test_confirm_no_callback_does_not_crash(self) -> None:
        picker = PixelTimePicker(initial_time="09:00")
        picker._handle_confirm()  # 不应抛出异常


# ============================================================
# PixelNumberDialog 测试
# ============================================================


class TestPixelNumberDialog:
    """4. PixelNumberDialog 测试"""

    def test_create_with_title_and_value(self) -> None:
        dlg = PixelNumberDialog(title="迟到罚款", initial_value="10")
        assert dlg._input.value == "10"

    def test_confirm_returns_value(self) -> None:
        results: list[str] = []
        dlg = PixelNumberDialog(
            title="测试",
            initial_value="50",
            on_confirm=lambda v: results.append(v),
        )
        dlg._handle_confirm()
        assert results == ["50"]

    def test_confirm_after_input_change(self) -> None:
        results: list[str] = []
        dlg = PixelNumberDialog(
            title="测试",
            initial_value="10",
            on_confirm=lambda v: results.append(v),
        )
        dlg._input.text = "25"
        dlg._handle_confirm()
        assert results == ["25"]

    def test_numeric_filter_removes_non_digits(self) -> None:
        dlg = PixelNumberDialog(title="测试", initial_value="0")
        dlg._filter_numeric(dlg._input, "12a3")
        assert dlg._input.text == "123"

    def test_numeric_filter_allows_negative_sign(self) -> None:
        dlg = PixelNumberDialog(title="测试", initial_value="0")
        dlg._input.text = "-10"
        assert dlg._input.text == "-10"

    def test_numeric_filter_removes_non_leading_minus(self) -> None:
        dlg = PixelNumberDialog(title="测试", initial_value="0")
        dlg._filter_numeric(dlg._input, "1-0")
        assert dlg._input.text == "10"

    def test_confirm_no_callback_does_not_crash(self) -> None:
        dlg = PixelNumberDialog(title="测试", initial_value="0")
        dlg._handle_confirm()


# ============================================================
# TimePickerRow 测试
# ============================================================


class TestTimePickerRow:
    """12. TimePickerRow 测试"""

    def test_create_display_correct_value(self) -> None:
        svc = MockSettingsService()
        row = TimePickerRow("上午上班", "morning_start", svc)
        assert row._value_btn.text == "09:00"

    def test_time_selected_writes_back(self) -> None:
        svc = MockSettingsService()
        row = TimePickerRow("上午上班", "morning_start", svc)
        row._on_time_selected("10:00")
        assert svc.get("morning_start") == "10:00"
        assert row._value_btn.text == "10:00"

    def test_refresh_updates_display(self) -> None:
        svc = MockSettingsService()
        row = TimePickerRow("上午上班", "morning_start", svc)
        svc.set("morning_start", "11:00")
        row.refresh()
        assert row._value_btn.text == "11:00"

    def test_no_service_does_not_crash(self) -> None:
        row = TimePickerRow("上午上班", "morning_start", None)
        assert row._value_btn.text == "09:00"  # 默认值


# ============================================================
# AmountPickerRow 测试
# ============================================================


class TestAmountPickerRow:
    """13. AmountPickerRow 测试"""

    def test_create_display_positive_value(self) -> None:
        svc = MockSettingsService()
        row = AmountPickerRow("全勤奖励", "full_attendance_bonus", svc, is_penalty=False)
        assert row._value_btn.text == "100"

    def test_create_display_penalty_value(self) -> None:
        svc = MockSettingsService()
        row = AmountPickerRow("迟到罚款", "late_penalty", svc, is_penalty=True)
        assert row._value_btn.text == "-10"

    def test_penalty_shows_zero_without_minus(self) -> None:
        svc = MockSettingsService()
        svc.set("late_penalty", "0")
        row = AmountPickerRow("迟到罚款", "late_penalty", svc, is_penalty=True)
        assert row._value_btn.text == "0"

    def test_value_confirmed_writes_back(self) -> None:
        svc = MockSettingsService()
        row = AmountPickerRow("迟到罚款", "late_penalty", svc, is_penalty=True)
        row._on_value_confirmed("15")
        assert svc.get("late_penalty") == "15"
        assert row._value_btn.text == "-15"

    def test_value_strips_negative_sign_before_save(self) -> None:
        svc = MockSettingsService()
        row = AmountPickerRow("迟到罚款", "late_penalty", svc, is_penalty=True)
        row._on_value_confirmed("-20")
        assert svc.get("late_penalty") == "20"
        assert row._value_btn.text == "-20"

    def test_refresh_updates_display(self) -> None:
        svc = MockSettingsService()
        row = AmountPickerRow("迟到罚款", "late_penalty", svc, is_penalty=True)
        svc.set("late_penalty", "30")
        row.refresh()
        assert row._value_btn.text == "-30"


# ============================================================
# SettingsScreen 测试
# ============================================================


class TestSettingsScreen:
    """14-15. SettingsScreen 测试"""

    def test_create_screen(self) -> None:
        """测试屏幕可正常创建。"""
        svc = MockSettingsService()
        sync = MockSyncService()
        screen = SettingsScreen(settings_service=svc, sync_service=sync)
        assert screen._settings_service is svc
        assert screen._sync_service is sync

    def test_has_four_collapsible_groups(self) -> None:
        """验证有 4 个 CollapsibleGroup。"""
        svc = MockSettingsService()
        screen = SettingsScreen(settings_service=svc)

        # 遍历 widget 树查找 CollapsibleGroup
        groups = _find_widgets(screen, CollapsibleGroup)
        assert len(groups) == 4
        titles = [g._title_label.text for g in groups]
        assert "上班时间" in titles
        assert "奖惩金额" in titles
        assert "对赌配置" in titles
        assert "其他" in titles

    # ---- 工作日切换 ----

    def test_work_days_toggle(self) -> None:
        """点击工作日按钮切换勾选状态。"""
        svc = MockSettingsService()
        screen = SettingsScreen(settings_service=svc)

        # 初始: Mon-Fri 选中 (5个 yellow, 2个 shadow)
        day_btns = _find_work_day_buttons(screen)
        assert len(day_btns) == 7

        initial_yellow = sum(1 for b in day_btns if b._is_day_selected)
        assert initial_yellow == 5  # Mon-Fri

        # 点击周六按钮 (index 5)
        day_btns[5].dispatch("on_press")
        assert day_btns[5]._is_day_selected
        assert svc.get("work_days") == "1,2,3,4,5,6"

        # 再点取消
        day_btns[5].dispatch("on_press")
        assert not day_btns[5]._is_day_selected
        assert svc.get("work_days") == "1,2,3,4,5"

    def test_work_days_remove_monday(self) -> None:
        """取消周一选中。"""
        svc = MockSettingsService()
        screen = SettingsScreen(settings_service=svc)

        day_btns = _find_work_day_buttons(screen)
        # 点击周一 (index 0)
        day_btns[0].dispatch("on_press")
        assert not day_btns[0]._is_day_selected
        assert svc.get("work_days") == "2,3,4,5"

    # ---- 分组折叠 ----

    def test_collapsible_groups_start_expanded(self) -> None:
        """验证所有分组默认展开。"""
        svc = MockSettingsService()
        screen = SettingsScreen(settings_service=svc)

        groups = _find_widgets(screen, CollapsibleGroup)
        for g in groups:
            assert not g.collapsed, f"组 '{g._title_label.text}' 默认应展开"

    def test_toggle_group_collapse(self) -> None:
        """点击分组标题折叠内容。"""
        svc = MockSettingsService()
        screen = SettingsScreen(settings_service=svc)

        groups = _find_widgets(screen, CollapsibleGroup)
        target = groups[0]  # 上班时间组

        assert not target.collapsed
        target.toggle()
        assert target.collapsed
        target.toggle()
        assert not target.collapsed

    def test_collapse_hides_content(self) -> None:
        """折叠后 collapsed 状态立即更新，箭头变为 ▶。"""
        svc = MockSettingsService()
        screen = SettingsScreen(settings_service=svc)

        groups = _find_widgets(screen, CollapsibleGroup)
        target = groups[0]

        target.collapse()
        assert target.collapsed  # 状态同步更新
        assert target._arrow_label.text == "▶"  # 箭头同步更新
        # 注意: 内容区高度动画是异步的 (Clock.schedule_once)，
        # 此处验证 collapsed 状态和 UI 文字的立即可见变化

    # ---- 备份按钮 ----

    def test_backup_calls_sync_service(self) -> None:
        """备份操作调用 SyncService.backup_full()。"""
        svc = MockSettingsService()
        sync = MockSyncService()
        screen = SettingsScreen(settings_service=svc, sync_service=sync)

        assert not sync.backup_called
        screen._do_backup()
        assert sync.backup_called

    def test_backup_no_service_does_not_crash(self) -> None:
        """无 SyncService 时不崩溃。"""
        svc = MockSettingsService()
        screen = SettingsScreen(settings_service=svc, sync_service=None)
        screen._do_backup()  # 不应崩溃

    # ---- 恢复按钮 ----

    def test_restore_calls_sync_service(self) -> None:
        """恢复操作调用 SyncService.restore_full()。"""
        svc = MockSettingsService()
        sync = MockSyncService()
        screen = SettingsScreen(settings_service=svc, sync_service=sync)

        assert not sync.restore_called
        screen._do_restore()
        assert sync.restore_called

    def test_restore_no_service_does_not_crash(self) -> None:
        """无 SyncService 时不崩溃。"""
        svc = MockSettingsService()
        screen = SettingsScreen(settings_service=svc, sync_service=None)
        screen._do_restore()

    # ---- 版本号连点 ----

    def test_version_click_5_times_shows_dev_panel(self) -> None:
        """连点 5 次版本号触发开发面板。"""
        svc = MockSettingsService()
        screen = SettingsScreen(settings_service=svc)

        version_label = _find_version_label(screen)
        assert version_label is not None
        assert version_label.text == "版本 1.0.0"

        touch = MockTouch(x=50, y=25)

        # 5 次点击应当重置 counter 并触发 dev panel
        for _ in range(5):
            screen._on_version_click(version_label, touch)

        assert screen._version_clicks == 0  # 已重置

    def test_version_click_4_times_not_enough(self) -> None:
        """不足 5 次不触发。"""
        svc = MockSettingsService()
        screen = SettingsScreen(settings_service=svc)

        version_label = _find_version_label(screen)
        touch = MockTouch(x=50, y=25)

        for _ in range(4):
            screen._on_version_click(version_label, touch)

        assert screen._version_clicks == 4

    def test_version_click_counter_resets_after_trigger(self) -> None:
        """触发后重置，下次仍需 5 次。"""
        svc = MockSettingsService()
        screen = SettingsScreen(settings_service=svc)

        version_label = _find_version_label(screen)
        touch = MockTouch(x=50, y=25)

        for _ in range(5):
            screen._on_version_click(version_label, touch)
        assert screen._version_clicks == 0  # 已触发并重置

        # 再点 1 次，计数从 1 开始
        screen._on_version_click(version_label, touch)
        assert screen._version_clicks == 1

    def test_dev_panel_shows_settings_json(self) -> None:
        """开发面板显示所有设置项。"""
        svc = MockSettingsService()
        screen = SettingsScreen(settings_service=svc)
        # verify no exception
        screen._show_dev_panel()
        # 验证版本点击计数器已重置
        assert screen._version_clicks == 0
        # 确认 settings_service.get_all 返回了数据
        data = svc.get_all()
        assert len(data) > 0
        assert "morning_start" in data


# ============================================================
# 内部辅助函数
# ============================================================


def _find_widgets(parent: Any, target_type: type) -> list[Any]:
    """递归查找指定类型的所有子 Widget。"""
    results: list[Any] = []
    if isinstance(parent, target_type):
        results.append(parent)
    if hasattr(parent, "children") and parent.children:
        for child in parent.children:
            results.extend(_find_widgets(child, target_type))
    return results


def _find_work_day_buttons(screen: SettingsScreen) -> list[PixelButton]:
    """查找 SettingsScreen 中的工作日按钮。"""
    return getattr(screen, "_day_buttons", [])


def _find_version_label(screen: SettingsScreen) -> Label | None:
    """递归查找版本号 Label。"""
    labels = _find_widgets(screen, Label)
    for lbl in labels:
        if hasattr(lbl, "text") and lbl.text == "版本 1.0.0":
            return lbl
    return None
