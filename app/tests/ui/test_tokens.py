"""测试设计令牌常量 — 验证所有令牌值的类型和格式正确性。"""

from __future__ import annotations

from app.ui.tokens import (
    BORDER_WIDTH,
    BTN_HEIGHT,
    CARD_PADDING,
    CARD_SHADOW,
    CARD_WHITE,
    COLORS,
    DOPAMINE_COLORS,
    FONT_PIXEL,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    GRID,
    GRID_UNIT,
    ICON_SIZE,
    NAV_HEIGHT,
    PRIMARY_DARK,
    PRIMARY_YELLOW,
    SEMANTIC_COLORS,
    SHADOW_BLACK,
    SHADOW_COLOR,
    SHADOW_OFFSET,
    SPRITE_SIZE,
    TEXT_BROWN,
    TEXT_GRAY,
)


def _is_valid_hex(value: str) -> bool:
    """验证字符串是否为合法的 7 位 hex 颜色值（如 #FFE030）。"""
    if not value.startswith("#") or len(value) != 7:
        return False
    try:
        int(value[1:], 16)
        return True
    except ValueError:
        return False


class TestMainPalette:
    """1.1 主色板测试"""

    def test_colors_is_dict_of_str(self) -> None:
        assert isinstance(COLORS, dict)
        assert len(COLORS) == 8
        for key, val in COLORS.items():
            assert isinstance(key, str)
            assert isinstance(val, str)

    def test_all_main_colors_are_valid_hex(self) -> None:
        hex_keys = [
            "PRIMARY_YELLOW", "PRIMARY_DARK", "BG_CREAM", "CARD_WHITE",
            "CARD_SHADOW", "TEXT_BROWN", "TEXT_GRAY", "SHADOW_BLACK",
        ]
        for key in hex_keys:
            assert _is_valid_hex(COLORS[key]), f"{key} = {COLORS[key]} is not valid hex"

    def test_convenience_aliases_match(self) -> None:
        assert PRIMARY_YELLOW == COLORS["PRIMARY_YELLOW"]
        assert PRIMARY_DARK == COLORS["PRIMARY_DARK"]
        assert CARD_WHITE == COLORS["CARD_WHITE"]
        assert CARD_SHADOW == COLORS["CARD_SHADOW"]
        assert TEXT_BROWN == COLORS["TEXT_BROWN"]
        assert TEXT_GRAY == COLORS["TEXT_GRAY"]
        assert SHADOW_BLACK == COLORS["SHADOW_BLACK"]


class TestDopamineColors:
    """1.2 多巴胺辅色测试"""

    def test_six_color_families(self) -> None:
        expected = ["coral", "mint", "lavender", "sky", "warm_orange", "watermelon"]
        for name in expected:
            assert name in DOPAMINE_COLORS, f"Missing {name}"

    def test_each_family_has_light_and_dark(self) -> None:
        for name, pair in DOPAMINE_COLORS.items():
            assert "light" in pair, f"{name}: missing light"
            assert "dark" in pair, f"{name}: missing dark"
            assert _is_valid_hex(pair["light"])
            assert _is_valid_hex(pair["dark"])

    def test_dark_is_darker_than_light(self) -> None:
        """暗面色值亮度应低于亮面。"""
        for name, pair in DOPAMINE_COLORS.items():
            # 粗略：暗面各通道和不大于亮面
            light_sum = sum(int(pair["light"][i:i+2], 16) for i in range(1, 7, 2))
            dark_sum = sum(int(pair["dark"][i:i+2], 16) for i in range(1, 7, 2))
            assert dark_sum <= light_sum, f"{name}: dark should be darker than light"


class TestSemanticColors:
    """1.3 功能语义色测试"""

    def test_seven_status_types(self) -> None:
        expected = ["normal", "late", "early_leave", "absent", "leave", "shooting", "completed"]
        for name in expected:
            assert name in SEMANTIC_COLORS, f"Missing {name}"

    def test_each_status_has_block_border_icon(self) -> None:
        for name, colors in SEMANTIC_COLORS.items():
            assert "block" in colors, f"{name}: missing block"
            assert "border" in colors, f"{name}: missing border"
            assert "icon" in colors, f"{name}: missing icon"
            assert _is_valid_hex(colors["block"])
            assert _is_valid_hex(colors["border"])
            assert _is_valid_hex(colors["icon"])


class TestGridConstants:
    """1.4 网格常量测试"""

    def test_grid_is_dict_of_int(self) -> None:
        for key, val in GRID.items():
            assert isinstance(val, int), f"{key} should be int"
            assert val > 0, f"{key} should be positive"

    def test_grid_aliases_are_positive(self) -> None:
        assert GRID_UNIT > 0
        assert BORDER_WIDTH > 0
        assert BTN_HEIGHT > 0
        assert CARD_PADDING > 0
        assert NAV_HEIGHT > 0
        assert ICON_SIZE > 0
        assert SPRITE_SIZE > 0

    def test_grid_unit_is_8(self) -> None:
        assert GRID_UNIT == 8

    def test_values_are_multiples_of_grid_unit(self) -> None:
        """CARD_PADDING、ICON_SIZE、SPRITE_SIZE 应为 GRID_UNIT 的倍数。"""
        assert CARD_PADDING % GRID_UNIT == 0
        assert ICON_SIZE % GRID_UNIT == 0
        assert SPRITE_SIZE % GRID_UNIT == 0


class TestFontConstants:
    """1.5 像素字体常量测试"""

    def test_font_names_are_strings(self) -> None:
        assert isinstance(FONT_PIXEL, str)
        assert len(FONT_PIXEL) > 0

    def test_font_sizes_are_positive(self) -> None:
        assert FONT_SIZE_TITLE > 0
        assert FONT_SIZE_BODY > 0
        assert FONT_SIZE_SMALL > 0

    def test_font_sizes_order(self) -> None:
        assert FONT_SIZE_TITLE > FONT_SIZE_BODY
        assert FONT_SIZE_BODY > FONT_SIZE_SMALL


class TestShadowConstants:
    """1.6 像素阴影常量测试"""

    def test_shadow_offset_positive(self) -> None:
        assert SHADOW_OFFSET > 0

    def test_shadow_color_is_black(self) -> None:
        assert SHADOW_COLOR == "#000000"

    def test_shadow_color_is_valid_hex(self) -> None:
        assert _is_valid_hex(SHADOW_COLOR)
