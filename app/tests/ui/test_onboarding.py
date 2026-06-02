"""测试引导流程 — OnboardingScreen 分步设置。"""

from __future__ import annotations

from app.ui.screens.onboarding_screen import OnboardingScreen


class TestOnboardingScreen:
    """7.10~7.16 OnboardingScreen 测试"""

    def test_create_onboarding(self) -> None:
        finished: list[bool] = []

        def on_finish() -> None:
            finished.append(True)

        screen = OnboardingScreen(on_finish=on_finish)
        assert screen._step == 0
        assert screen._current_card is not None
        assert "欢迎" in screen._current_card._title

    def test_step_progression(self) -> None:
        """测试逐步推进。"""
        screen = OnboardingScreen()
        assert screen._step == 0
        screen._next_step()
        assert screen._step == 1
        assert screen._current_card is not None
        assert "上午" in screen._current_card._title

    def test_skip_button_visible(self) -> None:
        """跳过按钮在非最后步骤可见。"""
        screen = OnboardingScreen()
        assert screen._skip_btn.opacity > 0

    def test_finish_callback_on_last_step(self) -> None:
        """最后一步触发完成回调。"""
        finished: list[bool] = []

        def on_finish() -> None:
            finished.append(True)

        screen = OnboardingScreen(on_finish=on_finish)
        # 快进到最后
        for _ in range(9):
            screen._next_step()

        assert len(finished) == 1
        assert finished[0]

    def test_progress_label_updates(self) -> None:
        """进度标签随步骤更新。"""
        screen = OnboardingScreen()
        assert screen._progress.text == "1 / 9"
        screen._next_step()
        assert screen._progress.text == "2 / 9"

    def test_last_step_button_text(self) -> None:
        """最后一步按钮文字变化。"""
        screen = OnboardingScreen()
        for _ in range(8):
            screen._next_step()
        # 第9步 (index 8): 按钮应为 "进入主界面"
        assert screen._next_btn.text == "进入主界面", (
            f"expected '进入主界面', got '{screen._next_btn.text}'"
        )
