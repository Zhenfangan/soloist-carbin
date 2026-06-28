"""PeriodPhotoStrip — 打卡主界面顶部相册条（2×2 或 3×2）"""

from __future__ import annotations

from pathlib import Path

from kivy.animation import Animation
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView

from app.ui.tokens import (
    CARD_PADDING,
    DOPAMINE_COLORS,
    FONT_SIZE_SMALL,
    GRID_UNIT,
    TEXT_GRAY,
)

_COLS_NORMAL = [("morning", "上午"), ("afternoon", "下午")]
_COLS_OVERTIME = [("morning", "上午"), ("afternoon", "下午"), ("evening", "晚上")]
_ACTIONS = [("in", "签到"), ("out", "签退")]

_PHOTO_BASE = Path("user_data/photos")
_MASCOT_LAST_FRAME = Path("app/ui/assets/animations/rabbit/frame_07.png")
_THUMB = 96
_LABEL_H = 18
_SLOT_H = _THUMB + _LABEL_H + 4
_STRIP_HEIGHT = _SLOT_H * 2 + GRID_UNIT


class PeriodPhotoStrip(BoxLayout):
    """2×2（普通）或 3×2（加班）相册格。

    无照片时折叠隐藏；有照片后展开，空格用 IP 最后一帧上下跳动占位。
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", 0)
        kwargs.setdefault("spacing", GRID_UNIT)
        kwargs.setdefault("padding", [CARD_PADDING, GRID_UNIT // 2])
        super().__init__(**kwargs)
        self.opacity = 0

        self._slots: dict[tuple[str, str], _PhotoSlot] = {}
        self._col_count = 0
        self._build_grid(2)

    def _build_grid(self, col_count: int) -> None:
        self.clear_widgets()
        self._slots.clear()
        self._col_count = col_count
        cols = _COLS_NORMAL if col_count == 2 else _COLS_OVERTIME

        for action, action_label in _ACTIONS:
            row_box = BoxLayout(
                orientation="horizontal",
                size_hint=(1, None),
                height=_SLOT_H,
                spacing=GRID_UNIT,
            )
            for period, period_label in cols:
                slot = _PhotoSlot(
                    period=period,
                    action=action,
                    label_text=f"{period_label}{action_label}",
                )
                self._slots[(period, action)] = slot
                row_box.add_widget(slot)
            self.add_widget(row_box)

    def refresh(self, date_str: str) -> None:
        """扫描照片目录，更新各格；自动切换 2/3 列；无照片时折叠。"""
        has_evening = (
            _find_photo(date_str, "evening", "in") is not None
            or _find_photo(date_str, "evening", "out") is not None
        )
        new_col_count = 3 if has_evening else 2
        if new_col_count != self._col_count:
            self._build_grid(new_col_count)

        photo_count = 0
        for (period, action), slot in self._slots.items():
            path = _find_photo(date_str, period, action)
            slot.set_photo(path)
            if path is not None:
                photo_count += 1

        if photo_count > 0:
            self.height = _STRIP_HEIGHT
            self.opacity = 1
        else:
            self.height = 0
            self.opacity = 0


def _find_photo(date: str, period: str, action: str) -> Path | None:
    base = _PHOTO_BASE / date
    for ext in ("jpg", "jpeg", "png"):
        p = base / f"{period}_{action}.{ext}"
        if p.exists():
            return p
    return None


class _PhotoSlot(BoxLayout):
    """单个打卡照片格子（缩略图 / IP 占位 + 小标签）。"""

    def __init__(self, period: str, action: str, label_text: str, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", _SLOT_H)
        kwargs.setdefault("spacing", 2)
        super().__init__(**kwargs)

        self._period = period
        self._action = action
        self._photo_path: Path | None = None

        self._thumb_area = BoxLayout(size_hint=(1, None), height=_THUMB)
        self._thumb_area.add_widget(_MascotBounce(size_hint=(1, 1)))

        self._lbl = Label(
            text=label_text,
            font_size=FONT_SIZE_SMALL - 2,
            color=_rgba(TEXT_GRAY),
            size_hint=(1, None),
            height=18,
            halign="center",
            valign="top",
        )
        self._lbl.bind(size=self._lbl.setter("text_size"))

        self.add_widget(self._thumb_area)
        self.add_widget(self._lbl)
        self.bind(on_touch_down=self._on_touch)

    def set_photo(self, path: Path | None) -> None:
        self._photo_path = path
        self._thumb_area.clear_widgets()
        if path:
            img = Image(
                source=path.as_posix(),
                size_hint=(1, 1),
                fit_mode="contain",
            )
            self._thumb_area.add_widget(img)
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt, i=img: i.reload(), 0)
            self._lbl.color = _rgba(DOPAMINE_COLORS["mint"]["light"])
        else:
            self._thumb_area.add_widget(_MascotBounce(size_hint=(1, 1)))
            self._lbl.color = _rgba(TEXT_GRAY)

    def _on_touch(self, instance, touch):
        if self._photo_path and self.collide_point(*touch.pos):
            PhotoPreviewDialog(photo_path=self._photo_path).open()
            return True
        return False


class _MascotBounce(Image):
    """IP 角色最后一帧 + 上下跳动动画，用于空相册格占位。"""

    bounce_y = NumericProperty(0)

    def __init__(self, **kwargs):
        kwargs.setdefault("source", _MASCOT_LAST_FRAME.as_posix())
        kwargs.setdefault("fit_mode", "contain")
        super().__init__(**kwargs)

        from kivy.graphics import PopMatrix, PushMatrix, Translate
        with self.canvas.before:
            PushMatrix()
            self._translate = Translate(0, 0)
        with self.canvas.after:
            PopMatrix()

        self._anim = (
            Animation(bounce_y=8, duration=0.5, t="in_out_sine")
            + Animation(bounce_y=0, duration=0.5, t="in_out_sine")
        )
        self._anim.repeat = True
        self._anim.start(self)

    def on_bounce_y(self, _instance: object, value: float) -> None:
        self._translate.y = value

    def on_parent(self, _instance: object, parent: object) -> None:
        if parent is None:
            self._anim.stop(self)


class PhotoPreviewDialog(ModalView):
    """全屏查看打卡照片。"""

    def __init__(self, photo_path: Path, **kwargs):
        kwargs.setdefault("size_hint", (0.95, 0.85))
        super().__init__(**kwargs)

        from kivy.uix.button import Button

        layout = BoxLayout(orientation="vertical", spacing=GRID_UNIT, padding=GRID_UNIT)
        img = Image(
            source=photo_path.as_posix(),
            size_hint=(1, 1),
            fit_mode="contain",
        )
        close_btn = Button(
            text="关闭",
            size_hint=(1, None),
            height=44,
        )
        close_btn.bind(on_press=lambda _: self.dismiss())

        layout.add_widget(img)
        layout.add_widget(close_btn)
        self.add_widget(layout)


def _rgba(hex_color: str, alpha: float = 1.0) -> tuple:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, alpha)
