"""BetTaskItem — 单条对赌任务行。

2px 边框卡片，显示任务描述 + 目标数量 + 当前进度 + PixelCheckbox，
支持进度增量、右滑完成、左滑删除。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label

from app.models.ledger import BetTask
from app.ui.assets.loader import SpriteLoader
from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_WHITE,
    COLORS,
    DOPAMINE_COLORS,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    GRID_UNIT,
    TEXT_BROWN,
    TEXT_GRAY,
)

# 常量
_SWIPE_THRESHOLD: float = 60.0
_DELETE_BTN_WIDTH: float = 80.0
_ANIM_DURATION: float = 0.4
_TASK_CARD_HEIGHT: float = 72.0


class BetTaskItem(FloatLayout):  # type: ignore[misc]
    """单条对赌任务行。

    属性:
        task: BetTask 数据对象
        on_progress: 进度变化回调 (task_id, current_qty) -> None
        on_complete: 任务完成回调 (task_id) -> None
        on_delete: 任务删除回调 (task_id) -> None
    """

    def __init__(
        self,
        task: BetTask,
        on_progress: Callable[[int, int], Any] | None = None,
        on_complete: Callable[[int], Any] | None = None,
        on_delete: Callable[[int], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = _TASK_CARD_HEIGHT
        self._task = task
        self._on_progress_cb = on_progress
        self._on_complete_cb = on_complete
        self._on_delete_cb = on_delete

        # 触摸状态
        self._start_x: float = 0.0
        self._start_y: float = 0.0
        self._swiping: bool = False
        self._delete_visible: bool = False
        self._completed_anim: bool = False
        self._content_offset: float = 0.0

        # ---- 内容容器 (swipe offset 动画) ----
        # opacity=0 直到第一次 _redraw 完成布局，防止 Label 在 (0,0) 处闪现
        self._content = FloatLayout(
            size_hint=(1, 1),
            opacity=0,
        )
        self._content.bind(pos=self._redraw_content)

        # ---- 复选框 (Label, 非 PixelCheckbox - 避免触摸冲突) ----
        self._check_label = Label(
            text="[x]" if task.is_completed else "[ ]",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(
                DOPAMINE_COLORS["mint"]["light"] if task.is_completed else TEXT_BROWN
            ),
            size_hint=(None, 1),
            width=36,
            halign="center",
            valign="middle",
        )

        # ---- 任务描述 ----
        desc_text = task.task_desc
        if task.is_completed:
            desc_text = f"[s]{desc_text}[/s]"
        self._desc_label = Label(
            text=desc_text,
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_GRAY if task.is_completed else TEXT_BROWN),
            size_hint=(None, 1),
            width=200,
            halign="left",
            valign="middle",
            markup=True,
            shorten=True,
            shorten_from="right",
        )

        # ---- 目标数量徽章 "×N" ----
        self._qty_label = Label(
            text=f"×{task.target_qty}",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(DOPAMINE_COLORS["warm_orange"]["light"]),
            size_hint=(None, 1),
            width=40,
            halign="center",
            valign="middle",
        )

        # ---- 当前进度 "current/target" ----
        self._progress_label = Label(
            text=f"{task.current_qty}/{task.target_qty}",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, 1),
            width=48,
            halign="center",
            valign="middle",
        )

        # ---- [+1] 按钮 ----
        self._plus_btn = Label(
            text="+1",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, 1),
            width=32,
            height=32,
            halign="center",
            valign="middle",
        )
        self._plus_btn.bind(pos=self._redraw_plus_btn, size=self._redraw_plus_btn)

        # 组装内容
        self._content.add_widget(self._check_label)
        self._content.add_widget(self._desc_label)
        self._content.add_widget(self._qty_label)
        self._content.add_widget(self._progress_label)
        self._content.add_widget(self._plus_btn)

        # ---- 红色删除按钮 (隐藏，左滑显示) ----
        self._delete_btn = Label(
            text="删除",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba("#FFFFFF"),
            size_hint=(None, 1),
            width=_DELETE_BTN_WIDTH,
            halign="center",
            valign="middle",
        )
        self._delete_btn.opacity = 0
        self._delete_btn.bind(pos=self._redraw_delete_btn, size=self._redraw_delete_btn)

        # ---- 旺仔完成动画 (隐藏，右滑显示) ----
        self._wangzai_img = Image(
            size_hint=(None, None),
            size=(48, 48),
            opacity=0,
            allow_stretch=True,
            keep_ratio=True,
        )

        # 添加所有子 widget
        self.add_widget(self._delete_btn)
        self.add_widget(self._content)
        self.add_widget(self._wangzai_img)

        self.bind(pos=self._redraw, size=self._redraw)

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (
            int(h[0:2], 16) / 255.0,
            int(h[2:4], 16) / 255.0,
            int(h[4:6], 16) / 255.0,
            alpha,
        )

    @property
    def task(self) -> BetTask:
        return self._task

    def _refresh_desc(self) -> None:
        """刷新 UI 显示以匹配 task 状态。"""
        self._check_label.text = "☑" if self._task.is_completed else "☐"
        chk_color = DOPAMINE_COLORS["mint"]["light"] if self._task.is_completed else TEXT_BROWN
        self._check_label.color = self._to_rgba(chk_color)
        desc = self._task.task_desc
        self._desc_label.text = f"[s]{desc}[/s]" if self._task.is_completed else desc
        self._desc_label.color = self._to_rgba(TEXT_GRAY if self._task.is_completed else TEXT_BROWN)
        self._progress_label.text = f"{self._task.current_qty}/{self._task.target_qty}"

    # ---- 触摸处理 (延迟 Grab → 不阻断 ScrollView 垂直滚动) ----

    def on_touch_down(self, touch: Any) -> bool:
        if self.collide_point(*touch.pos):
            self._start_x = touch.x
            self._start_y = touch.y
            self._swiping = False
            # 不在 down 时 grab，让 ScrollView 先响应垂直滚动
            return True
        return cast(bool, super().on_touch_down(touch))

    def on_touch_move(self, touch: Any) -> bool:
        if touch.grab_current is self:
            dx = touch.x - self._start_x
            dy = abs(touch.y - self._start_y)

            if not self._swiping and abs(dx) > 15 and abs(dx) > dy * 2:
                self._swiping = True

            if self._swiping:
                self._content_offset = dx
                self._update_swipe_position()
            return True

        # 尚未 grab: 检测是否为横向滑动，是则 grab 并接管
        if self.collide_point(*touch.pos):
            dx = abs(touch.x - self._start_x)
            dy = abs(touch.y - self._start_y)
            if dx > 15 and dx > dy * 2:
                touch.grab(self)
                self._swiping = True
                self._content_offset = touch.x - self._start_x
                self._update_swipe_position()
                return True

        return cast(bool, super().on_touch_move(touch))

    def on_touch_up(self, touch: Any) -> bool:
        if touch.grab_current is self:
            touch.ungrab(self)
            if self._completed_anim:
                self._content_offset = 0
                return True

            if not self._swiping:
                self._handle_tap(touch)
            else:
                dx = touch.x - self._start_x
                if dx > _SWIPE_THRESHOLD and not self._task.is_completed:
                    self._animate_complete()
                elif dx < -_SWIPE_THRESHOLD and not self._delete_visible:
                    self._show_delete()
                else:
                    self._snap_back()
            return True

        # 未被 grab 的 touch_up: 视为 tap
        if self.collide_point(*touch.pos):
            self._handle_tap(touch)
            return True

        return cast(bool, super().on_touch_up(touch))

    def _handle_tap(self, touch: Any) -> None:
        """处理点击事件 — 判断点击区域。"""
        # 触摸点在 self 坐标系中的位置
        tx = touch.x - self.x
        ty = touch.y - self.y

        # [+1] 按钮区域
        btn_x = self._plus_btn.x + self._content.x
        btn_y = self._plus_btn.y + self._content.y
        if (
            btn_x <= tx <= btn_x + self._plus_btn.width
            and btn_y <= ty <= btn_y + self._plus_btn.height
        ):
            self._do_increment()
            return

        # 复选框区域
        cb_x = self._check_label.x + self._content.x
        cb_y = self._check_label.y + self._content.y
        if (
            cb_x <= tx <= cb_x + self._check_label.width
            and cb_y <= ty <= cb_y + self._check_label.height
        ):
            self._do_toggle_check()
            return

        # 删除按钮区域 (如果可见)
        if self._delete_visible:
            db_x = self._delete_btn.x
            db_y = self._delete_btn.y
            if (
                db_x <= tx <= db_x + self._delete_btn.width
                and db_y <= ty <= db_y + self._delete_btn.height
            ):
                self._do_delete()
                return

    def _do_increment(self) -> None:
        """进度 +1。"""
        if self._task.is_completed:
            return
        cur = self._task.current_qty + 1
        target = self._task.target_qty
        self._task.current_qty = cur
        if cur >= target:
            self._task.is_completed = 1
            self._refresh_desc()
            if self._on_complete_cb and self._task.id is not None:
                self._on_complete_cb(self._task.id)
        else:
            self._refresh_desc()
        if self._on_progress_cb and self._task.id is not None:
            self._on_progress_cb(self._task.id, cur)

    def _do_toggle_check(self) -> None:
        """切换完成状态。"""
        self._task.is_completed = 1 if not self._task.is_completed else 0
        self._refresh_desc()
        if self._task.is_completed and self._on_complete_cb and self._task.id is not None:
            self._on_complete_cb(self._task.id)

    def _do_delete(self) -> None:
        """删除任务。"""
        if self._on_delete_cb and self._task.id is not None:
            self._on_delete_cb(self._task.id)
        # 从父容器移除自身
        if self.parent:
            self.parent.remove_widget(self)

    # ---- Swipe 动画 ----

    def _update_swipe_position(self) -> None:
        """根据 swipe offset 更新内容位置。"""
        clamped = max(-_DELETE_BTN_WIDTH, min(150, self._content_offset))
        self._content.pos = (self.x + clamped, self.y)
        # 控制删除按钮可见度
        if clamped < -10:
            self._delete_visible = True
            self._delete_btn.opacity = 1
            self._delete_btn.pos = (
                self.x + self.width + clamped,
                self.y,
            )
        else:
            self._delete_visible = False
            self._delete_btn.opacity = 0

    def _snap_back(self) -> None:
        """弹回原位。"""
        self._content_offset = 0
        self._delete_visible = False
        self._delete_btn.opacity = 0
        self._content.pos = (self.x, self.y)
        self._redraw()

    def _show_delete(self) -> None:
        """左滑: 露出删除按钮。"""
        self._delete_visible = True
        self._delete_btn.opacity = 1
        clamped = -_DELETE_BTN_WIDTH
        self._content_offset = clamped
        self._content.pos = (self.x + clamped, self.y)
        self._delete_btn.pos = (
            self.x + self.width + clamped,
            self.y,
        )

    def _animate_complete(self) -> None:
        """右滑: 完成动画 — 划线 + 灰色 + 旺仔从侧边滑入。"""
        if self._completed_anim:
            return
        self._completed_anim = True

        # 标记完成
        self._task.is_completed = 1
        self._refresh_desc()
        if self._on_complete_cb and self._task.id is not None:
            self._on_complete_cb(self._task.id)

        # 加载旺仔 sprite
        try:
            frames = SpriteLoader.load_sprite("wangzai")
            if frames:
                self._wangzai_img.texture = frames[0].texture
        except Exception:
            pass

        self._wangzai_img.size = (48, 48)
        self._wangzai_img.opacity = 1
        # 从右侧滑入
        self._wangzai_img.pos = (self.x + self.width, self.y + (self.height - 48) / 2)

        def _slide_in(dt: float, step: int) -> None:
            if not self._wangzai_img or not self._content:
                return
            progress = (step + 1) / 8
            img_x = self.x + self.width - 48 * (1 - progress)
            self._wangzai_img.pos = (img_x, self.y + (self.height - 48) / 2)
            # 旺仔摇尾 (切换帧)
            try:
                frames = SpriteLoader.load_sprite("wangzai")
                if frames and len(frames) > 1:
                    frame_idx = step % min(2, len(frames))
                    self._wangzai_img.texture = frames[frame_idx].texture
            except Exception:
                pass

        for i in range(8):
            Clock.schedule_once(lambda dt, s=i: _slide_in(dt, s), i * 0.05)

        # 内容灰色 + 偏移
        def _fade_content(dt: float) -> None:
            self._content.pos = (self.x + 20, self.y)
            self._snap_back()
            self._completed_anim = False
            # 隐藏旺仔
            self._wangzai_img.opacity = 0

        Clock.schedule_once(_fade_content, _ANIM_DURATION)

    # ---- Canvas 绘制 ----

    def _redraw(self, *args: Any) -> None:
        """绘制整体 2px 边框 + 阴影。"""
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        bw = BORDER_WIDTH

        with self.canvas.before:
            # 阴影
            Color(*self._to_rgba(COLORS["SHADOW_BLACK"]))
            Rectangle(pos=(x + 2, y - 2), size=(w, h))
            # 卡片背景
            Color(*self._to_rgba(CARD_WHITE))
            Rectangle(pos=(x, y), size=(w, h))
            # 亮面边框 top+left
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(x, y + h - bw), size=(w, bw))
            Rectangle(pos=(x, y), size=(bw, h))
            # 暗面边框 bottom+right
            Color(*self._to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(x, y), size=(w, bw))
            Rectangle(pos=(x + w - bw, y), size=(bw, h))

        self._layout_children()
        # 确保内容首次布局后可见
        self._content.opacity = 1

    def _redraw_content(self, *args: Any) -> None:
        """内容位置更新时重绘。"""
        self._layout_children()

    def _layout_children(self) -> None:
        """排列内容中的子 widget。"""
        cx = self._content.x
        cy = self._content.y
        cw = self._content.width
        ch = self._content.height

        self._check_label.pos = (cx + GRID_UNIT, cy + (ch - 24) / 2)
        self._desc_label.pos = (cx + GRID_UNIT + 40, cy + (ch - 20) / 2)
        self._desc_label.width = cw * 0.45

        self._qty_label.pos = (cx + cw - 120, cy + (ch - 20) / 2)
        self._progress_label.pos = (cx + cw - 80, cy + (ch - 20) / 2 + 2)
        self._plus_btn.pos = (cx + cw - 36, cy + (ch - 32) / 2)

    def _redraw_plus_btn(self, *args: Any) -> None:
        """绘制 [+1] 按钮像素边框。"""
        self._plus_btn.canvas.before.clear()
        x, y = self._plus_btn.pos
        w, h = self._plus_btn.size
        bw = BORDER_WIDTH

        with self._plus_btn.canvas.before:
            Color(*self._to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(x, y), size=(w, h))
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(x, y + h - bw), size=(w, bw))
            Rectangle(pos=(x, y), size=(bw, h))
            Color(*self._to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(x, y), size=(w, bw))
            Rectangle(pos=(x + w - bw, y), size=(bw, h))

    def _redraw_delete_btn(self, *args: Any) -> None:
        """绘制删除按钮红色背景。"""
        self._delete_btn.canvas.before.clear()
        x, y = self._delete_btn.pos
        w, h = self._delete_btn.size

        if self._delete_visible:
            with self._delete_btn.canvas.before:
                Color(*self._to_rgba("#FF5070"))
                Rectangle(pos=(x, y), size=(w, h))
