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
    GRASS_INSET,
    GRID_UNIT,
    LOGICAL_HEIGHT,
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
            padding=[CARD_PADDING, GRID_UNIT, CARD_PADDING, GRASS_INSET + GRID_UNIT],
            spacing=GRID_UNIT,
        )
        content.bind(minimum_height=content.setter("height"))

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

        # --- 4. 推送通知组 ---
        ntfy_content = self._build_ntfy_group()
        group4 = CollapsibleGroup(
            title="推送通知",
            content=ntfy_content,
            collapsed=True,
        )
        content.add_widget(group4)

        # --- 5. 个性化激励语句组 ---
        enc_content = self._build_encouragement_group()
        group5 = CollapsibleGroup(
            title="个性化激励语句",
            content=enc_content,
            collapsed=True,
        )
        content.add_widget(group5)

        # --- 6. 其他组 ---
        other_content = self._build_other_group()
        group6 = CollapsibleGroup(
            title="其他",
            content=other_content,
            collapsed=False,
        )
        content.add_widget(group6)

        scroll.add_widget(content)
        self.add_widget(scroll)

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    @staticmethod
    def _make_vbox() -> BoxLayout:
        """创建垂直 BoxLayout，自动适应高度，左右留 CARD_PADDING 边距。"""
        box = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=2,
            padding=[CARD_PADDING, 0, CARD_PADDING, 0],
        )
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
        """显示临时 Toast 通知(委托公共组件 components.toast)。"""
        from app.ui.components.toast import show_toast as _show_toast
        _show_toast(message, duration)

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

        # 休息天数控件 — 与对赌结算后休息弹窗读写同一参数(rest_start/rest_end)
        rest_days_row = self._build_rest_days_row()
        box.add_widget(rest_days_row)

        return box

    def _build_rest_days_row(self) -> Widget:
        """构建休息天数行 — 显示当前休息期, 可 +/- 调整。

        与结算后 RestDaysDialog 读写同一对参数(rest_start/rest_end),
        弹窗里填完这里自动显示, 这里改完弹窗也能读到。
        """
        container = BoxLayout(
            orientation="horizontal",
            spacing=CARD_PADDING,
            padding=[CARD_PADDING, 4],
            size_hint=(1, None),
            height=44,
        )

        day_label = Label(
            text="休息天数",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, 1),
            width=70,
            halign="left",
            valign="middle",
        )
        container.add_widget(day_label)

        self._rest_days_display = Label(
            text=self._rest_days_display_text(),
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, 1),
            halign="center",
            valign="middle",
        )
        self._rest_days_display.bind(
            size=lambda inst, _: setattr(inst, "text_size", (inst.width, None))
        )
        container.add_widget(self._rest_days_display)

        minus_btn = PixelButton(
            text="−",
            size_mode="small",
            size_hint=(None, 1),
            width=44,
            color=COLORS["CARD_SHADOW"],
        )
        minus_btn.bind(on_press=lambda _: self._adjust_rest_days(-1))
        container.add_widget(minus_btn)

        plus_btn = PixelButton(
            text="+",
            size_mode="small",
            size_hint=(None, 1),
            width=44,
            color=MINT_GREEN,
        )
        plus_btn.bind(on_press=lambda _: self._adjust_rest_days(1))
        container.add_widget(plus_btn)

        return container

    def _rest_days_display_text(self) -> str:
        """根据 rest_start/rest_end 计算当前休息天数。"""
        if not self._settings_service:
            return "未设置"
        period = self._settings_service.get_rest_period()
        if period is None:
            return "未设置"
        start, end = period
        if not start or not end:
            return "未设置"
        try:
            from datetime import datetime
            s = datetime.strptime(start, "%Y-%m-%d")
            e = datetime.strptime(end, "%Y-%m-%d")
            days = (e - s).days + 1
            return f"{days} 天 ({start[5:]} – {end[5:]})"
        except Exception:
            return "未设置"

    def _adjust_rest_days(self, delta: int) -> None:
        """调整休息天数 — 从明天起算, 与结算弹窗语义一致。"""
        if not self._settings_service:
            return
        from datetime import datetime, timedelta
        from app.utils.clock import get_clock

        today = get_clock().today_str()
        tomorrow = (
            datetime.strptime(today, "%Y-%m-%d") + timedelta(days=1)
        ).strftime("%Y-%m-%d")

        period = self._settings_service.get_rest_period()
        if period is None or not period[0] or not period[1]:
            # 未设置 → 从明天起, 至少 1 天
            days = max(1, delta)
        else:
            start, end = period
            try:
                s = datetime.strptime(start, "%Y-%m-%d")
                e = datetime.strptime(end, "%Y-%m-%d")
                current_days = (e - s).days + 1
                days = max(0, current_days + delta)
            except Exception:
                days = max(1, delta)

        if days <= 0:
            self._settings_service.set("rest_start", "")
            self._settings_service.set("rest_end", "")
        else:
            self._settings_service.start_rest_period(tomorrow, days)

        self._rest_days_display.text = self._rest_days_display_text()

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

        # --- 个性化称呼 ---
        nickname_row = self._build_text_input_row(
            label="个性称呼",
            key="user_nickname",
            hint="如:老公、宝贝…(留空不使用)",
            password=False,
        )
        box.add_widget(nickname_row)

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

    # ------------------------------------------------------------------
    # 推送通知组
    # ------------------------------------------------------------------

    def _build_ntfy_group(self) -> Widget:
        box = self._make_vbox()

        # --- 开关行 ---
        switch_row = BoxLayout(
            orientation="horizontal",
            spacing=CARD_PADDING,
            padding=[CARD_PADDING, 4],
            size_hint=(1, None),
            height=48,
        )
        switch_lbl = Label(
            text="启用推送",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, 1),
            halign="left",
            valign="middle",
            text_size=(None, None),
        )
        switch_row.add_widget(switch_lbl)

        enabled_now = self._read("ntfy_enabled") == "1"
        toggle_btn = PixelButton(
            text="开" if enabled_now else "关",
            size_mode="small",
            size_hint=(None, 1),
            width=80,
            color=MINT_GREEN if enabled_now else COLORS["CARD_SHADOW"],
        )

        def _on_toggle(_btn: Any) -> None:
            new_val = "0" if self._read("ntfy_enabled") == "1" else "1"
            self._write("ntfy_enabled", new_val)
            toggle_btn.text = "开" if new_val == "1" else "关"
            toggle_btn.set_color(MINT_GREEN if new_val == "1" else COLORS["CARD_SHADOW"])

        toggle_btn.bind(on_press=_on_toggle)
        switch_row.add_widget(toggle_btn)
        box.add_widget(switch_row)

        # --- topic 输入 + 随机生成 ---
        topic_row = BoxLayout(
            orientation="horizontal",
            spacing=CARD_PADDING,
            padding=[CARD_PADDING, 4],
            size_hint=(1, None),
            height=48,
        )
        topic_lbl = Label(
            text="主题(topic)",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, 1),
            width=90,
            halign="left",
            valign="middle",
            text_size=(90, None),
        )
        topic_row.add_widget(topic_lbl)

        topic_input = PixelInput(
            hint_text="andy-soloist-xxxxxxx",
            value=self._read("ntfy_topic"),
            password=False,
            size_hint=(1, 1),
        )
        topic_input.bind(text=lambda _i, v: self._write("ntfy_topic", v))
        topic_row.add_widget(topic_input)

        rand_btn = PixelButton(
            text="随机",
            size_mode="small",
            size_hint=(None, 1),
            width=70,
            color=SKY_BLUE,
        )

        def _on_random(_btn: Any) -> None:
            import secrets
            new_topic = f"andy-soloist-{secrets.token_urlsafe(8)}"
            topic_input.text = new_topic
            self._write("ntfy_topic", new_topic)

        rand_btn.bind(on_press=_on_random)
        topic_row.add_widget(rand_btn)
        box.add_widget(topic_row)

        # --- 服务器地址（可选）---
        server_row = self._build_text_input_row(
            label="服务器",
            key="ntfy_server",
            hint="https://ntfy.sh",
            password=False,
        )
        box.add_widget(server_row)

        # --- 测试推送按钮 ---
        box.add_widget(Widget(size_hint=(1, None), height=GRID_UNIT))
        test_btn = PixelButton(
            text="测试推送",
            color=WARM_ORANGE,
            size_mode="normal",
            size_hint=(1, None),
        )
        test_btn.bind(on_press=lambda _: self._on_ntfy_test())
        box.add_widget(test_btn)

        return box

    def _on_ntfy_test(self) -> None:
        from kivy.app import App
        app = App.get_running_app()
        svc = getattr(app, "_ntfy_svc", None) if app else None
        if svc is None:
            self.show_toast("推送服务未初始化")
            return
        try:
            ok = svc.send_test()
        except Exception as e:
            Logger.error(f"SettingsScreen: ntfy 测试推送失败 {e}")
            ok = False
        self.show_toast("测试推送已发出，请到 ntfy 客户端查看" if ok else "测试推送失败：请检查 topic / 网络")

    # ------------------------------------------------------------------
    # 个性化激励语句组
    # ------------------------------------------------------------------

    def _build_encouragement_group(self) -> Widget:
        box = self._make_vbox()

        # 顶部输入行：输入框 + 添加按钮
        input_row = BoxLayout(
            orientation="horizontal",
            spacing=CARD_PADDING,
            padding=[CARD_PADDING, 4],
            size_hint=(1, None),
            height=48,
        )
        self._enc_input = PixelInput(
            hint_text="添加一条激励语句…",
            value="",
            password=False,
            size_hint=(1, 1),
        )
        input_row.add_widget(self._enc_input)

        add_btn = PixelButton(
            text="添加",
            size_mode="small",
            size_hint=(None, 1),
            width=70,
            color=MINT_GREEN,
        )
        add_btn.bind(on_press=lambda _b: self._on_encouragement_add())
        input_row.add_widget(add_btn)

        box.add_widget(input_row)

        # 列表容器（每次刷新清空再重建）
        self._enc_list_box = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            spacing=2,
        )
        self._enc_list_box.bind(minimum_height=self._enc_list_box.setter("height"))
        box.add_widget(self._enc_list_box)

        self._refresh_encouragement_list()
        return box

    def _refresh_encouragement_list(self) -> None:
        """重建列表 UI：先清空容器，再按当前数据重新生成行"""
        self._enc_list_box.clear_widgets()

        items: list[str] = []
        if self._settings_service:
            items = self._settings_service.get_user_encouragements()

        if not items:
            empty_lbl = Label(
                text="尚未添加，战报将随机使用内置 5 句",
                font_size=FONT_SIZE_SMALL,
                color=self._to_rgba(TEXT_GRAY),
                size_hint=(1, None),
                height=40,
                halign="center",
                valign="middle",
            )
            empty_lbl.bind(size=lambda lbl, _: setattr(lbl, "text_size", lbl.size))
            self._enc_list_box.add_widget(empty_lbl)
            return

        for idx, text in enumerate(items):
            row = BoxLayout(
                orientation="horizontal",
                spacing=CARD_PADDING,
                padding=[CARD_PADDING, 4],
                size_hint=(1, None),
                height=48,
            )
            lbl = Label(
                text=text,
                font_size=FONT_SIZE_BODY,
                color=self._to_rgba(TEXT_BROWN),
                size_hint=(1, 1),
                halign="left",
                valign="middle",
            )
            lbl.bind(size=lambda inst, _: setattr(inst, "text_size", (inst.width, None)))
            row.add_widget(lbl)

            del_btn = PixelButton(
                text="X",
                size_mode="small",
                size_hint=(None, 1),
                width=40,
                color=COLORS["CARD_SHADOW"],
            )
            del_btn.bind(on_press=lambda _b, i=idx: self._on_encouragement_delete(i))
            row.add_widget(del_btn)

            self._enc_list_box.add_widget(row)

    def _on_encouragement_add(self) -> None:
        """添加按钮：取输入框文本，校验后入库并刷新列表"""
        if not self._settings_service:
            self.show_toast("设置服务未初始化")
            return

        text = self._enc_input.text.strip()
        if not text:
            self.show_toast("请输入内容")
            return
        if len(text) > 100:
            self.show_toast("单条不能超过 100 字")
            return

        current = self._settings_service.get_user_encouragements()
        if text in current:
            self.show_toast("已存在相同语录")
            return

        try:
            self._settings_service.set_user_encouragements(current + [text])
        except Exception as e:  # noqa: BLE001
            Logger.error(f"SettingsScreen: 添加激励语录失败 {e}")
            self.show_toast("保存失败，请重试")
            return

        self._enc_input.text = ""
        self._refresh_encouragement_list()

    def _on_encouragement_delete(self, index: int) -> None:
        """删除按钮：按索引移除一条并刷新列表"""
        if not self._settings_service:
            return
        current = self._settings_service.get_user_encouragements()
        if 0 <= index < len(current):
            new_list = current[:index] + current[index + 1 :]
            try:
                self._settings_service.set_user_encouragements(new_list)
            except Exception as e:  # noqa: BLE001
                Logger.error(f"SettingsScreen: 删除激励语录失败 {e}")
                self.show_toast("删除失败，请重试")
                return
            self._refresh_encouragement_list()

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
        """显示开发面板（设置数据 + 虚拟时钟开关）。"""
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

        # 虚拟时钟开关
        time_toggle = PixelButton(
            text=self._time_panel_btn_text(),
            color=DOPAMINE_COLORS["sky"]["light"],
            size_mode="normal",
            size_hint=(None, None),
            size=(180, 42),
            pos_hint={"center_x": 0.5, "y": 1 - 0.24},
        )
        time_toggle.bind(on_press=lambda _: self._toggle_time_panel(time_toggle))
        card.add_widget(time_toggle)

        data_label = Label(
            text=json_text,
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, None),
            halign="left",
            valign="top",
        )

        scroll = ScrollView(
            size_hint=(0.9, 0.35),
            pos_hint={"x": 0.05, "y": 0.20},
            do_scroll_x=False,
            do_scroll_y=True,
        )
        scroll.add_widget(data_label)
        card.add_widget(scroll)

        scroll.bind(
            width=lambda _, w: setattr(data_label, 'text_size', (w * 0.95, None))
        )
        data_label.bind(
            texture_size=lambda _, ts: setattr(data_label, 'size', ts)
        )

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

    def _time_panel_btn_text(self) -> str:
        from kivy.app import App
        app = App.get_running_app()
        if app and getattr(app, "_time_panel_visible", False):
            return "关闭虚拟时钟"
        return "开启虚拟时钟"

    def _toggle_time_panel(self, btn: Any) -> None:
        from datetime import datetime, timedelta
        from kivy.app import App
        from app.utils.clock import SimulatedClock, SystemClock, set_clock, get_clock

        app = App.get_running_app()
        if app is None:
            return
        panel = getattr(app, "_time_panel", None)
        if panel is None:
            return

        if app._time_panel_visible:
            # 关闭 → 切回系统真实时钟
            set_clock(SystemClock())
            app._time_panel_visible = False
            panel.opacity = 0
            panel.height = 0
            # 恢复内容区高度(用真机动态拉伸后的画布高度, 而非固定 750 常量)
            if hasattr(app, "_sm"):
                app._sm.height = getattr(app, "_canvas_height", LOGICAL_HEIGHT)
        else:
            # 开启 → 自动设为本周一 07:00
            now = get_clock().now()
            monday = now - timedelta(days=now.weekday())
            clock = SimulatedClock()
            clock.set_date_and_time(monday.strftime("%Y-%m-%d"), "07:00")
            set_clock(clock)
            app._time_panel_visible = True
            panel.opacity = 1
            panel.height = 64
            panel._refresh_inputs()  # 同步输入框到模拟时钟时间
            # 内容区下移,面板在上方不遮挡
            if hasattr(app, "_sm"):
                app._sm.height = getattr(app, "_canvas_height", LOGICAL_HEIGHT) - 64
        btn.text = self._time_panel_btn_text()

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
            Rectangle(pos=(x + w - bw, y), size=(bw, h))
