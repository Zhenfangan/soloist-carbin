"""ReportPreview — 战报全屏弹层。

视觉规格 (真机高清，无文本 emoji):
  ① 品牌头部    — 啦啦队小猫 IP + Soloist Cabin
  ② 日期卡      — 黄边圆角，大字日期 + 各时段时间
  ③ 自律时光机  — 4/6 帧，双重线边框 + 像素阴影 + PNG 图标标签
  ④ 奖励联动    — 达标浅青 / 未达标暖灰，PNG 角标装饰
  ⑤ 鼓励语接口  — 柴犬 IP 左右夹持，留扩展接口
  ⑥ 底部按钮    — 关闭 + 保存到相册

所有视觉元素严禁使用文本 emoji（SmileySans 不含 emoji 字形 → 豆腐块）。
装饰一律使用项目 PNG 资产（增量叠加，不触碰打卡/奖惩核心逻辑）。
"""

from __future__ import annotations

import os
import random
from pathlib import Path
from typing import TYPE_CHECKING, Any

from kivy.animation import Animation
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scatter import Scatter
from kivy.uix.scrollview import ScrollView

from app.services.report_service import ENCOURAGEMENTS
from app.ui.assets.landscape import BG_LANDSCAPE, get_grass_overlay_path
from app.ui.assets.loader import apply_pixel_filter
from app.ui.components.pixel_button import PixelButton
from app.ui.scale_util import scale_wrap
from app.ui.tokens import (
    BG_CREAM,
    CARD_PADDING,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    GRASS_INSET,
    GRID_UNIT,
    LOGICAL_HEIGHT,
    LOGICAL_WIDTH,
    PRIMARY_YELLOW,
    TEXT_BROWN,
    TEXT_GRAY,
)

if TYPE_CHECKING:
    from app.models.report import ReportData

# ── 战报专用颜色 ─────────────────────────────────────────────────
_COLOR_REWARD_BG = "#C8F5EC"   # 达标看板：浅青
_COLOR_UNMET_BG  = "#E8E0D8"   # 未达标看板：暖灰

# 每格双重线边框配色 (outer, inner, shadow, content_bg)
_SLOT_FRAME: dict[tuple[str, str], tuple[str, str, str, str]] = {
    ("morning",   "in"):  ("#FF9040", "#FFD4A0", "#C07028", "#FFF8F0"),
    ("morning",   "out"): ("#FFE030", "#FFF4A0", "#C8A800", "#FFFEF0"),
    ("afternoon", "in"):  ("#50E8B0", "#A8F4D8", "#28C888", "#F0FFF8"),
    ("afternoon", "out"): ("#60C8FF", "#B0E0FF", "#38A0D8", "#F0F8FF"),
    ("evening",   "in"):  ("#B090F0", "#D8C8FF", "#8060C8", "#F8F4FF"),
    ("evening",   "out"): ("#FF6B8A", "#FFB8CC", "#D84060", "#FFF4F6"),
}
_ABSENT_OUTER  = "#FF5070"
_ABSENT_INNER  = "#FFC0CC"
_ABSENT_SHADOW = "#D83050"
_ABSENT_BG     = "#FFF0F2"
_ABSENT_TEXT   = "#E03050"

# ── PNG 资产路径 (无文本 emoji，全部使用图片) ───────────────────────
# IP 动画帧统一存于 app/ui/assets/animations/<role>/frame_NN.png (ASCII 路径)。
# 注意: 原 doc/ui-design/.../<中文目录名>/ 路径在安卓打包/运行时无法可靠解析
# 中文文件名 (桌面端因 CWD=项目根凑巧能找到, 真机上贴图为空 → 渲染成白方块)，
# 故全部改为引用已规范化的 ASCII 路径副本。
_ICON_CAT      = "app/ui/assets/animations/cat/frame_02.png"
_ICON_WARNING  = "app/ui/assets/icons/warning.png"
_ICON_CHECKIN  = "app/ui/assets/icons/btn_checkin.png"   # 签到格图标
_ICON_CHECKOUT = "app/ui/assets/icons/btn_checkout.png"  # 签退格图标
_ICON_SAVE     = "app/ui/assets/icons/btn_save.png"      # 保存按钮图标
_SPRITE_DOG        = "app/ui/assets/animations/dog/frame_01.png"
_SPRITE_RABBIT     = "app/ui/assets/animations/rabbit/frame_01.png"
_SPRITE_CAT_CORNER = "app/ui/assets/animations/cat/frame_01.png"
_SPRITE_BEAR       = "app/ui/assets/animations/bear/frame_07.png"  # 最后一帧
_SPRITE_PIG        = "app/ui/assets/animations/pig/frame_01.png"   # 第一帧(开心站立)
_PIG_FRAMES = [
    f"app/ui/assets/animations/pig/frame_{i:02d}.png"
    for i in range(1, 8)
]

_CAT_FRAMES = [
    f"app/ui/assets/animations/cat/frame_{i:02d}.png"
    for i in range(1, 8)
]
_RABBIT_FRAMES = [
    f"app/ui/assets/animations/rabbit/frame_{i:02d}.png"
    for i in range(1, 8)
]
def _photo_base() -> Path:
    """图片根目录 — 与 AndroidCameraService/DesktopCameraMock 实际存盘位置保持一致。

    真机拍照存到公共 Pictures/Soloist (get_pictures_dir()), 而非旧的
    user_data/photos (仅桌面 mock 用); 硬编码旧路径会导致战报永远找不到
    真机拍摄的照片, 格子一直显示占位图。
    """
    from app.utils.storage import get_pictures_dir
    return get_pictures_dir()

