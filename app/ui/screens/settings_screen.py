"""SettingsScreen — 设置主页面 (UI-06)。

4 个 CollapsibleGroup 分组折叠，默认全部展开。
构造函数注入 SettingsService + SyncService。
"""

from __future__ import annotations

from typing import Any

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.logger import Logger
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from app.ui.components.amount_picker_row import AmountPickerRow
from app.ui.components.collapsible_group import CollapsibleGroup
from app.ui.components.pixel_button import PixelButton
from app.ui.components.pixel_dialog import ConfirmDialog
from app.ui.components.pixel_input import PixelInput
from app.ui.components.time_picker_row import TimePickerRow
from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_PADDING,
    CARD_WHITE,
    COLORS,
    DOPAMINE_COLORS,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    GRID_UNIT,
    SHADOW_BLACK,
    TEXT_BROWN,
    TEXT_GRAY,
)

# 便捷颜色常量
SKY_BLUE: str = DOPAMINE_COLORS["sky"]["light"]
WARM_ORANGE: str = DOPAMINE_COLORS["warm_orange"]["light"]
MINT_GREEN: str = DOPAMINE_COLORS["mint"]["light"]

# 星期映射：1=周一 … 7=周日
DAY_LABELS: list[tuple[int, str]] = [
    (1, "一"),
    (2, "二"),
    (3, "三"),
    (4, "四"),
    (5, "五"),
    (6, "六"),
    (7, "日"),
]


