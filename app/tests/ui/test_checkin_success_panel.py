"""CheckinSuccessPanel — 过期判定, 避免 on_resume 秒杀刚打开的庆祝面板。

回归背景(真机): SoloistApp.on_resume() 钩子调用 CheckinScreen.refresh(),
refresh() 里原本无条件 force-dismiss 任何 _active_success_panel。但
on_resume 在相机 Intent 返回后几乎与面板刚创建同一瞬间触发(Android 生
命周期: onActivityResult 早于 onResume), 导致面板被自己秒杀 —— 签到后
按钮状态正确了(refresh_status 生效), 但用户再也看不到庆祝动画。

修复: 面板记录真实打开时刻(time.monotonic, 不依赖 Kivy Clock 是否正常
跳动), refresh() 只在面板"确实展示够 DISPLAY_DURATION 仍未消失"(过期/
卡死)时才强制解挂; 刚打开的面板应被放过, 让它自然播放/自然消失。
"""

from __future__ import annotations

from kivy.uix.widget import Widget

from app.ui.components.checkin_success_panel import DISPLAY_DURATION, CheckinSuccessPanel


def _make_card() -> Widget:
    return Widget(size=(300, 100), pos=(0, 0))


class TestIsOverdue:
    def test_freshly_opened_panel_is_not_overdue(self) -> None:
        panel = CheckinSuccessPanel(target_card=_make_card())
        panel.open()
        assert panel.is_overdue() is False

    def test_panel_open_past_display_duration_is_overdue(self) -> None:
        panel = CheckinSuccessPanel(target_card=_make_card())
        panel.open()
        # 手动把"打开时刻"回拨到超过展示时长之前, 模拟真实经过了那么久
        panel._shown_at -= (DISPLAY_DURATION + 0.1)
        assert panel.is_overdue() is True

    def test_not_yet_opened_panel_is_not_overdue(self) -> None:
        """open() 还没调用(理论上不应发生, 但防御性检查不应崩溃/误判)。"""
        panel = CheckinSuccessPanel(target_card=_make_card())
        assert panel.is_overdue() is False


class TestPanelSizing:
    """签退成功时卡片可能在 open() 前已折叠到 _COLLAPSED_HEIGHT(=HEADER_HEIGHT),
    面板高度不能再用 card.height-HEADER_HEIGHT 反算 —— 否则算出 0, 整个庆祝
    动画完全不可见(真机复现: 签退后卡片瞬间折叠, 用户从未看到过动画)。
    """

    def test_panel_visible_even_if_card_already_collapsed_before_open(self) -> None:
        card = Widget(size=(300, 48), pos=(0, 0))  # 模拟 PeriodCard._COLLAPSED_HEIGHT
        panel = CheckinSuccessPanel(target_card=card)
        panel.open()
        assert panel.height > 0

    def test_panel_height_matches_expanded_card_content_area(self) -> None:
        """卡片仍是展开态(_EXPANDED_HEIGHT=180)时, 面板高度应为
        180-HEADER_HEIGHT(48)=132 —— 与此前正确行为保持一致, 不能因
        改为固定高度而回归。"""
        card = Widget(size=(300, 180), pos=(0, 0))
        panel = CheckinSuccessPanel(target_card=card)
        panel.open()
        assert panel.height == 132

    def test_panel_height_unaffected_by_card_shrinking_after_open(self) -> None:
        """面板打开后, 若卡片(比如紧接着的签退动作)把高度收缩到
        COLLAPSED, 面板自己的高度不应跟着塌缩到 0 —— 展示期间应保持
        稳定可见。"""
        card = Widget(size=(300, 180), pos=(0, 0))
        panel = CheckinSuccessPanel(target_card=card)
        panel.open()
        card.height = 48  # 触发 _on_card_changed
        assert panel.height > 0