# 格标签：纯文本，无 emoji（SmileySans 不含 emoji 字形）
_SLOT_LABELS: dict[tuple[str, str], str] = {
    ("morning",   "in"):  "早到岗",
    ("morning",   "out"): "早收工",
    ("afternoon", "in"):  "午到岗",
    ("afternoon", "out"): "晚收工",
    ("evening",   "in"):  "夜到岗",
    ("evening",   "out"): "深夜收工",
}
# 格行图标 (action → PNG)
_ACTION_ICON: dict[str, str] = {
    "in":  _ICON_CHECKIN,
    "out": _ICON_CHECKOUT,
}
_PERIOD_DISPLAY = {"morning": "早", "afternoon": "午", "evening": "晚"}

_STATUS_LABEL: dict[str, str] = {
    "normal": "正常", "late": "迟到", "early_leave": "早退",
    "absent_morning": "旷工", "absent_afternoon": "旷工",
    "leave": "请假", "shooting": "拍摄", "pending": "待判定",
}
_STATUS_COLOR: dict[str, str] = {
    "normal": "#27AE60", "late": "#E67E22", "early_leave": "#E67E22",
    "absent_morning": "#E74C3C", "absent_afternoon": "#E74C3C",
    "leave": "#3498DB", "shooting": "#E67E22", "pending": "#9E9690",
}

# ── 字号 (真机高可读性) ──────────────────────────────────────────
_FONT_DATE    = FONT_SIZE_TITLE + 6   # 24
_FONT_PERIOD  = FONT_SIZE_BODY + 1   # 15
_FONT_TIME    = FONT_SIZE_BODY        # 14
_FONT_SECTION = FONT_SIZE_BODY + 1   # 15
_FONT_SLOT    = FONT_SIZE_BODY        # 14
_FONT_STATUS  = FONT_SIZE_BODY       # 14
_FONT_REWARD  = FONT_SIZE_BODY + 4   # 18
_FONT_SUB     = FONT_SIZE_BODY       # 14
_FONT_ENC     = FONT_SIZE_BODY - 1   # 13

# ── 尺寸 ─────────────────────────────────────────────────────────
_LABEL_H = 26
_THUMB_H = 110
_SLOT_H  = _THUMB_H + _LABEL_H + 6


def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0,
            int(h[4:6], 16) / 255.0, alpha)


def _find_photo(date: str, period: str, action: str) -> Path | None:
    base = _photo_base() / date
    for ext in ("jpg", "jpeg", "png"):
        p = base / f"{period}_{action}.{ext}"
        if p.exists():
            return p
    return None


def _format_date(date_str: str) -> str:
    try:
        parts = date_str.split("-")
        return f"{int(parts[1])}月{int(parts[2])}日"
    except (IndexError, ValueError):
        return date_str


def _bind_bg(
    widget: Any,
    hex_color: str,
    radius: list[int] | None = None,
    border_color: str | None = None,
    border_w: int = 2,
) -> None:
    def _redraw(w: Any, *_: Any) -> None:
        w.canvas.before.clear()
        with w.canvas.before:
            if border_color:
                Color(*_to_rgba(border_color))
                if radius:
                    RoundedRectangle(pos=w.pos, size=w.size, radius=radius)
                else:
                    Rectangle(pos=w.pos, size=w.size)
                Color(*_to_rgba(hex_color))
                ip = (w.x + border_w, w.y + border_w)
                isz = (w.width - border_w * 2, w.height - border_w * 2)
                ir = [max(1, r - border_w) for r in radius] if radius else None
                if ir:
                    RoundedRectangle(pos=ip, size=isz, radius=ir)
                else:
                    Rectangle(pos=ip, size=isz)
            else:
                Color(*_to_rgba(hex_color))
                if radius:
                    RoundedRectangle(pos=w.pos, size=w.size, radius=radius)
                else:
                    Rectangle(pos=w.pos, size=w.size)
    widget.bind(pos=_redraw, size=_redraw)
    _redraw(widget)


def _bind_slot_frame(
    thumb: Any,
    outer: str,
    inner: str,
    shadow: str,
    content_bg: str,
    radius: int = 8,
) -> None:
    """双重线边框 + 像素阴影 (4 层 canvas)。"""
    r = [radius]

    def _redraw(w: Any, *_: Any) -> None:
        w.canvas.before.clear()
        with w.canvas.before:
            # 像素阴影
            Color(*_to_rgba(shadow, alpha=0.45))
            RoundedRectangle(pos=(w.x + 4, w.y - 4), size=w.size, radius=r)
            # 外边框
            Color(*_to_rgba(outer))
            RoundedRectangle(pos=w.pos, size=w.size, radius=r)
            # 内边框
            Color(*_to_rgba(inner))
            RoundedRectangle(
                pos=(w.x + 3, w.y + 3),
                size=(w.width - 6, w.height - 6),
                radius=[max(1, radius - 3)],
            )
            # 内容背景
            Color(*_to_rgba(content_bg))
            RoundedRectangle(
                pos=(w.x + 5, w.y + 5),
                size=(w.width - 10, w.height - 10),
                radius=[max(1, radius - 5)],
            )

    thumb.bind(pos=_redraw, size=_redraw)
    _redraw(thumb)


