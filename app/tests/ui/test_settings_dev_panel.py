"""测试设置页 dev_panel data_label 使用 ScrollView 防溢出。"""
import pytest
from kivy.uix.scrollview import ScrollView
from app.ui.screens.settings_screen import SettingsScreen
from app.repositories.settings_repo import SettingsRepo
from app.services.settings_service import SettingsService


class TestSettingsDevPanel:
    """测试 dev_panel 中 data_label 被 ScrollView 包裹。"""

    @pytest.fixture
    def screen(self, temp_db: str) -> SettingsScreen:
        """创建 SettingsScreen 实例。"""
        svc = SettingsService(SettingsRepo(temp_db))
        # 写入一些数据，确保 json_text 超过 100 字符以便测试断言
        test_data = {
            "work_start": "09:00",
            "work_end": "18:00",
            "absent_penalty": "50",
            "full_attendance_bonus": "100",
            "bet_base_reward": "50",
            "bet_extra_reward": "30",
            "bet_penalty": "50",
        }
        for k, v in test_data.items():
            svc.set(k, v)
        return SettingsScreen(settings_service=svc)

    def test_dev_panel_data_label_inside_scrollview(self, screen: SettingsScreen) -> None:
        """触发 _show_dev_panel, 校验 data_label 的 parent 是 ScrollView。"""
        screen._show_dev_panel()
        # ModalView.open() 会将自身添加到 Window.children
        from kivy.core.window import Window
        from kivy.uix.label import Label
        from kivy.uix.modalview import ModalView

        # 遍历 Window 的子元素查找 ModalView
        for child in Window.children:
            if isinstance(child, ModalView):
                # 在 widget 树中查找含长文本的 Label
                for label in child.walk():
                    if (
                        isinstance(label, Label)
                        and hasattr(label, 'text')
                        and label.text and len(label.text) > 100
                    ):
                        parent_type = type(label.parent).__name__
                        assert isinstance(label.parent, ScrollView), (
                            f"data_label parent 应该是 ScrollView, 实际是 {parent_type}"
                        )
                        return

        pytest.skip("dev_panel ModalView 未找到 (可能需要其他依赖)")
