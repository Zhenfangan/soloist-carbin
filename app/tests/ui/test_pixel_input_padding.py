"""测试 PixelInput padding 为 4 元素列表, 防止 text 渲染 clip。"""
from app.ui.components.pixel_input import PixelInput


def test_padding_is_4_element_list() -> None:
    """实例化 PixelInput, 校验 padding 是 [pad, pad, pad, pad] 4 元素。"""
    inp = PixelInput()
    assert len(inp.padding) == 4, f"期望 padding 4 元素, 实际 {len(inp.padding)}: {inp.padding}"
    assert all(v == inp.padding[0] for v in inp.padding), (
        f"期望 padding 4 元素值相同, 实际: {inp.padding}"
    )