def _bind_mosaic_bg(
    widget: Any,
    tile: int = 18,
    border_color: str = PRIMARY_YELLOW,
    border_w: int = 3,
    radius: int = 10,
) -> None:
    """多巴胺马赛克渐变背景 — 像素格子拼接，棋盘交错配色。"""
    TILES = [
        "#FFF8D8",  # 奶黄
        "#D8F8E8",  # 薄荷
        "#D8EEFF",  # 天蓝
        "#FFD8E8",  # 蜜桃
        "#EDD8FF",  # 薰衣草
        "#FFE8CC",  # 蜜橙
        "#CCFFE8",  # 浅绿
        "#FFD8F8",  # 浅紫粉
    ]

    def _redraw(w: Any, *_: Any) -> None:
        w.canvas.before.clear()
        with w.canvas.before:
            # 像素阴影
            Color(*_to_rgba("#C8A800", alpha=0.38))
            RoundedRectangle(pos=(w.x + 4, w.y - 4), size=w.size, radius=[radius])
            # 黄色边框
            Color(*_to_rgba(border_color))
            RoundedRectangle(pos=w.pos, size=w.size, radius=[radius])
            # 内部马赛克
            x0 = w.x + border_w
            y0 = w.y + border_w
            wi = w.width  - border_w * 2
            hi = w.height - border_w * 2
            cols = int(wi / tile) + 1
            rows = int(hi / tile) + 1
            for row in range(rows):
                for col in range(cols):
                    idx = (row * 3 + col) % len(TILES)
                    tx  = x0 + col * tile
                    ty  = y0 + row * tile
                    tw  = min(tile, x0 + wi - tx)
                    th  = min(tile, y0 + hi - ty)
                    if tw > 0 and th > 0:
                        Color(*_to_rgba(TILES[idx], alpha=0.82))
                        Rectangle(pos=(tx, ty), size=(tw, th))

    widget.bind(pos=_redraw, size=_redraw)
    _redraw(widget)


def _bind_panel_frame(
    widget: Any,
    outer: str,
    inner: str,
    shadow: str,
    content_bg: str,
    radius: int = 10,
) -> None:
    """大卡片双重线边框 + 像素阴影（照片格同款风格，用于奖励面板/鼓励槽）。"""
    r = [radius]

    def _redraw(w: Any, *_: Any) -> None:
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*_to_rgba(shadow, alpha=0.40))
            RoundedRectangle(pos=(w.x + 4, w.y - 4), size=w.size, radius=r)
            Color(*_to_rgba(outer))
            RoundedRectangle(pos=w.pos, size=w.size, radius=r)
            Color(*_to_rgba(inner))
            RoundedRectangle(
                pos=(w.x + 3, w.y + 3),
                size=(w.width - 6, w.height - 6),
                radius=[max(1, radius - 3)],
            )
            Color(*_to_rgba(content_bg))
            RoundedRectangle(
                pos=(w.x + 5, w.y + 5),
                size=(w.width - 10, w.height - 10),
                radius=[max(1, radius - 5)],
            )

    widget.bind(pos=_redraw, size=_redraw)
    _redraw(widget)


def _start_frame_anim(
    img: Any,
    frames: list[str],
    fps: float = 4.0,
    bubble_indices: set[int] | None = None,
    loop_pause: float = 0.0,
) -> None:
    """逐帧切换 PNG 序列；气泡帧停留 2× 基础时长，最后一帧后暂停 loop_pause 秒。"""
    from kivy.clock import Clock
    base = 1.0 / fps
    state = [0]

    def _advance(dt: float) -> None:
        state[0] = (state[0] + 1) % len(frames)
        img.source = frames[state[0]]
        _schedule_next()

    def _schedule_next() -> None:
        idx = state[0]
        if idx == len(frames) - 1 and loop_pause > 0:
            Clock.schedule_once(_advance, loop_pause)
        elif bubble_indices and idx in bubble_indices:
            Clock.schedule_once(_advance, base * 2)
        else:
            Clock.schedule_once(_advance, base)

    _schedule_next()


def _fmt_hhmm(t: str | None) -> str:
    """把 HH:MM:SS 或 HH:MM 统一截断为 HH:MM，空值返回 --:--。"""
    if not t:
        return "--:--"
    parts = t.split(":")
    return f"{parts[0]}:{parts[1]}" if len(parts) >= 2 else t


