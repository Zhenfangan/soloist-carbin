"""测试像素资源 — Sprite/Icon 文件验证 + 加载器功能测试。"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image as PILImage

from app.ui.assets.loader import (
    ICON_FILES,
    SPRITE_CONFIG,
    IconLoader,
    SpriteLoader,
    preload_all,
)
from app.ui.fonts import apply_global_font


def _get_assets_dir() -> Path:
    return Path(__file__).parent.parent.parent / "ui" / "assets"


class TestSpriteFiles:
    """2.3〜2.7 角色 Sprite 文件验证"""

    def test_all_sprite_files_exist(self) -> None:
        assets = _get_assets_dir()
        for _mascot_id, (filename, _, _) in SPRITE_CONFIG.items():
            path = assets / filename
            assert path.exists(), f"Sprite missing: {filename}"
            assert path.is_file(), f"Not a file: {filename}"

    def test_sprite_dimensions(self) -> None:
        """验证 sprite sheet 尺寸：frame_w × 4 宽 × frame_h 高。"""
        assets = _get_assets_dir()
        for _mascot_id, (filename, frame_w, frame_count) in SPRITE_CONFIG.items():
            path = assets / filename
            img = PILImage.open(str(path))
            assert img.width == frame_w * frame_count, (
                f"{filename}: expected width {frame_w * frame_count}, got {img.width}"
            )
            assert img.height == frame_w, (
                f"{filename}: expected height {frame_w}, got {img.height}"
            )

    def test_sprite_frame_count(self) -> None:
        """所有角色至少 4 帧。"""
        for mascot_id, (_filename, _, frame_count) in SPRITE_CONFIG.items():
            assert frame_count >= 4, f"{mascot_id}: expected >= 4 frames, got {frame_count}"

    def test_dudu_is_32x32(self) -> None:
        config = SPRITE_CONFIG["dudu"]
        assert config[1] == 32  # frame width

    def test_wengweng_is_16x16(self) -> None:
        config = SPRITE_CONFIG["wengweng"]
        assert config[1] == 16

    def test_tuantuan_is_32x32(self) -> None:
        config = SPRITE_CONFIG["tuantuan"]
        assert config[1] == 32

    def test_wangzai_is_32x32(self) -> None:
        config = SPRITE_CONFIG["wangzai"]
        assert config[1] == 32

    def test_migu_is_16x16(self) -> None:
        config = SPRITE_CONFIG["migu"]
        assert config[1] == 16

    def test_sprites_are_rgba(self) -> None:
        """所有 sprite PNG 应该是 RGBA 模式。"""
        assets = _get_assets_dir()
        for _mascot_id, (filename, _, _) in SPRITE_CONFIG.items():
            path = assets / filename
            img = PILImage.open(str(path))
            assert img.mode == "RGBA", f"{filename}: expected RGBA, got {img.mode}"


class TestIconFiles:
    """2.8〜2.9 功能图标文件验证"""

    def test_all_24_icons_exist(self) -> None:
        assets = _get_assets_dir()
        assert len(ICON_FILES) == 24, f"Expected 24 icons, got {len(ICON_FILES)}"
        for _icon_name, rel_path in ICON_FILES.items():
            path = assets / rel_path
            assert path.exists(), f"Icon missing: {rel_path}"
            assert path.is_file(), f"Not a file: {rel_path}"

    def test_icons_are_32x32(self) -> None:
        """基础图标生成后应该被 nearest-neighbor 放大至 32×32。
        tab_*_active / tab_*_inactive 图标尺寸较大(118-132×97-105),不在 32×32 范围内。
        """
        assets = _get_assets_dir()
        base_icons = {
            k: v for k, v in ICON_FILES.items()
            if "_active" not in k and "_inactive" not in k
        }
        for icon_name, rel_path in base_icons.items():
            path = assets / rel_path
            img = PILImage.open(str(path))
            assert img.width == 32, f"{icon_name}: expected width 32, got {img.width}"
            assert img.height == 32, f"{icon_name}: expected height 32, got {img.height}"

    def test_icons_are_rgba(self) -> None:
        assets = _get_assets_dir()
        for icon_name, rel_path in ICON_FILES.items():
            path = assets / rel_path
            img = PILImage.open(str(path))
            assert img.mode == "RGBA", f"{icon_name}: expected RGBA, got {img.mode}"


class TestSpriteLoader:
    """2.10 SpriteLoader 测试"""

    def test_load_sprite_returns_frames(self) -> None:
        frames = SpriteLoader.load_sprite("dudu")
        assert len(frames) == 4

    def test_load_frame_returns_single_frame(self) -> None:
        frame = SpriteLoader.load_frame("dudu", 0)
        assert frame is not None

    def test_load_frame_index_out_of_range(self) -> None:
        with pytest.raises(IndexError):
            SpriteLoader.load_frame("dudu", 99)

    def test_unknown_mascot_id(self) -> None:
        with pytest.raises(ValueError):
            SpriteLoader.load_sprite("unknown")

    def test_get_frame_count(self) -> None:
        assert SpriteLoader.get_frame_count("dudu") == 4
        assert SpriteLoader.get_frame_count("wengweng") == 4

    def test_get_frame_count_unknown(self) -> None:
        assert SpriteLoader.get_frame_count("unknown") == 0

    def test_load_all_sprites(self) -> None:
        for mascot_id in SPRITE_CONFIG:
            frames = SpriteLoader.load_sprite(mascot_id)
            assert len(frames) == 4, f"{mascot_id}: expected 4 frames"


class TestIconLoader:
    """2.11 IconLoader 测试"""

    def test_get_icon_returns_image(self) -> None:
        img = IconLoader.get_icon("tab_checkin")
        assert img is not None

    def test_get_icon_path_returns_path(self) -> None:
        path = IconLoader.get_icon_path("btn_add")
        assert path.exists()

    def test_get_icon_with_color(self) -> None:
        img = IconLoader.get_icon("check_mark", color=(1.0, 0.0, 0.0, 1.0))
        assert img is not None

    def test_unknown_icon(self) -> None:
        with pytest.raises(ValueError):
            IconLoader.get_icon("nonexistent")


class TestPreloadAll:
    """2.12 preload_all 测试"""

    def test_preload_all_returns_counts(self) -> None:
        result = preload_all()
        assert result["sprites"] == 5
        assert result["icons"] == 24

    def test_preload_all_is_idempotent(self) -> None:
        result1 = preload_all()
        result2 = preload_all()
        assert result1 == result2


class TestFonts:
    """2.1〜2.2 字体测试"""

    def test_font_files_exist(self) -> None:
        font_dir = _get_assets_dir() / "fonts"
        assert (font_dir / "PressStart2P-Regular.ttf").exists()
        assert (font_dir / "Silkscreen-Regular.ttf").exists()

    def test_apply_global_font_registers_roboto(self) -> None:
        from kivy.core.text import LabelBase
        apply_global_font()
        assert "Roboto" in LabelBase._fonts
