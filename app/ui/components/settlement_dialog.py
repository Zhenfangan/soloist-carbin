"""SettlementDialog — 周结算确认弹窗。

像素弹窗展示: 完成 / 超额 / 奖励 + 超额 = +Total / 惩罚 -N / 净额 +N，
确认后调用 BetService.settle_week() -> 团团抱星星动画 (4帧)。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from app.utils.clock import get_clock
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView

from app.services.bet_service import BetService
from app.ui.assets.loader import SequenceLoader
from app.ui.components.pixel_button import PixelButton
from app.ui.scale_util import scale_wrap
from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_PADDING,
    CARD_WHITE,
    COLORS,
    DOPAMINE_COLORS,
    FONT_SIZE_BODY,
    FONT_SIZE_TITLE,
    GRID_UNIT,
    TEXT_BROWN,
    TEXT_GRAY,
)


class SettlementDialog(ModalView):  # type: ignore[misc]
    """周结算确认弹窗。

    用法:
        dialog = SettlementDialog(
            week_start="2026-06-01",
            bet_service=bet_service,
            summary=summary_dict,
            on_settled=lambda: refresh(),
        )
        dialog.open()
    """

    def __init__(
        self,
        week_start: str,
        bet_service: BetService,
        summary: dict[str, object],
        on_settled: Callable[[], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.background = ""
        self.background_color = (0, 0, 0, 0)
        self.auto_dismiss = True

        self._week_start = week_start
        self._bet_service = bet_service
        self._summary = summary
        self._on_settled = on_settled
        self._is_settling = False

        root = FloatLayout()
        self.add_widget(root)

        # 半透明遮罩
        with root.canvas.before:
            Color(0, 0, 0, 0.5)
            self._mask_rect = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_mask, pos=self._update_mask)

        # 弹窗卡片
        card_w = 340
        card_h = 380

        card = FloatLayout(
            size_hint=(None, None),
            size=(card_w, card_h),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )

        # 卡片边框 + 阴影
        with card.canvas.before:
            Color(*self._to_rgba(COLORS["SHADOW_BLACK"]))
            Rectangle(pos=(card.x + 2, card.y - 2), size=(card.width, card.height))
            Color(*self._to_rgba(CARD_WHITE))
            Rectangle(pos=(card.x, card.y), size=(card.width, card.height))
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(card.x, card.y + card_h - BORDER_WIDTH), size=(card_w, BORDER_WIDTH))
            Rectangle(pos=(card.x, card.y), size=(BORDER_WIDTH, card_h))
            Color(*self._to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(card.x, card.y), size=(card_w, BORDER_WIDTH))
            Rectangle(pos=(card.x + card_w - BORDER_WIDTH, card.y), size=(BORDER_WIDTH, card_h))

        card.bind(pos=self._redraw_card, size=self._redraw_card)

        # 计算结算数据
        completed = cast(int, summary.get("completed", 0) or 0)
        total_tasks = cast(int, summary.get("total_tasks", 0) or 0)
        extra_count = cast(int, summary.get("extra_count", 0) or 0)
        week_status = str(summary.get("status", "active"))
        accrued_late_fees = float(summary.get("accrued_late_fees", 0) or 0)
        late_fee_per_day = float(summary.get("late_fee_per_day", 10) or 10)
        late_start_date = summary.get("late_start_date")

        config = summary.get("config")
        if config and hasattr(config, "base_reward"):
            base_reward_val = float(getattr(config, "base_reward", 50))
            extra_reward_val = float(getattr(config, "extra_reward", 30))
            penalty_val = float(getattr(config, "penalty", 50))
        else:
            base_reward_val = 50.0
            extra_reward_val = 30.0
            penalty_val = 50.0

        self._is_late = week_status == "late"
        uncompleted = total_tasks - completed
        self._is_success = uncompleted == 0 and completed > 0

        if self._is_late:
            # 滞纳期结算：罚金已付，无新奖励
            reward_total = 0.0
            extra_total = 0.0
            penalty_total = 0.0
            net = -accrued_late_fees
        elif self._is_success:
            reward_total = base_reward_val
            extra_total = extra_reward_val * extra_count
            penalty_total = 0.0
            net = reward_total + extra_total
        else:
            reward_total = 0.0
            extra_total = 0.0
            penalty_total = penalty_val
            net = -penalty_total

        # 缓存结果用于结算
        self._cached_base_reward = base_reward_val
        self._cached_extra_reward = extra_reward_val
        self._cached_penalty = penalty_val

        # 标题
        title_label = Label(
            text="本周结算确认",
            font_size=FONT_SIZE_TITLE,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=36,
            pos_hint={"x": 0, "y": 1 - 0.13},
            halign="center",
            valign="middle",
        )

        # 结算详情
        detail_box = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=200,
            pos_hint={"x": 0.08, "y": 0.24},
            spacing=GRID_UNIT // 2,
        )

        details: list[tuple[str, str, str]] = [
            ("完成", f"{completed}/{total_tasks}", DOPAMINE_COLORS["mint"]["light"]),
            ("超额", f"{extra_count}", DOPAMINE_COLORS["warm_orange"]["light"]),
            ("", "", ""),
        ]

        if self._is_late:
            # 滞纳期结算详情
            # 计算滞纳天数
            late_days = 0
            if late_start_date:
                try:
                    from datetime import date as dt_date
                    late_start_dt = dt_date.fromisoformat(str(late_start_date))
                    late_days = (get_clock().now().date() - late_start_dt).days + 1
                except Exception:
                    pass
            details.append(("滞纳天数", f"{late_days}天", DOPAMINE_COLORS["coral"]["light"]))
            details.append(("每日滞纳金", f"-{int(late_fee_per_day)}", DOPAMINE_COLORS["coral"]["light"]))
            details.append(("累计滞纳金", f"-{int(accrued_late_fees)}", DOPAMINE_COLORS["coral"]["light"]))
        else:
            details.append(("奖励", f"+{int(reward_total)}", COLORS["PRIMARY_YELLOW"]))

        if extra_total > 0:
            details.append(("超额奖励", f"+{int(extra_total)}", COLORS["PRIMARY_YELLOW"]))
            total_label = f"+{int(reward_total + extra_total)}"
            details.append(("奖励合计", total_label, COLORS["PRIMARY_YELLOW"]))

        if penalty_total > 0:
            details.append(("惩罚", f"-{int(penalty_total)}", DOPAMINE_COLORS["coral"]["light"]))

        details.append(("", "", ""))

        net_color = DOPAMINE_COLORS["mint"]["light"] if net >= 0 else DOPAMINE_COLORS["coral"]["light"]
        sign = "+" if net >= 0 else ""
        details.append(("净额", f"{sign}{int(net)}", net_color))

        for label_text, value_text, color in details:
            if not label_text and not value_text:
                detail_box.add_widget(Label(size_hint_y=None, height=4))
                continue
            row = BoxLayout(orientation="horizontal", size_hint_y=None, height=22)
            lbl = Label(
                text=label_text,
                font_size=FONT_SIZE_BODY,
                color=self._to_rgba(TEXT_GRAY),
                size_hint=(0.5, 1),
                halign="left",
                valign="middle",
            )
            val = Label(
                text=value_text,
                font_size=FONT_SIZE_BODY,
                color=self._to_rgba(color),
                size_hint=(0.5, 1),
                halign="right",
                valign="middle",
                bold=True,
            )
            row.add_widget(lbl)
            row.add_widget(val)
            detail_box.add_widget(row)

        # 结算动画区域 (隐藏)
        self._tuantuan_img = Image(
            size_hint=(None, None),
            size=(64, 64),
            pos_hint={"center_x": 0.5, "center_y": 0.65},
            opacity=0,
            allow_stretch=True,
            keep_ratio=True,
        )

        # 按钮
        btn_layout = BoxLayout(
            orientation="horizontal",
            spacing=GRID_UNIT * 2,
            size_hint=(1, None),
            height=40,
            pos_hint={"x": 0, "y": 0.02},
            padding=[CARD_PADDING, 0],
        )

        cancel_btn = PixelButton(
            text="取消",
            color=COLORS["CARD_SHADOW"],
            size_mode="small",
            size_hint=(1, None),
        )
        cancel_btn.bind(on_press=lambda _: self._handle_cancel())

        confirm_btn = PixelButton(
            text="确认结算",
            color=COLORS["PRIMARY_YELLOW"],
            size_mode="small",
            size_hint=(1, None),
        )
        confirm_btn.bind(on_press=lambda _: self._handle_confirm())

        btn_layout.add_widget(cancel_btn)
        btn_layout.add_widget(confirm_btn)

        card.add_widget(title_label)
        card.add_widget(detail_box)
        card.add_widget(self._tuantuan_img)
        card.add_widget(btn_layout)
        root.add_widget(scale_wrap(card))

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    def _update_mask(self, instance: Any, value: Any) -> None:
        self._mask_rect.size = instance.size
        self._mask_rect.pos = instance.pos

    def _redraw_card(self, instance: Any, value: Any) -> None:
        instance.canvas.before.clear()
        bw = BORDER_WIDTH
        x, y = instance.pos
        w, h = instance.size

        with instance.canvas.before:
            Color(*self._to_rgba(COLORS["SHADOW_BLACK"]))
            Rectangle(pos=(x + 2, y - 2), size=(w, h))
            Color(*self._to_rgba(CARD_WHITE))
            Rectangle(pos=(x, y), size=(w, h))
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(x, y + h - bw), size=(w, bw))
            Rectangle(pos=(x, y), size=(bw, h))
            Color(*self._to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(x, y), size=(w, bw))
            Rectangle(pos=(x + w - bw, y), size=(bw, h))

    def _handle_confirm(self) -> None:
        if self._is_settling:
            return
        self._is_settling = True

        # 滞纳期结算前先补扣当日滞纳金
        try:
            if self._is_late:
                self._bet_service.accrue_late_fees(self._week_start)
            self._bet_service.settle_week(self._week_start)
        except Exception:
            self._is_settling = False
            return

        # 结算动画: 完成用小狗摘星星，失败用小猪倒下 (7帧, 每帧 400ms, 总 2800ms)
        anim_id = "dog" if self._is_success else "pig"
        try:
            frames = SequenceLoader.load_sequence(anim_id)
        except Exception:
            frames = []

        self._tuantuan_img.opacity = 1

        frame_duration = 0.4
        if frames:
            for i in range(len(frames)):
                Clock.schedule_once(
                    lambda dt, idx=i: self._set_tuantuan_frame(frames, idx),
                    i * frame_duration,
                )

        # 结算完成后回调（等动画播完再关闭）
        def _on_settled(dt: float) -> None:
            if self._on_settled:
                self._on_settled()
            self.dismiss()

        total_duration = frame_duration * max(len(frames), 1) + 0.4
        Clock.schedule_once(_on_settled, total_duration)

    def _set_tuantuan_frame(self, frames: list[Any], idx: int) -> None:
        if idx < len(frames):
            self._tuantuan_img.texture = frames[idx].texture

    def _handle_cancel(self) -> None:
        self.dismiss()
