"""资源加载器 — Sprite 切片 + Icon 获取 + 帧序列动画 + 预加载。

所有像素资源在此统一管理，UI 组件通过此模块获取图像。
使用 PIL 做帧切片，Kivy CoreImage 加载独立帧（兼容 headless 测试）。
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from kivy.core.image import Image as CoreImage
from kivy.uix.image import Image as KivyImage
from PIL import Image as PILImage

_ASSETS_DIR = Path(__file__).parent.resolve()
_SPRITE_CACHE: dict[str, list[CoreImage]] = {}
_SEQUENCE_CACHE: dict[str, list[CoreImage]] = {}

# sprite 帧配置: {mascot_id: (filename, frame_width, frame_count)}
SPRITE_CONFIG: dict[str, tuple[str, int, int]] = {
    "dudu": ("sprites/dudu_32x32.png", 32, 4),
    "wengweng": ("sprites/wengweng_16x16.png", 16, 4),
    "tuantuan": ("sprites/tuantuan_32x32.png", 32, 4),
    "wangzai": ("sprites/wangzai_32x32.png", 32, 4),
    "migu": ("sprites/migu_16x16.png", 16, 4),
}

# 帧序列动画配置: {anim_id: folder_relative_path}
SEQUENCE_CONFIG: dict[str, str] = {
    "rabbit": "animations/rabbit",   # 小兔胜利 — 日常签到/签退
    "bear": "animations/bear",       # 小熊熬夜 — 加班签到/签退
    "dog": "animations/dog",         # 小狗摘星星 — 结算完成/超额
    "pig": "animations/pig",         # 小猪倒下 — 结算未完成
    "cat": "animations/cat",         # 小猫庆祝 — 备用
}

# 图标文件映射: {icon_name: relative_path}
ICON_FILES: dict[str, str] = {
    "tab_checkin": "icons/tab_checkin.png",
    "tab_checkin_active": "icons/tab_checkin_active.png",
    "tab_checkin_inactive": "icons/tab_checkin_inactive.png",
    "tab_history": "icons/tab_history.png",
    "tab_history_active": "icons/tab_history_active.png",
    "tab_history_inactive": "icons/tab_history_inactive.png",
    "tab_bet": "icons/tab_bet.png",
    "tab_bet_active": "icons/tab_bet_active.png",
    "tab_bet_inactive": "icons/tab_bet_inactive.png",
    "tab_settings": "icons/tab_settings.png",
    "tab_settings_active": "icons/tab_settings_active.png",
    "tab_settings_inactive": "icons/tab_settings_inactive.png",
    "btn_checkin": "icons/btn_checkin.png",
    "btn_checkout": "icons/btn_checkout.png",
    "btn_leave": "icons/btn_leave.png",
    "btn_add": "icons/btn_add.png",
    "btn_report": "icons/btn_report.png",
    "btn_save": "icons/btn_save.png",
    "btn_settle": "icons/btn_settle.png",
    "arrow_left": "icons/arrow_left.png",
    "arrow_right": "icons/arrow_right.png",
    "check_mark": "icons/check_mark.png",
    "cross": "icons/cross.png",
    "warning": "icons/warning.png",
}


def _slice_sprite_sheet(path: Path, frame_w: int, frame_count: int) -> list[CoreImage]:
    """用 PIL 切割 sprite sheet 为独立帧，每帧用 Kivy CoreImage 加载。"""
    sheet = PILImage.open(str(path))
    frames: list[CoreImage] = []

    for i in range(frame_count):
        # PIL 裁切当前帧
        frame_img = sheet.crop((i * frame_w, 0, (i + 1) * frame_w, frame_w))
        # 写入内存 buffer
        buf = io.BytesIO()
        frame_img.save(buf, format="PNG")
        buf.seek(0)
        # Kivy 从 buffer 加载
        ci = CoreImage(buf, ext="png")
        frames.append(ci)

    return frames


class SpriteLoader:
    """角色 Sprite Sheet 加载器。

    从 PNG 加载并切片为帧列表。
    """

    @staticmethod
    def load_sprite(mascot_id: str) -> list[CoreImage]:
        """加载指定角色的所有帧。

        Args:
            mascot_id: 角色 ID (dudu/wengweng/tuantuan/wangzai/migu)

        Returns:
            帧 CoreImage 列表 (通常 4 帧)
        """
        if mascot_id in _SPRITE_CACHE:
            return list(_SPRITE_CACHE[mascot_id])

        config = SPRITE_CONFIG.get(mascot_id)
        if not config:
            raise ValueError(f"Unknown mascot_id: {mascot_id}")

        filename, frame_w, frame_count = config
        path = _ASSETS_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Sprite file not found: {path}")

        frames = _slice_sprite_sheet(path, frame_w, frame_count)
        _SPRITE_CACHE[mascot_id] = frames
        return list(frames)

    @staticmethod
    def load_frame(mascot_id: str, frame_index: int) -> CoreImage:
        """加载指定角色的单个帧。

        Args:
            mascot_id: 角色 ID
            frame_index: 帧索引 (0-3)
        """
        frames = SpriteLoader.load_sprite(mascot_id)
        if frame_index < 0 or frame_index >= len(frames):
            raise IndexError(f"Frame index {frame_index} out of range for {mascot_id}")
        return frames[frame_index]

    @staticmethod
    def get_frame_count(mascot_id: str) -> int:
        """获取指定角色的总帧数。"""
        config = SPRITE_CONFIG.get(mascot_id)
        return config[2] if config else 0


class IconLoader:
    """功能图标加载器。"""

    @staticmethod
    def get_icon(icon_name: str, color: tuple[float, float, float, float] | None = None) -> KivyImage:
        """获取指定图标的 Kivy Image widget。

        Args:
            icon_name: 图标名 (如 'tab_checkin', 'btn_add' 等)
            color: 可选颜色 overlay (RGBA 0-1 元组)

        Returns:
            Kivy Image widget
        """
        path = IconLoader.get_icon_path(icon_name)
        img = KivyImage(source=str(path))
        img.allow_stretch = True
        img.keep_ratio = True
        if color:
            img.color = color
        return img

    @staticmethod
    def get_icon_path(icon_name: str) -> Path:
        """获取图标文件路径。"""
        rel_path = ICON_FILES.get(icon_name)
        if not rel_path:
            raise ValueError(f"Unknown icon: {icon_name}")

        path = _ASSETS_DIR / rel_path
        if not path.exists():
            raise FileNotFoundError(f"Icon file not found: {path}")
        return path


class SequenceLoader:
    """帧序列动画加载器（支持 JPG/PNG 独立帧文件）。

    从 animations/<name>/ 目录按文件名排序加载所有帧。
    """

    @staticmethod
    def load_sequence(anim_id: str) -> list[CoreImage]:
        """加载指定动画的帧序列。

        Args:
            anim_id: 动画 ID (rabbit/bear/dog/pig)

        Returns:
            CoreImage 帧列表（按文件名升序）
        """
        if anim_id in _SEQUENCE_CACHE:
            return list(_SEQUENCE_CACHE[anim_id])

        folder = SEQUENCE_CONFIG.get(anim_id)
        if not folder:
            raise ValueError(f"Unknown animation: {anim_id}")

        anim_dir = _ASSETS_DIR / folder
        if not anim_dir.exists():
            raise FileNotFoundError(f"Animation directory not found: {anim_dir}")

        frame_files = sorted(
            f for f in anim_dir.iterdir()
            if f.suffix.lower() in (".jpg", ".jpeg", ".png")
        )
        if not frame_files:
            raise FileNotFoundError(f"No frame files in: {anim_dir}")

        frames = [CoreImage(str(f)) for f in frame_files]
        _SEQUENCE_CACHE[anim_id] = frames
        return list(frames)


def preload_all() -> dict[str, Any]:
    """启动时预加载所有 sprite、序列动画和 icon 到内存。

    Returns:
        加载状态字典: {'sprites': loaded_count, 'sequences': loaded_count, 'icons': loaded_count}
    """
    sprite_count = 0
    for mascot_id in SPRITE_CONFIG:
        try:
            SpriteLoader.load_sprite(mascot_id)
            sprite_count += 1
        except Exception:
            pass

    sequence_count = 0
    for anim_id in SEQUENCE_CONFIG:
        try:
            SequenceLoader.load_sequence(anim_id)
            sequence_count += 1
        except Exception:
            pass

    icon_count = 0
    for icon_name in ICON_FILES:
        try:
            IconLoader.get_icon_path(icon_name)
            icon_count += 1
        except Exception:
            pass

    return {"sprites": sprite_count, "sequences": sequence_count, "icons": icon_count}