class _PassthroughImage(Image):  # type: ignore[misc]
    """草地前景遮罩 Widget — 全尺寸渲染，collide_point 恒返回 False 以透传触控事件。"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        apply_pixel_filter(self.texture)  # 像素风背景放大时保持硬边, 不被线性过滤抹糊

    def collide_point(self, x: float, y: float) -> bool:  # type: ignore[override]
        return False


class ReportPreview(ModalView):  # type: ignore[misc]
    """全屏战报预览弹层。"""

    def __init__(
        self,
        image_path: str = "",
        date_str: str = "",
        report_data: ReportData | None = None,
        on_save: Any = None,
        on_settle: Any = None,
        settings_service: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._date_str = date_str
        self._settings_service = settings_service
        self.background = ""
        self.background_color = (0, 0, 0, 0)

        root = FloatLayout()
        with root.canvas.before:
            Color(0, 0, 0, 0.6)
            self._mask = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_mask, pos=self._update_mask)

        # panel 固定为逻辑设计画布尺寸, 稍后用 Scatter 整体等比缩放到屏幕。
        panel = FloatLayout(size=(LOGICAL_WIDTH, LOGICAL_HEIGHT), size_hint=(None, None))

        # ── 底层 [Image #6]: 完整景观背景（天空+彩虹+草地+土壤）─────
        def _redraw_panel_bg(w: Any, *_: Any) -> None:
            w.canvas.before.clear()
            with w.canvas.before:
                Color(1, 1, 1, 1)
                bg_rect = Rectangle(source=BG_LANDSCAPE, pos=w.pos, size=w.size)
            apply_pixel_filter(bg_rect.texture)
        panel.bind(pos=_redraw_panel_bg, size=_redraw_panel_bg)
        _redraw_panel_bg(panel)

        scroll = ScrollView(size_hint=(1, None), pos_hint={"x": 0, "y": 0.10})
        scroll.height = LOGICAL_HEIGHT - 72  # panel 尺寸固定, 手动设初值
        panel.bind(size=lambda w, _: setattr(scroll, "height", w.height - 72))

        self._content_box = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            spacing=0,
            padding=[CARD_PADDING, GRID_UNIT, CARD_PADDING, GRID_UNIT + GRASS_INSET // 3],
        )
        self._content_box.bind(minimum_height=self._content_box.setter("height"))

        if report_data is not None:
            self._build_report_content(report_data)
        elif image_path and os.path.exists(image_path):
            self._content_box.add_widget(
                Image(source=image_path, size_hint=(1, None), height=400)
            )
        else:
            self._content_box.add_widget(Label(
                text="战报数据加载中...",
                font_size=_FONT_STATUS,
                color=_to_rgba(TEXT_BROWN),
                size_hint_y=None,
                height=100,
                halign="center",
                valign="middle",
            ))

        scroll.add_widget(self._content_box)
        panel.add_widget(scroll)

        # ── 顶层 [Image #6]: 草地锯齿前景遮罩，夹在内容和按钮之间 ──
        # _PassthroughImage 不拦截触控，按钮区在此之后添加故处于更高 z 层
        _grass = _PassthroughImage(
            source=get_grass_overlay_path(),
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
            fit_mode="fill",
        )
        panel.add_widget(_grass)

        # 底部按钮区：关闭 + 保存（图标用 PNG 不用 emoji）
        btn_area = BoxLayout(
            orientation="horizontal",
            spacing=GRID_UNIT * 2,
            size_hint=(1, None),
            height=60,
            pos_hint={"x": 0, "y": 0.01},
            padding=[CARD_PADDING, 6],
        )
        close_btn = PixelButton(
            text="关闭",
            color="#8A8078",
            size_mode="normal",
            size_hint=(0.36, None),
        )
        close_btn.bind(on_press=lambda _: self._handle_settle(on_settle))

        # 保存按钮：文字 + 小图标行
        save_row = BoxLayout(
            orientation="horizontal",
            size_hint=(0.64, None),
            height=48,
            spacing=6,
        )
        save_btn = PixelButton(
            text="保存到相册",
            color="#FFE030",
            size_mode="normal",
            size_hint=(1, None),
        )
        if on_save:
            save_btn.bind(on_press=lambda _: on_save())
        save_row.add_widget(save_btn)

        btn_area.add_widget(close_btn)
        btn_area.add_widget(save_row)
        panel.add_widget(btn_area)

        root.add_widget(scale_wrap(panel))
        self.add_widget(root)

        panel.y = -panel.height
        anim = Animation(y=0, duration=0.25, t="out_quad")
        Clock = __import__("kivy.clock", fromlist=["Clock"]).Clock
        Clock.schedule_once(lambda dt: anim.start(panel), 0.05)

    # ── 内容构建 ────────────────────────────────────────────────

    def _build_report_content(self, data: ReportData) -> None:
        _add = self._content_box.add_widget

        # ① 品牌头部
        _add(self._brand_header())
        _add(self._spacer(GRID_UNIT * 2))

        # ② 日期卡
        _add(self._date_card(data))
        _add(self._spacer(GRID_UNIT * 2))

        # ②.5 拍摄复盘（仅拍摄日且有复盘时出现，办公日战报零改动）
        refl_section = self._shooting_reflection_section(data)
        if refl_section is not None:
            _add(refl_section)
            _add(self._spacer(GRID_UNIT * 2))

        # ③ 拍摄日：一张大幅现场照(占四帧)；办公日：自律时光机六格打卡
        if data.is_shooting_day:
            scene_title = Label(
                text="拍摄现场",
                font_size=_FONT_SECTION,
                bold=True,
                color=_to_rgba(TEXT_BROWN),
                size_hint=(1, None),
                height=28,
                halign="center",
                valign="middle",
            )
            scene_title.bind(size=scene_title.setter("text_size"))
            _add(scene_title)
            _add(self._spacer(GRID_UNIT))
            _add(_ShootingSceneBig(data))
            _add(self._spacer(GRID_UNIT * 2))
        else:
            has_evening = any(p.period == "evening" for p in data.periods)
            frame_count = 6 if has_evening else 4

            sec_row = BoxLayout(
                orientation="horizontal",
                size_hint=(1, None),
                height=63,
                spacing=GRID_UNIT,
            )
            sec_dog = Image(
                source=_SPRITE_DOG,
                size_hint=(None, 1),
                width=63,
                fit_mode="contain",
            )
            title_col = BoxLayout(orientation="vertical", size_hint=(None, 1), width=100, spacing=2)
            t_sub = Label(
                text=f"一日{frame_count}帧",
                font_size=12,
                color=_to_rgba(TEXT_GRAY),
                size_hint_y=0.4,
                halign="left",
                valign="bottom",
            )
            t_sub.bind(size=t_sub.setter("text_size"))
            t_main = Label(
                text="自律时光机",
                font_size=_FONT_SECTION,
                bold=True,
                color=_to_rgba(TEXT_BROWN),
                size_hint_y=0.6,
                halign="left",
                valign="top",
            )
            t_main.bind(size=t_main.setter("text_size"))
            title_col.add_widget(t_sub)
            title_col.add_widget(t_main)
            sec_row.add_widget(BoxLayout(size_hint_x=1))
            sec_row.add_widget(sec_dog)
            sec_row.add_widget(title_col)
            sec_row.add_widget(BoxLayout(size_hint_x=1))
            _add(sec_row)
            _add(self._spacer(GRID_UNIT))
            _add(_ReportPhotoGrid(data))
            _add(self._spacer(GRID_UNIT * 2))

        # ④ 男友奖励联动看板 (FloatLayout 包裹，右下角圆圆贴纸)
        _add(self._reward_panel(data))

        # ⑤ 鼓励语 (柴犬左右夹持)
        enc = self._encouragement_slot(data)
        if enc is not None:
            _add(self._spacer(GRID_UNIT))
            _add(enc)

        _add(self._spacer(GRID_UNIT * 2))

    # ── 辅助构建 ────────────────────────────────────────────────

    @staticmethod
    def _brand_header() -> BoxLayout:
        """品牌头部：居中，小猫 IP + 标题（0.75× 缩放）。"""
        outer = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=90,
            spacing=GRID_UNIT,
            padding=[0, 4],
        )
        outer.add_widget(BoxLayout(size_hint_x=1))

        cat = Image(source=_ICON_CAT, size_hint=(None, 1), width=84, fit_mode="contain")
        apply_pixel_filter(cat.texture)  # 品牌小猫像素图放大保持硬边
        cat.bind(texture=lambda _i, t: apply_pixel_filter(t))  # 异步/重载后仍 nearest
        text_col = BoxLayout(orientation="vertical", size_hint=(None, 1), width=144, spacing=4)
        t1 = Label(
            text="Soloist Cabin",
            font_size=22,
            bold=True,
            color=_to_rgba(TEXT_BROWN),
            halign="left",
            valign="bottom",
            size_hint_y=0.55,
        )
        t1.bind(size=t1.setter("text_size"))
        t2 = Label(
            text="每日自律战报",
            font_size=20,
            color=_to_rgba(TEXT_GRAY),
            halign="left",
            valign="top",
            size_hint_y=0.45,
        )
        t2.bind(size=t2.setter("text_size"))
        text_col.add_widget(t1)
        text_col.add_widget(t2)

        outer.add_widget(cat)
        outer.add_widget(text_col)
        outer.add_widget(BoxLayout(size_hint_x=1))
        return outer

    @staticmethod
    def _date_card(data: ReportData) -> FloatLayout:
        """马赛克渐变日期卡 + 右上角小猪贴纸。"""
        period_map = {p.period: p for p in data.periods}
        periods_to_show = ["morning", "afternoon"]
        if any(p.period == "evening" for p in data.periods):
            periods_to_show.append("evening")

        # 三行：日期(36) + 时间(26) + 状态(22)，加间距和内边距
        card_h = 36 + 6 + 68 + GRID_UNIT * 2

        wrapper = FloatLayout(size_hint=(1, None), height=card_h)

        card = BoxLayout(
            orientation="vertical",
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
            padding=[GRID_UNIT * 2, GRID_UNIT],
            spacing=6,
        )
        _bind_mosaic_bg(card, tile=18, border_color=PRIMARY_YELLOW, border_w=3, radius=10)

        card.add_widget(Label(
            text=_format_date(data.date),
            font_size=_FONT_DATE,
            bold=True,
            color=_to_rgba(TEXT_BROWN),
            size_hint_y=None,
            height=36,
            halign="center",
            valign="middle",
        ))

        time_row = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=68,
            spacing=GRID_UNIT,
        )
        for pk in periods_to_show:
            p = period_map.get(pk)
            ci = _fmt_hhmm(p.checkin_time  if p else None)
            co = _fmt_hhmm(p.checkout_time if p else None)
            st = (p.status or "pending") if p else "pending"
            st_text  = _STATUS_LABEL.get(st, "待判定")
            st_color = _STATUS_COLOR.get(st, "#9E9690")
            col = BoxLayout(orientation="vertical", size_hint=(1, 1), spacing=2)
            n = Label(
                text=_PERIOD_DISPLAY.get(pk, pk),
                font_size=_FONT_PERIOD,
                color=_to_rgba(TEXT_GRAY),
                size_hint_y=None,
                height=20,
                halign="center",
                valign="middle",
            )
            n.bind(size=n.setter("text_size"))
            t = Label(
                text=f"{ci}→{co}",
                font_size=_FONT_TIME,
                bold=True,
                color=_to_rgba(TEXT_BROWN),
                size_hint_y=None,
                height=24,
                halign="center",
                valign="middle",
            )
            t.bind(size=t.setter("text_size"))
            s = Label(
                text=st_text,
                font_size=_FONT_PERIOD,
                bold=True,
                color=_to_rgba(st_color),
                size_hint_y=None,
                height=20,
                halign="center",
                valign="middle",
            )
            s.bind(size=s.setter("text_size"))
            col.add_widget(n)
            col.add_widget(t)
            col.add_widget(s)
            time_row.add_widget(col)
        card.add_widget(time_row)
        wrapper.add_widget(card)

        # 右上角小猪贴纸：中心对齐卡片顶边，一半在框内一半在框外，上下跳动
        from kivy.animation import Animation as _Anim
        from kivy.clock import Clock as _Clock
        from kivy.graphics.context_instructions import PopMatrix, PushMatrix, Translate
        pig = Image(
            source=_SPRITE_PIG,
            size_hint=(None, None),
            size=(112, 112),
            pos_hint={"right": 1.0, "center_y": 1.0},
            fit_mode="contain",
        )
        with pig.canvas.before:
            PushMatrix()
            _pig_tr = Translate(0, 0, 0)
        with pig.canvas.after:
            PopMatrix()

        def _pig_bounce(dt, t=_pig_tr):
            anim = (
                _Anim(y=10, duration=0.5, t="out_sine")
                + _Anim(y=0, duration=0.5, t="in_sine")
            )
            anim.repeat = True
            anim.start(t)

        _Clock.schedule_once(_pig_bounce, 0.5)
        wrapper.add_widget(pig)
        return wrapper

    @staticmethod
    def _shooting_reflection_section(data: ReportData) -> BoxLayout | None:
        """拍摄复盘卡片 — 仅拍摄日且有复盘时出现，复用面板双重线边框(暖橙)。

        办公日战报不受影响(data.shooting_reflection 为空则返回 None)。
        """
        if not data.shooting_reflection:
            return None

        box = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            padding=[CARD_PADDING, GRID_UNIT],
            spacing=6,
        )
        _bind_panel_frame(
            box,
            outer="#FF9040", inner="#FFD4A0",
            shadow="#C07028", content_bg="#FFF8F0",
        )

        title = Label(
            text="拍摄复盘",
            font_size=_FONT_SECTION,
            bold=True,
            color=_to_rgba(TEXT_BROWN),
            size_hint_y=None,
            height=28,
            halign="center",
            valign="middle",
        )
        title.bind(size=title.setter("text_size"))
        box.add_widget(title)

        meta_parts = []
        if data.shooting_content:
            meta_parts.append(f"内容：{data.shooting_content}")
        if data.shooting_location:
            meta_parts.append(f"地点：{data.shooting_location}")
        if meta_parts:
            meta = Label(
                text="    ".join(meta_parts),
                font_size=_FONT_SUB,
                color=_to_rgba(TEXT_GRAY),
                size_hint_y=None,
                height=24,
                halign="center",
                valign="middle",
            )
            meta.bind(size=meta.setter("text_size"))
            box.add_widget(meta)

        refl = Label(
            text=data.shooting_reflection,
            font_size=_FONT_SUB,
            color=_to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            halign="center",
            valign="top",
        )
        refl.bind(width=lambda w, _v: setattr(w, "text_size", (w.width, None)))
        refl.bind(texture_size=lambda w, ts: setattr(w, "height", ts[1]))
        box.add_widget(refl)

        box.bind(minimum_height=box.setter("height"))
        return box

    def _reward_panel(self, data: ReportData) -> FloatLayout:
        """达标/未达标双态看板，IP 贴纸叠加。

        拍摄日没有"工时"概念(全天跳过打卡), 达标与否看拍摄奖励是否已入账,
        而非 total_work_hours(拍摄日恒为 0, 会被误判成"未达标")。
        """
        if data.is_shooting_day:
            achieved = data.reward_total > 0
        elif data.promise is not None:
            achieved = data.promise.fulfilled
        else:
            achieved = data.total_work_hours >= data.threshold_hours

        panel_h  = 124
        sprite_w = panel_h
        pad = [sprite_w + 8, GRID_UNIT, CARD_PADDING, GRID_UNIT]

        wrapper = FloatLayout(size_hint=(1, None), height=panel_h)

        panel = BoxLayout(
            orientation="vertical",
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
            padding=pad,
            spacing=GRID_UNIT,
        )

        if achieved:
            _bind_panel_frame(
                panel,
                outer="#50C8B8", inner="#A0E8D8",
                shadow="#208878", content_bg=_COLOR_REWARD_BG,
            )
            if data.is_shooting_day:
                main_text = f"拍摄奖励 {data.reward_total:.0f} 元已经到账啦！"
                sub_text = "辛苦拍摄啦，好好休息一下吧~"
            elif data.promise:
                nickname = ""
                if self._settings_service:
                    nickname = self._settings_service.get_user_nickname()
                reward_desc = data.promise.reward_desc
                if nickname:
                    reward_desc = reward_desc.replace("兜兜", nickname)
                nickname = ""
                if self._settings_service:
                    nickname = self._settings_service.get_user_nickname()
                who = nickname if nickname else "猪大样"
                main_text = (
                    f"{data.promise.reward_qty} 次{reward_desc}，"
                    f"{who}请客~"
                )
                sub_text = "小木屋替你记着，他可不能赖账哦！"
            else:
                main_text = f"今天工时 {data.total_work_hours:.1f}h，达标啦！"
                sub_text = "小木屋替你记着，他可不能赖账哦！"
        else:
            _bind_panel_frame(
                panel,
                outer="#B0A090", inner="#D8D0C0",
                shadow="#807060", content_bg=_COLOR_UNMET_BG,
            )
            if data.is_shooting_day:
                main_text = "拍摄复盘还没提交，奖励还没到账哦"
                sub_text = "记得点「完成拍摄」提交复盘~"
            elif data.promise:
                nickname = ""
                if self._settings_service:
                    nickname = self._settings_service.get_user_nickname()
                # 剥离 reward_desc 中可能存在的 "兜兜"→昵称替换
                reward = data.promise.reward_desc.replace("兜兜", nickname).lstrip("：:、, ").strip()
                main_text = (
                    f"今天工时 {data.total_work_hours:.1f}h "
                    f"未达 {data.threshold_hours:.0f}h 门槛，"
                    f"没拿到「{reward}」"
                )
                sub_text = random.choice(ENCOURAGEMENTS)
            else:
                main_text = f"今天工时 {data.total_work_hours:.1f}h，未达标"
                sub_text = random.choice(ENCOURAGEMENTS)

        ml = Label(
            text=main_text,
            font_size=_FONT_REWARD,
            bold=True,
            color=_to_rgba(TEXT_BROWN),
            size_hint_y=None,
            height=48,
            halign="center",
            valign="middle",
            shorten=False,
        )
        ml.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))

        sl = Label(
            text=sub_text,
            font_size=_FONT_SUB,
            color=_to_rgba(TEXT_BROWN),
            size_hint_y=None,
            height=44,
            halign="center",
            valign="middle",
            shorten=False,
        )
        sl.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))

        panel.add_widget(ml)
        panel.add_widget(sl)
        wrapper.add_widget(panel)

        # 左侧 IP 贴纸：达标→庆祝小猫(canvas Translate 上下跳动)；未达标→熬夜小熊(静止)
        if achieved:
            from kivy.graphics.context_instructions import PushMatrix, PopMatrix, Translate
            corner = Image(
                source=_CAT_FRAMES[0],
                size_hint=(None, None),
                size=(sprite_w, panel_h),
                pos_hint={"x": 0, "y": 0},
                fit_mode="contain",
            )
            # 用 canvas Translate 偏移渲染，不改动 widget.y，FloatLayout 不会干扰
            with corner.canvas.before:
                PushMatrix()
                _tr = Translate(0, 0, 0)
            with corner.canvas.after:
                PopMatrix()

            def _start_bounce(dt, t=_tr, img=corner):
                anim = (
                    Animation(y=8, duration=0.45, t="out_sine")
                    + Animation(y=0, duration=0.45, t="in_sine")
                )
                anim.repeat = True
                anim.start(t)
                _start_frame_anim(img, _CAT_FRAMES, fps=4.0, bubble_indices={1, 3, 4}, loop_pause=2.0)

            from kivy.clock import Clock
            Clock.schedule_once(_start_bounce, 0.3)
        else:
            corner = Image(
                source=_SPRITE_BEAR,
                size_hint=(None, 1),
                width=sprite_w,
                pos_hint={"x": 0, "y": 0},
                fit_mode="contain",
            )
        wrapper.add_widget(corner)

        return wrapper

    @staticmethod
    def _encouragement_slot(data: ReportData) -> BoxLayout | None:
        """鼓励语 — 小狗(左) + 小兔(右) 3 倍大夹持文字。

        扩展点：用户自定义语录库写入 data.encouragement 即可，接口签名不变。
        """
        if not data.encouragement:
            return None

        _SPRITE_H = 84   # 3 倍 ≈ 原 28px × 3
        row = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=_SPRITE_H,
            spacing=GRID_UNIT,
            padding=[GRID_UNIT, 4],
        )
        _bind_panel_frame(
            row,
            outer="#E8C070", inner="#F8E8A0",
            shadow="#A87830", content_bg="#FFFAEE",
        )
        rabbit = Image(
            source=_RABBIT_FRAMES[0],
            size_hint=(None, 1),
            width=_SPRITE_H,
            fit_mode="contain",
        )
        from kivy.clock import Clock as _Clock
        _Clock.schedule_once(
            lambda dt, img=rabbit: _start_frame_anim(img, _RABBIT_FRAMES, fps=4.0, loop_pause=2.0), 0.1
        )
        lab = Label(
            text=data.encouragement,
            font_size=_FONT_ENC,
            color=_to_rgba(TEXT_GRAY),
            size_hint=(1, 1),
            halign="center",
            valign="middle",
            shorten=False,
        )
        lab.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))
        row.add_widget(lab)
        row.add_widget(rabbit)
        return row

    def _update_mask(self, instance: Any, value: Any) -> None:
        self._mask.size = instance.size
        self._mask.pos = instance.pos

    def _handle_settle(self, on_settle: Any) -> None:
        if on_settle:
            on_settle()
        self.dismiss()

    @staticmethod
    def _spacer(height: int = 8) -> Label:
        return Label(text="", size_hint_y=None, height=height)


# ── 内联照片网格 ──────────────────────────────────────────────────

class _ReportPhotoGrid(BoxLayout):
    """战报照片网格：始终展示全部格，空格显示状态占位。"""

    def __init__(self, data: ReportData, **kwargs: Any) -> None:
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("spacing", GRID_UNIT + 4)
        super().__init__(**kwargs)

        period_status: dict[str, str] = {
            p.period: (p.status or "pending") for p in data.periods
        }
        has_evening = any(p.period == "evening" for p in data.periods)
        periods = (["morning", "afternoon", "evening"] if has_evening
                   else ["morning", "afternoon"])

        row_count = 2
        self.height = row_count * _SLOT_H + (row_count - 1) * (GRID_UNIT + 4)

        for action_key in ("in", "out"):
            row = BoxLayout(
                orientation="horizontal",
                size_hint=(1, None),
                height=_SLOT_H,
                spacing=GRID_UNIT,
            )
            for period_key in periods:
                status = period_status.get(period_key, "pending")
                photo  = _find_photo(data.date, period_key, action_key)
                label  = _SLOT_LABELS.get((period_key, action_key), "")
                frame  = _SLOT_FRAME.get(
                    (period_key, action_key),
                    ("#B8C0C8", "#D8DCE0", "#909898", "#F8F8F6"),
                )
                row.add_widget(_ReportSlot(
                    label_text=label,
                    action_key=action_key,
                    photo_path=photo,
                    status=status,
                    frame=frame,
                ))
            self.add_widget(row)


class _ShootingSceneBig(BoxLayout):
    """拍摄日战报的大幅现场照 — 占原四帧网格大小，替代打卡六格。

    有 shooting_scene 照片则大图铺满(cover)；无则暖橙占位标注"今日拍摄现场"。
    """

    def __init__(self, data: ReportData, **kwargs: Any) -> None:
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint", (1, None))
        super().__init__(**kwargs)

        big_h = 2 * _SLOT_H   # 占原四帧(2×2)高度
        self.height = big_h

        thumb = BoxLayout(size_hint=(1, None), height=big_h)
        _bind_slot_frame(thumb, "#FF9040", "#FFD4A0", "#C07028", "#FFF8F0")

        photo = _find_photo(data.date, "shooting", "scene")
        if photo is not None:
            img = Image(
                source=photo.as_posix(),
                size_hint=(1, 1),
                fit_mode="cover",
            )
            thumb.add_widget(img)
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt, i=img: i.reload(), 0)
        else:
            placeholder = BoxLayout(orientation="vertical", size_hint=(1, 1), padding=[10, 10])
            top = Label(
                text="今日拍摄现场",
                font_size=_FONT_SECTION,
                bold=True,
                color=_to_rgba("#FF9040"),
                size_hint=(1, 0.55),
                halign="center",
                valign="bottom",
            )
            top.bind(size=top.setter("text_size"))
            sub = Label(
                text="(未拍现场照)",
                font_size=_FONT_SUB,
                color=_to_rgba(TEXT_GRAY),
                size_hint=(1, 0.45),
                halign="center",
                valign="top",
            )
            sub.bind(size=sub.setter("text_size"))
            placeholder.add_widget(top)
            placeholder.add_widget(sub)
            thumb.add_widget(placeholder)

        self.add_widget(thumb)


class _ReportSlot(BoxLayout):
    """单个照片格：PNG 图标 + 文本标签(上) + 双重线边框照片区(下)。"""

    def __init__(
        self,
        label_text: str,
        action_key: str,
        photo_path: Path | None,
        status: str,
        frame: tuple[str, str, str, str],
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", _SLOT_H)
        kwargs.setdefault("spacing", 6)
        super().__init__(**kwargs)

        # ── 上方标签行：PNG 图标 + 文本 ─────────────────────
        label_row = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=_LABEL_H,
            spacing=4,
        )
        icon_src = _ACTION_ICON.get(action_key, _ICON_CHECKIN)
        icon_img = Image(
            source=icon_src,
            size_hint=(None, 1),
            width=18,
            fit_mode="contain",
        )
        lbl = Label(
            text=label_text,
            font_size=_FONT_SLOT,
            color=_to_rgba(TEXT_BROWN),
            size_hint=(1, 1),
            halign="center",
            valign="middle",
        )
        lbl.bind(size=lbl.setter("text_size"))
        label_row.add_widget(icon_img)
        label_row.add_widget(lbl)
        self.add_widget(label_row)

        # ── 照片区（双重线边框 + 像素阴影）─────────────────────
        thumb = BoxLayout(size_hint=(1, None), height=_THUMB_H)

        is_absent = "absent" in status
        is_shooting = status == "shooting"
        if is_absent:
            outer, inner, shadow, content_bg = (
                _ABSENT_OUTER, _ABSENT_INNER, _ABSENT_SHADOW, _ABSENT_BG
            )
        else:
            outer, inner, shadow, content_bg = frame

        _bind_slot_frame(thumb, outer, inner, shadow, content_bg)

        if photo_path is not None:
            img = Image(
                source=photo_path.as_posix(),
                size_hint=(1, 1),
                fit_mode="cover",
            )
            thumb.add_widget(img)
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt, i=img: i.reload(), 0)
        else:
            placeholder = BoxLayout(
                orientation="vertical",
                size_hint=(1, 1),
                padding=[4, 4],
            )
            if is_absent:
                placeholder.add_widget(Image(
                    source=_ICON_WARNING,
                    size_hint=(1, 0.55),
                    fit_mode="contain",
                ))
                placeholder.add_widget(Label(
                    text="旷工",
                    font_size=_FONT_STATUS,
                    bold=True,
                    color=_to_rgba(_ABSENT_TEXT),
                    size_hint=(1, 0.45),
                    halign="center",
                    valign="middle",
                ))
            elif is_shooting:
                # 拍摄日无打卡照片时不应显示成"待打卡"(像什么都没发生),
                # 用已定义好的拍摄专属文案+配色明确标注状态。
                placeholder.add_widget(Label(
                    text=_STATUS_LABEL.get("shooting", "拍摄"),
                    font_size=_FONT_STATUS,
                    bold=True,
                    color=_to_rgba(_STATUS_COLOR.get("shooting", TEXT_GRAY)),
                    size_hint=(1, 1),
                    halign="center",
                    valign="middle",
                ))
            else:
                placeholder.add_widget(Label(
                    text="待打卡",
                    font_size=_FONT_STATUS,
                    color=_to_rgba(TEXT_GRAY),
                    size_hint=(1, 1),
                    halign="center",
                    valign="middle",
                ))
            thumb.add_widget(placeholder)

        self.add_widget(thumb)
