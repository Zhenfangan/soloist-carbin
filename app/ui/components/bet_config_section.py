"""BetConfigSection — 赏罚设置折叠区。

基于 CollapsibleGroup，折叠态显示"本周赏罚设置 ▶"，
展开态显示完成奖励/超额奖励/惩罚金额，每项旁有编辑按钮。
"""

from __future__ import annotations

from typing import Any

from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView

from app.services.bet_service import BetService
from app.ui.components.collapsible_group import CollapsibleGroup
from app.ui.components.pixel_button import PixelButton
from app.ui.components.pixel_input import PixelInput
from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_PADDING,
    CARD_WHITE,
    COLORS,
    FONT_SIZE_BODY,
    GRID_UNIT,
    TEXT_BROWN,
)


class _EditDialog(ModalView):  # type: ignore[misc]
    """数字编辑弹窗。"""

    def __init__(
        self,
        label: str,
        current_value: float,
        on_save: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.background = ""
        self.background_color = (0, 0, 0, 0)
        self.auto_dismiss = True
        self._on_save = on_save

        root = FloatLayout()
        self.add_widget(root)

        with root.canvas.before:
            Color(0, 0, 0, 0.5)
            self._mask_rect = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_mask, pos=self._update_mask)

        card_w = 280
        card_h = 200

        card = FloatLayout(
            size_hint=(None, None),
            size=(card_w, card_h),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )

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

        title_label = Label(
            text=label,
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=40,
            pos_hint={"x": 0, "y": 1 - 0.25},
            halign="center",
            valign="middle",
        )

        self._input = PixelInput(
            hint_text="输入金额",
            value=str(int(current_value)),
            size_hint=(None, None),
            size=(card_w - CARD_PADDING * 2, 40),
            pos_hint={"x": 0.5, "y": 0.45},
        )

        btn_layout = BoxLayout(
            orientation="horizontal",
            spacing=GRID_UNIT * 2,
            size_hint=(1, None),
            height=40,
            pos_hint={"x": 0, "y": 0.05},
            padding=[CARD_PADDING, 0],
        )

        cancel_btn = PixelButton(
            text="取消",
            color=COLORS["CARD_SHADOW"],
            size_mode="small",
            size_hint=(1, None),
        )
        cancel_btn.bind(on_press=lambda _: self.dismiss())

        save_btn = PixelButton(
            text="保存",
            color=COLORS["PRIMARY_YELLOW"],
            size_mode="small",
            size_hint=(1, None),
        )
        save_btn.bind(on_press=lambda _: self._handle_save())

        btn_layout.add_widget(cancel_btn)
        btn_layout.add_widget(save_btn)

        card.add_widget(title_label)
        card.add_widget(self._input)
        card.add_widget(btn_layout)
        root.add_widget(card)

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

    def _handle_save(self) -> None:
        try:
            val = float(self._input.value)
            if val < 0:
                val = 0.0
            if self._on_save:
                self._on_save(val)
            self.dismiss()
        except ValueError:
            pass


class BetConfigSection(CollapsibleGroup):
    """赏罚设置折叠区。

    折叠态: "本周赏罚设置 ▶"
    展开态: 完成奖励 / 超额单任务奖励 / 未完成惩罚金额，每项有编辑按钮。
    编辑弹出数字输入弹窗 -> 调用 BetService.set_week_config()。

    属性:
        week_start: 周起始日期 YYYY-MM-DD
        bet_service: BetService 实例
    """

    def __init__(
        self,
        week_start: str,
        bet_service: BetService,
        **kwargs: Any,
    ) -> None:
        self._week_start = week_start
        self._bet_service = bet_service
        self._config: dict[str, float] = {
            "base_reward": 50.0,
            "extra_reward": 30.0,
            "penalty": 50.0,
        }

        # 构建展开内容
        content = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=GRID_UNIT // 2,
            padding=[CARD_PADDING, GRID_UNIT],
        )
        self._content_layout = content

        # 三个配置行
        self._reward_row = self._build_config_row("完成奖励", "base_reward", "50")
        self._extra_row = self._build_config_row("超额单任务奖励", "extra_reward", "30")
        self._penalty_row = self._build_config_row("未完成惩罚", "penalty", "50")

        content.add_widget(self._reward_row)
        content.add_widget(self._extra_row)
        content.add_widget(self._penalty_row)

        # 绑定高度
        content.bind(minimum_height=content.setter("height"))

        super().__init__(
            title="本周赏罚设置 [+]",
            content=content,
            collapsed=True,
            **kwargs,
        )

        # 加载当前配置
        self._load_config()

    def _build_config_row(self, label: str, key: str, default: str) -> BoxLayout:
        """构建一行配置: 标签 + 数值 + 编辑按钮。"""
        row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=40,
            spacing=GRID_UNIT,
        )

        label_w = Label(
            text=label,
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(0.6, 1),
            halign="left",
            valign="middle",
        )

        value_w = Label(
            text=default,
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(COLORS["PRIMARY_YELLOW"]),
            size_hint=(0.2, 1),
            halign="center",
            valign="middle",
        )

        edit_btn = PixelButton(
            text="编辑",
            color=COLORS["CARD_SHADOW"],
            size_mode="small",
            size_hint=(0.2, 1),
        )

        # 保存引用用于更新
        setattr(self, f"_{key}_label", value_w)

        # 绑定编辑
        current_default = float(default)
        edit_btn.bind(
            on_press=lambda _: self._open_edit_dialog(key, current_default)
        )

        row.add_widget(label_w)
        row.add_widget(value_w)
        row.add_widget(edit_btn)
        return row

    def _open_edit_dialog(self, key: str, current: float) -> None:
        """打开编辑弹窗。"""
        label_map = {
            "base_reward": "完成奖励金额",
            "extra_reward": "超额单任务奖励",
            "penalty": "未完成惩罚金额",
        }
        dialog = _EditDialog(
            label=label_map.get(key, "编辑"),
            current_value=current,
            on_save=lambda val: self._save_config(key, val),
        )
        dialog.open()

    def _save_config(self, key: str, value: float) -> None:
        """保存单项配置并更新显示。"""
        self._config[key] = value

        # 更新显示
        label = getattr(self, f"_{key}_label", None)
        if label:
            label.text = str(int(value))

        # 持久化
        try:
            self._bet_service.set_week_config(
                week_start=self._week_start,
                base_reward=self._config["base_reward"],
                extra_reward=self._config["extra_reward"],
                penalty=self._config["penalty"],
            )
        except Exception:
            pass

    def _load_config(self) -> None:
        """从 BetService 加载当前配置。"""
        try:
            summary = self._bet_service.get_week_summary(self._week_start)
            config = summary.get("config")
            if config:
                self._config["base_reward"] = float(getattr(config, "base_reward", 50))
                self._config["extra_reward"] = float(getattr(config, "extra_reward", 30))
                self._config["penalty"] = float(getattr(config, "penalty", 50))

                # 更新显示
                for key in ("base_reward", "extra_reward", "penalty"):
                    label = getattr(self, f"_{key}_label", None)
                    if label:
                        label.text = str(int(self._config[key]))
        except Exception:
            pass

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)
