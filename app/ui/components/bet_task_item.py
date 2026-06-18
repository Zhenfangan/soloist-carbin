"""BetTaskItem — 单条对赌任务行。

2px 边框卡片，显示任务描述 + 目标数量 + 当前进度 + PixelCheckbox，
支持进度增量、右滑完成、左滑删除。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from kivy.clock import Clock
from kivy.graphics import Color, Line, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.widget import Widget

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
_EDIT_BTN_WIDTH: float = 64.0
_DELETE_BTN_WIDTH: float = 64.0
_ACTION_AREA_WIDTH: float = _EDIT_BTN_WIDTH + _DELETE_BTN_WIDTH
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
        on_edit: Callable[[int], Any] | None = None,
        on_complete: Callable[[int], Any] | None = None,
        on_delete: Callable[[int], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = _TASK_CARD_HEIGHT
        self._task = task
        self._on_progress_cb = on_progress
        self._on_edit_cb = on_edit
        self._on_complete_cb = on_complete
        self._on_delete_cb = on_delete

        # 触摸状态
        self._start_x: float = 0.0
        self._start_y: float = 0.0
        self._swiping: bool = False
        self._delete_visible: bool = False
        self._completed_anim: bool = False
        self._content_offset: float = 0.0
        # 防止首次布局前 Label 在 (0,0) 闪现 — opacity=0 直到第一次 _redraw
        self._layout_initialized: bool = False

        # ---- 复选框 (Widget + canvas 矩形, 跟主页 PixelCheckbox 视觉一致;
        # 不用 PixelCheckbox widget 因为 BetTaskItem on_touch_down 自己 consume,
        # 触摸由 _handle_tap 统一处理) ----
        self._check_box = Widget(
            size_hint=(None, None),
            size=(20, 20),
            opacity=0,
        )
        self._check_box.checked = bool(task.is_completed)
        self._check_box.bind(pos=self._redraw_check_box, size=self._redraw_check_box)

        # ---- 任务描述 ----
        desc_text = task.task_desc
        if task.is_completed:
            desc_text = f"[s]{desc_text}[/s]"
        self._desc_label = Label(
            text=desc_text,
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_GRAY if task.is_completed else TEXT_BROWN),
            size_hint=(None, None),
            size=(160, 32),
            halign="left",
            valign="middle",
            markup=True,
            shorten=True,
            shorten_from="right",
            opacity=0,
        )

        # ---- 目标数量徽章 "×N" ----
        self._qty_label = Label(
            text=f"×{task.target_qty}",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(DOPAMINE_COLORS["warm_orange"]["light"]),
            size_hint=(None, None),
            size=(40, 20),
            halign="center",
            valign="middle",
            opacity=0,
        )

        # ---- 当前进度 "current/target" ----
        self._progress_label = Label(
            text=f"{task.current_qty}/{task.target_qty}",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, None),
            size=(48, 20),
            halign="center",
            valign="middle",
            opacity=0,
        )

        # ---- [-1] 按钮 (允许误操作回退) ----
        self._minus_btn = Label(
            text="-1",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, None),
            size=(28, 32),
            halign="center",
            valign="middle",
            opacity=0,
        )
        self._minus_btn.bind(pos=self._redraw_minus_btn, size=self._redraw_minus_btn)

        # ---- [+1] 按钮 ----
        self._plus_btn = Label(
            text="+1",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, None),
            size=(32, 32),
            halign="center",
            valign="middle",
            opacity=0,
        )
        self._plus_btn.bind(pos=self._redraw_plus_btn, size=self._redraw_plus_btn)

        # ---- 橙色编辑按钮 (隐藏，左滑显示) ----
        self._edit_btn = Label(
            text="编辑",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba("#FFFFFF"),
            size_hint=(None, None),
            size=(_EDIT_BTN_WIDTH, _TASK_CARD_HEIGHT),
            halign="center",
            valign="middle",
        )
        self._edit_btn.opacity = 0
        self._edit_btn.bind(pos=self._redraw_edit_btn, size=self._redraw_edit_btn)

        # ---- 红色删除按钮 (隐藏，左滑显示) ----
        self._delete_btn = Label(
            text="删除",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba("#FFFFFF"),
            size_hint=(None, None),
            size=(_DELETE_BTN_WIDTH, _TASK_CARD_HEIGHT),
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

        # 添加所有子 widget (直接作为 self 的孩子，去掉 _content 中间层)
        self.add_widget(self._edit_btn)
        self.add_widget(self._delete_btn)
        self.add_widget(self._check_box)
        self.add_widget(self._desc_label)
        self.add_widget(self._qty_label)
        self.add_widget(self._progress_label)
        self.add_widget(self._minus_btn)
        self.add_widget(self._plus_btn)
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
        self._check_box.checked = bool(self._task.is_completed)
        self._redraw_check_box()
        desc = self._task.task_desc
        self._desc_label.text = f"[s]{desc}[/s]" if self._task.is_completed else desc
        self._desc_label.color = self._to_rgba(TEXT_GRAY if self._task.is_completed else TEXT_BROWN)
        self._progress_label.text = f"{self._task.current_qty}/{self._task.target_qty}"

    # ---- 触摸处理 ----

    def on_touch_down(self, touch: Any) -> bool:
        if self.collide_point(*touch.pos):
            self._start_x = touch.x
            self._start_y = touch.y
            self._swiping = False
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

        if self.collide_point(*touch.pos):
            self._handle_tap(touch)
            return True

        return cast(bool, super().on_touch_up(touch))

    def _handle_tap(self, touch: Any) -> None:
        """处理点击 — touch 直接比子 widget 的绝对窗口 bounding box。"""
        tx, ty = touch.x, touch.y

        # [+1] 按钮
        px, py = self._plus_btn.pos
        pw, ph = self._plus_btn.size
        if px <= tx <= px + pw and py <= ty <= py + ph:
            self._do_increment()
            return

        # [-1] 按钮
        mx, my = self._minus_btn.pos
        mw, mh = self._minus_btn.size
        if mx <= tx <= mx + mw and my <= ty <= my + mh:
            self._do_decrement()
            return

        # 复选框区域仅显示，不可交互

        # 编辑/删除按钮 (左滑露出时可见)
        if self._delete_visible:
            ex, ey = self._edit_btn.pos
            ew, eh = self._edit_btn.size
            if ex <= tx <= ex + ew and ey <= ty <= ey + eh:
                self._do_edit()
                return
            dx, dy = self._delete_btn.pos
            dw, dh = self._delete_btn.size
            if dx <= tx <= dx + dw and dy <= ty <= dy + dh:
                self._do_delete()
                return
            # 露出状态点其他区域 -> snap 回收
            self._snap_back()
            return

        # 描述区域 tap -> 弹出操作菜单
        dx, dy = self._desc_label.pos
        dw, dh = self._desc_label.size
        if dx <= tx <= dx + dw and dy <= ty <= dy + dh:
            self._show_action_menu()
            return

    def _do_increment(self) -> None:
        """进度 +1 (允许超额: 已完成的任务可继续递增)。

        回调传 delta=+1, 与 service.update_task_progress 的增量语义对齐。
        """
        cur = self._task.current_qty + 1
        target = self._task.target_qty
        already_done = self._task.is_completed
        self._task.current_qty = cur
        if cur >= target and not already_done:
            self._task.is_completed = 1
            self._refresh_desc()
            if self._on_complete_cb and self._task.id is not None:
                self._on_complete_cb(self._task.id)
        else:
            self._refresh_desc()
        if self._on_progress_cb and self._task.id is not None:
            self._on_progress_cb(self._task.id, 1)

    def _do_decrement(self) -> None:
        """进度 -1 (下限 0; 若回退到低于 target 取消完成态)。

        回调传 delta=-1, service SQL 自动 MAX(0, x-1) + 双向 is_completed 维护。
        """
        if self._task.current_qty <= 0:
            return
        cur = self._task.current_qty - 1
        target = self._task.target_qty
        self._task.current_qty = cur
        if cur < target and self._task.is_completed:
            self._task.is_completed = 0
        self._refresh_desc()
        if self._on_progress_cb and self._task.id is not None:
            self._on_progress_cb(self._task.id, -1)

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
        if self.parent:
            self.parent.remove_widget(self)

    def _do_edit(self) -> None:
        """触发编辑回调 (由父组件 BetScreen 弹出 AddTaskDialog 编辑模式)。"""
        if self._on_edit_cb and self._task.id is not None:
            self._on_edit_cb(self._task.id)
        self._snap_back()

    def _show_action_menu(self) -> None:
        """弹出任务操作菜单（修改/删除/取消）。"""
        from app.ui.components.pixel_dialog import TaskActionDialog
        dialog = TaskActionDialog(
            task_desc=self._task.task_desc,
            on_edit=self._do_edit,
            on_delete=self._do_delete,
        )
        dialog.open()

    # ---- Swipe 动画 ----

    def _update_swipe_position(self) -> None:
        """根据 swipe offset 更新所有子 widget 的位置 (左滑露出编辑+删除两按钮)。"""
        clamped = max(-_ACTION_AREA_WIDTH, min(150, self._content_offset))
        self._layout_labels(clamped)
        if clamped < -10:
            self._delete_visible = True
            self._edit_btn.opacity = 1
            self._delete_btn.opacity = 1
            # edit 在左, delete 在右
            self._edit_btn.pos = (self.x + self.width + clamped, self.y)
            self._delete_btn.pos = (
                self.x + self.width + clamped + _EDIT_BTN_WIDTH,
                self.y,
            )
        else:
            self._delete_visible = False
            self._edit_btn.opacity = 0
            self._delete_btn.opacity = 0

    def _snap_back(self) -> None:
        """弹回原位。"""
        self._content_offset = 0
        self._delete_visible = False
        self._edit_btn.opacity = 0
        self._delete_btn.opacity = 0
        self._layout_labels(0)

    def _show_delete(self) -> None:
        """左滑: 露出编辑 + 删除两个按钮。"""
        self._delete_visible = True
        self._edit_btn.opacity = 1
        self._delete_btn.opacity = 1
        clamped = -_ACTION_AREA_WIDTH
        self._content_offset = clamped
        self._layout_labels(clamped)
        self._edit_btn.pos = (self.x + self.width + clamped, self.y)
        self._delete_btn.pos = (
            self.x + self.width + clamped + _EDIT_BTN_WIDTH,
            self.y,
        )

    def _animate_complete(self) -> None:
        """右滑: 完成动画。"""
        if self._completed_anim:
            return
        self._completed_anim = True

        self._task.is_completed = 1
        self._refresh_desc()
        if self._on_complete_cb and self._task.id is not None:
            self._on_complete_cb(self._task.id)

        try:
            frames = SpriteLoader.load_sprite("wangzai")
            if frames:
                self._wangzai_img.texture = frames[0].texture
        except Exception:
            pass

        self._wangzai_img.size = (48, 48)
        self._wangzai_img.opacity = 1
        self._wangzai_img.pos = (self.x + self.width, self.y + (self.height - 48) / 2)

        def _slide_in(dt: float, step: int) -> None:
            if not self._wangzai_img:
                return
            progress = (step + 1) / 8
            img_x = self.x + self.width - 48 * (1 - progress)
            self._wangzai_img.pos = (img_x, self.y + (self.height - 48) / 2)
            try:
                frames = SpriteLoader.load_sprite("wangzai")
                if frames and len(frames) > 1:
                    frame_idx = step % min(2, len(frames))
                    self._wangzai_img.texture = frames[frame_idx].texture
            except Exception:
                pass

        for i in range(8):
            Clock.schedule_once(lambda dt, s=i: _slide_in(dt, s), i * 0.05)

        def _fade_content(dt: float) -> None:
            self._layout_labels(20)
            self._snap_back()
            self._completed_anim = False
            self._wangzai_img.opacity = 0

        Clock.schedule_once(_fade_content, _ANIM_DURATION)

    # ---- 布局 ----

    def _layout_labels(self, offset: float) -> None:
        """排列所有子 Label — 用绝对窗口坐标 (Kivy widget 默认坐标系)。

        子 widget 不是 RelativeLayout 的孩子, pos 是窗口绝对坐标,
        必须加上 self.x / self.y 偏移; offset 是 swipe 水平动画位移。

        布局: [check] desc... [×N] [N/M] [-1] [+1]
                36   动态     40    48   28   32
        """
        sx = self.x
        sy = self.y
        h = self.height
        w = self.width

        # checkbox 20x20 在原 36x32 位置居中: x+8 让中心点对齐, y 居中
        self._check_box.pos = (sx + offset + GRID_UNIT + 8, sy + (h - 20) / 2)
        self._desc_label.pos = (sx + offset + GRID_UNIT + 40, sy + (h - 32) / 2)
        # desc 宽度: 留出右侧 ×N(40)+N/M(48)+-1(28)+1(32)+ 间隔 ~ 160px
        self._desc_label.width = max(60, w - 220)
        self._qty_label.pos = (sx + offset + w - 152, sy + (h - 20) / 2)
        self._progress_label.pos = (sx + offset + w - 110, sy + (h - 20) / 2)
        self._minus_btn.pos = (sx + offset + w - 64, sy + (h - 32) / 2)
        self._plus_btn.pos = (sx + offset + w - 34, sy + (h - 32) / 2)

    # ---- Canvas 绘制 ----

    def _redraw(self, *args: Any) -> None:
        """绘制 2px 边框 + 阴影 + 排列子 widget。"""
        self._layout_labels(self._content_offset)

        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        bw = BORDER_WIDTH

        with self.canvas.before:
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

        # 首次布局完成后开启 widget 可见性 (防止 (0,0) 闪现)
        if not self._layout_initialized and w > 0 and h > 0:
            self._layout_initialized = True
            self._check_box.opacity = 1
            self._desc_label.opacity = 1
            self._qty_label.opacity = 1
            self._progress_label.opacity = 1
            self._minus_btn.opacity = 1
            self._plus_btn.opacity = 1
            self._redraw_check_box()

    def _redraw_check_box(self, *args: Any) -> None:
        """仅在完成时绘制对勾，不画方框，不可交互，只读显示完成状态。"""
        self._check_box.canvas.before.clear()
        if self._check_box.opacity <= 0 or not self._check_box.checked:
            return
        x, y = self._check_box.pos
        with self._check_box.canvas.before:
            Color(*self._to_rgba(DOPAMINE_COLORS["mint"]["light"]))
            Line(
                points=[x + 4, y + 10, x + 8, y + 6, x + 16, y + 14],
                width=2,
            )

    def _redraw_plus_btn(self, *args: Any) -> None:
        """绘制 [+1] 按钮像素边框 — 用 plus_btn 绝对窗口坐标。"""
        self._draw_btn_border(self._plus_btn)

    def _redraw_minus_btn(self, *args: Any) -> None:
        """绘制 [-1] 按钮像素边框 — 同 [+1] 风格。"""
        self._draw_btn_border(self._minus_btn)

    def _draw_btn_border(self, btn: Label) -> None:
        """通用像素按钮边框绘制 (内凹: 暗面 bottom/right, 亮面 top/left)。"""
        btn.canvas.before.clear()
        x, y = btn.pos
        w, h = btn.size
        bw = BORDER_WIDTH
        with btn.canvas.before:
            Color(*self._to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(x, y), size=(w, h))
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(x, y + h - bw), size=(w, bw))
            Rectangle(pos=(x, y), size=(bw, h))
            Color(*self._to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(x, y), size=(w, bw))
            Rectangle(pos=(x + w - bw, y), size=(bw, h))

    def _redraw_delete_btn(self, *args: Any) -> None:
        """绘制删除按钮红色背景 — 用 delete_btn 绝对窗口坐标。"""
        self._delete_btn.canvas.before.clear()
        x, y = self._delete_btn.pos
        w, h = self._delete_btn.size
        if self._delete_visible:
            with self._delete_btn.canvas.before:
                Color(*self._to_rgba("#FF5070"))
                Rectangle(pos=(x, y), size=(w, h))

    def _redraw_edit_btn(self, *args: Any) -> None:
        """绘制编辑按钮橙色背景 — 用 edit_btn 绝对窗口坐标。"""
        self._edit_btn.canvas.before.clear()
        x, y = self._edit_btn.pos
        w, h = self._edit_btn.size
        if self._delete_visible:
            with self._edit_btn.canvas.before:
                Color(*self._to_rgba(DOPAMINE_COLORS["warm_orange"]["light"]))
                Rectangle(pos=(x, y), size=(w, h))