class SettingsScreen(BoxLayout):  # type: ignore[misc]
    """设置主页面。

    用法:
        screen = SettingsScreen(settings_service, sync_service)

    包含 4 个折叠分组:
        - 上班时间 (4 条 TimePickerRow + 工作日多选)
        - 奖惩金额 (4 条 AmountPickerRow)
        - 对赌配置 (3 条 AmountPickerRow)
        - 其他 (男友门槛/拍摄日奖励/服务器地址/Token/备份恢复/版本号)
    """

    def __init__(
        self,
        settings_service: Any = None,
        sync_service: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(orientation="vertical", **kwargs)
        self._settings_service = settings_service
        self._sync_service = sync_service
        self._version_clicks = 0

        # ScrollView 主容器
        scroll = ScrollView(size_hint=(1, 1), bar_width=8)
        content = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=[0, GRID_UNIT, 0, GRID_UNIT],
            spacing=GRID_UNIT,
        )
        content.bind(minimum_height=content.setter("height"))

        # 白色背景
        with content.canvas.before:
            Color(*self._to_rgba(CARD_WHITE))
            self._content_bg_rect = Rectangle(size=content.size, pos=content.pos)
        content.bind(size=self._update_content_bg, pos=self._update_content_bg)

        # 标题
        title_label = Label(
            text="设置",
            font_size=FONT_SIZE_TITLE,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=48,
            halign="center",
            valign="middle",
        )
        content.add_widget(title_label)

        # --- 1. 上班时间组 ---
        work_time_content = self._build_work_time_group()
        group1 = CollapsibleGroup(
            title="上班时间",
            content=work_time_content,
            collapsed=False,
        )
        content.add_widget(group1)

        # --- 2. 奖惩金额组 ---
        penalty_content = self._build_penalty_group()
        group2 = CollapsibleGroup(
            title="奖惩金额",
            content=penalty_content,
            collapsed=False,
        )
        content.add_widget(group2)

        # --- 3. 对赌配置组 ---
        bet_content = self._build_bet_group()
        group3 = CollapsibleGroup(
            title="对赌配置",
            content=bet_content,
            collapsed=False,
        )
        content.add_widget(group3)

        # --- 4. 其他组 ---
        other_content = self._build_other_group()
        group4 = CollapsibleGroup(
            title="其他",
            content=other_content,
            collapsed=False,
        )
        content.add_widget(group4)

        scroll.add_widget(content)
        self.add_widget(scroll)

    def _update_content_bg(self, instance: Any, value: Any) -> None:
        self._content_bg_rect.size = instance.size
        self._content_bg_rect.pos = instance.pos

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    @staticmethod
    def _make_vbox() -> BoxLayout:
        """创建垂直 BoxLayout，自动适应高度。"""
        box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=2)
        box.bind(minimum_height=box.setter("height"))
        return box

    def _read(self, key: str) -> str:
        if self._settings_service:
            return self._settings_service.get(key)  # type: ignore[no-any-return]
        return ""

    def _write(self, key: str, value: str) -> None:
        if self._settings_service:
            self._settings_service.set(key, value)

    # ------------------------------------------------------------------
    # Toast 通知
    # ------------------------------------------------------------------

    def show_toast(self, message: str, duration: float = 2.0) -> None:
        """显示临时 Toast 通知。"""
        toast = ModalView(
            size_hint=(None, None),
            size=(300, 50),
            background="",
            background_color=(0, 0, 0, 0),
            auto_dismiss=True,
        )

        toast_label = Label(
            text=message,
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(COLORS["BG_CREAM"]),
            halign="center",
            valign="middle",
        )

        # 带背景的 Toast 容器
        with toast.canvas.before:
            Color(0, 0, 0, 0.85)
            Rectangle(pos=toast.pos, size=toast.size)
        toast.bind(pos=lambda _t, _v: toast.canvas.before.clear() or self._redraw_toast(toast))
        toast.bind(size=lambda _t, _v: toast.canvas.before.clear() or self._redraw_toast(toast))

        toast.add_widget(toast_label)
        toast.open()
        Clock.schedule_once(lambda dt: toast.dismiss(), duration)

    @staticmethod
    def _redraw_toast(toast: ModalView) -> None:
        with toast.canvas.before:
            Color(0, 0, 0, 0.85)
            Rectangle(pos=toast.pos, size=toast.size)

    # ------------------------------------------------------------------
    # 上班时间组
    # ------------------------------------------------------------------

    def _build_work_time_group(self) -> Widget:
        box = self._make_vbox()
        time_rows = [
            ("上午上班", "morning_start"),
            ("上午下班", "morning_end"),
            ("下午上班", "afternoon_start"),
            ("下午下班", "afternoon_end"),
        ]
        for label, key in time_rows:
            row = TimePickerRow(label, key, self._settings_service)
            box.add_widget(row)

        # 工作日多选行
        work_days_row = self._build_work_days_row()
        box.add_widget(work_days_row)

        return box

    def _build_work_days_row(self) -> Widget:
        """构建工作日多选行。"""
        container = BoxLayout(
            orientation="horizontal",
            spacing=4,
            padding=[CARD_PADDING, 4],
            size_hint=(1, None),
            height=44,
        )

        day_label = Label(
            text="工作日",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, 1),
            width=80,
            halign="left",
            valign="middle",
        )
        container.add_widget(day_label)

        # 读取当前工作日设置
        current_days: list[int] = []
        if self._settings_service:
            current_days = self._settings_service.get_work_days()

        self._day_buttons: list[PixelButton] = []
        self._day_values: list[int] = []

        for weekday, label_char in DAY_LABELS:
            is_selected = weekday in current_days
            btn = PixelButton(
                text=label_char,
                size_mode="small",
                size_hint=(None, 1),
                width=40,
                color=COLORS["PRIMARY_YELLOW"] if is_selected else COLORS["CARD_SHADOW"],
            )
            btn._is_day_selected = is_selected
            btn._weekday = weekday
            btn.bind(on_press=lambda _b=btn: self._toggle_work_day(_b))
            container.add_widget(btn)
            self._day_buttons.append(btn)
            self._day_values.append(weekday)

        return container

    def _toggle_work_day(self, btn: PixelButton) -> None:
        """切换工作日勾选状态。"""
        btn._is_day_selected = not btn._is_day_selected
        btn.set_color(
            COLORS["PRIMARY_YELLOW"] if btn._is_day_selected else COLORS["CARD_SHADOW"]
        )

        # 构建新的 work_days 字符串
        selected = sorted([
            btn._weekday for btn in self._day_buttons
            if btn._is_day_selected
        ])
        self._write("work_days", ",".join(str(d) for d in selected))

    # ------------------------------------------------------------------
    # 奖惩金额组
    # ------------------------------------------------------------------

    def _build_penalty_group(self) -> Widget:
        box = self._make_vbox()
        rows = [
            ("迟到罚款", "late_penalty", True),
            ("早退罚款", "early_leave_penalty", True),
            ("旷工罚款", "absent_penalty", True),
            ("全勤奖励", "full_attendance_bonus", False),
        ]
        for label, key, is_penalty in rows:
            row = AmountPickerRow(label, key, self._settings_service, is_penalty=is_penalty)
            box.add_widget(row)
        return box

    # ------------------------------------------------------------------
    # 对赌配置组
    # ------------------------------------------------------------------

    def _build_bet_group(self) -> Widget:
        box = self._make_vbox()
        rows = [
            ("基础奖励", "bet_base_reward", False),
            ("超额奖励", "bet_extra_reward", False),
            ("惩罚金额", "bet_penalty", True),
        ]
        for label, key, is_penalty in rows:
            row = AmountPickerRow(label, key, self._settings_service, is_penalty=is_penalty)
            box.add_widget(row)
        return box

    # ------------------------------------------------------------------
    # 其他组
    # ------------------------------------------------------------------

    def _build_other_group(self) -> Widget:
        box = self._make_vbox()

        # --- 男友奖励时长门槛 ---
        threshold_row = AmountPickerRow(
            "男友奖励时长门槛",
            "boyfriend_hour_threshold",
            self._settings_service,
            is_penalty=False,
        )
        box.add_widget(threshold_row)

        # --- 拍摄日奖励 ---
        shooting_row = AmountPickerRow(
            "拍摄日奖励",
            "shooting_reward",
            self._settings_service,
            is_penalty=False,
        )
        box.add_widget(shooting_row)

        # --- 服务器地址 (PixelInput 行) ---
        server_row = self._build_text_input_row(
            label="服务器地址",
            key="server_url",
            hint="http://localhost:8000",
            password=False,
        )
        box.add_widget(server_row)

        # --- 同步 Token (PixelInput 行，密码遮蔽) ---
        token_row = self._build_text_input_row(
            label="同步Token",
            key="sync_token",
            hint="",
            password=True,
        )
        box.add_widget(token_row)

        # --- 分隔间距 ---
        box.add_widget(Widget(size_hint=(1, None), height=GRID_UNIT))

        # --- 备份数据按钮 ---
        backup_btn = PixelButton(
            text="备份数据",
            color=SKY_BLUE,
            size_mode="normal",
            size_hint=(1, None),
        )
        backup_btn.bind(on_press=lambda _: self._on_backup())
        box.add_widget(backup_btn)

        # --- 恢复数据按钮 ---
        restore_btn = PixelButton(
            text="恢复数据",
            color=WARM_ORANGE,
            size_mode="normal",
            size_hint=(1, None),
        )
        restore_btn.bind(on_press=lambda _: self._on_restore())
        box.add_widget(restore_btn)

        # --- 分隔间距 ---
        box.add_widget(Widget(size_hint=(1, None), height=GRID_UNIT))

        # --- 版本号行 ---
        version_container = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=36,
            padding=[CARD_PADDING, 0],
        )
        version_label = Label(
            text="版本 1.0.0",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_GRAY),
            size_hint=(1, 1),
            halign="center",
            valign="middle",
        )
        version_label.bind(on_touch_down=self._on_version_click)
        version_container.add_widget(version_label)
        box.add_widget(version_container)

        return box

    def _build_text_input_row(self, label: str, key: str, hint: str = "", password: bool = False) -> Widget:
        """构建带标签的 PixelInput 行。"""
        row = BoxLayout(
            orientation="horizontal",
            spacing=CARD_PADDING,
            padding=[CARD_PADDING, 4],
            size_hint=(1, None),
            height=48,
        )

        lbl = Label(
            text=label,
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, 1),
            width=90,
            halign="left",
            valign="middle",
            text_size=(90, None),
        )
        row.add_widget(lbl)

        current_value = self._read(key)
        inp = PixelInput(
            hint_text=hint,
            value=current_value,
            password=password,
            size_hint=(1, 1),
        )
        inp.bind(text=lambda _inst, _val: self._on_text_input_change(key, _val))
        row.add_widget(inp)

        return row

    def _on_text_input_change(self, key: str, value: str) -> None:
        """PixelInput 文本变化时自动保存。"""
        self._write(key, value)

    # ------------------------------------------------------------------
    # 备份 / 恢复
    # ------------------------------------------------------------------

    def _on_backup(self) -> None:
        """备份数据：弹出确认 → 执行备份 → Toast。"""
        if not self._sync_service:
            self.show_toast("同步服务未初始化")
            return

        dialog = ConfirmDialog(
            title="备份数据",
            message="确定要备份全部数据吗？",
            confirm_text="确认备份",
            cancel_text="取消",
            on_confirm=self._do_backup,
        )
        dialog.open()

    def _do_backup(self) -> None:
        """执行备份。"""
        try:
            self._sync_service.backup_full()
            self.show_toast("数据备份成功")
        except Exception as e:
            Logger.error(f"SettingsScreen: {e}")
            self.show_toast("备份失败，请重试")

    def _on_restore(self) -> None:
        """恢复数据：弹出警告确认 → 执行恢复 → Toast。"""
        if not self._sync_service:
            self.show_toast("同步服务未初始化")
            return

        dialog = ConfirmDialog(
            title="恢复数据",
            message="警告：恢复数据将覆盖当前全部数据！此操作不可撤销！",
            confirm_text="确认恢复",
            cancel_text="取消",
            on_confirm=self._do_restore,
        )
        dialog.open()

    def _do_restore(self) -> None:
        """执行恢复。"""
        try:
            backup_data = self._sync_service.backup_full()
            data = backup_data.get("data", {})
            if isinstance(data, dict):
                self._sync_service.restore_full(data)
            self.show_toast("数据恢复成功")
        except Exception as e:
            Logger.error(f"SettingsScreen: {e}")
            self.show_toast("恢复失败，请重试")

    # ------------------------------------------------------------------
    # 版本号连击 → 开发面板
    # ------------------------------------------------------------------

    def _on_version_click(self, instance: Any, touch: Any) -> bool:
        """版本号连点 5 次进入开发面板。"""
        if not instance.collide_point(*touch.pos):
            return False

        self._version_clicks += 1
        if self._version_clicks >= 5:
            self._version_clicks = 0
            self._show_dev_panel()
        return True

    def _show_dev_panel(self) -> None:
        """显示开发面板（原始 JSON 数据）。"""
        raw: dict[str, str] = {}
        if self._settings_service:
            raw = self._settings_service.get_all()

        lines = []
        for key, val in raw.items():
            lines.append(f"{key}={val}")
        json_text = "\n".join(lines) if lines else "(空)"

        dev_view = ModalView(
            size_hint=(0.85, 0.7),
            background="",
            background_color=(0, 0, 0, 0),
            auto_dismiss=True,
        )

        card = FloatLayout()

        # 背景 + 边框
        with card.canvas.before:
            Color(*self._to_rgba(SHADOW_BLACK))
            Rectangle(pos=(card.x + 2, card.y - 2), size=(card.width, card.height))
            Color(*self._to_rgba(CARD_WHITE))
            Rectangle(pos=(card.x, card.y), size=(card.width, card.height))
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(card.x, card.y + card.height - BORDER_WIDTH), size=(card.width, BORDER_WIDTH))
            Rectangle(pos=(card.x, card.y), size=(BORDER_WIDTH, card.height))
            Color(*self._to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(card.x, card.y), size=(card.width, BORDER_WIDTH))
            Rectangle(pos=(card.x + card.width - BORDER_WIDTH, card.y), size=(BORDER_WIDTH, card.height))

        card.bind(pos=self._redraw_card_border, size=self._redraw_card_border)

        title_lbl = Label(
            text="开发面板",
            font_size=FONT_SIZE_TITLE,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=40,
            pos_hint={"x": 0, "y": 1 - 0.12},
            halign="center",
            valign="middle",
        )
        card.add_widget(title_lbl)

        data_label = Label(
            text=json_text,
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            pos_hint={"x": 0.05, "y": 0.15},
            halign="left",
            valign="top",
            text_size=(None, None),
        )
        card.add_widget(data_label)

        # Dump widget tree 按钮 (Wave 2 Phase 1 诊断)
        dump_btn = PixelButton(
            text="Dump widget tree",
            color=COLORS["CARD_SHADOW"],
            size_mode="small",
            size_hint=(None, None),
            size=(160, 36),
            pos_hint={"center_x": 0.3, "y": 0.02},
        )
        dump_btn.bind(on_press=lambda _: self._on_dump_widget_tree())
        card.add_widget(dump_btn)

        close_btn = PixelButton(
            text="关闭",
            color=COLORS["PRIMARY_YELLOW"],
            size_mode="small",
            size_hint=(None, None),
            size=(120, 36),
            pos_hint={"center_x": 0.75, "y": 0.02},
        )
        close_btn.bind(on_press=lambda _: dev_view.dismiss())
        card.add_widget(close_btn)

        dev_view.add_widget(card)
        dev_view.open()

    def _on_dump_widget_tree(self) -> None:
        """Dump 当前 widget 树到 Kivy Logger."""
        from kivy.app import App
        from app.ui.debug.layout_tracer import trace_layout

        root = App.get_running_app().root
        if root is None:
            Logger.info("[LAY] root is None, nothing to dump")
            return
        Logger.info(trace_layout(root, label="dev_panel dump"))

    def _redraw_card_border(self, instance: Any, value: Any) -> None:
        """重绘卡片的像素边框。"""
        instance.canvas.before.clear()
        bw = BORDER_WIDTH
        x, y = instance.pos
        w, h = instance.size

        with instance.canvas.before:
            Color(*self._to_rgba(SHADOW_BLACK))
            Rectangle(pos=(x + 2, y - 2), size=(w, h))
            Color(*self._to_rgba(CARD_WHITE))
            Rectangle(pos=(x, y), size=(w, h))
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(x, y + h - bw), size=(w, bw))
            Rectangle(pos=(x, y), size=(bw, h))
            Color(*self._to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(x, y), size=(w, bw))
            Rectangle(pos=(x + w - bw, y), size=(w, h))
