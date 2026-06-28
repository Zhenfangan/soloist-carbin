"""像素景观背景资源：路径常量。

所有对背景图的引用必须通过此模块，严禁硬编码路径。
"""
from __future__ import annotations

# 背景：纯天空层（无草地），替换背景只需修改此常量
BG_LANDSCAPE: str = "doc/ui-design/ip/images/sky-background.png"

# 草地前景：预裁剪好的草地+土壤层，顶部透明，锯齿边界已由用户裁剪好
_GRASS_FRONT: str = "doc/ui-design/ip/images/grass-front.png"


def get_grass_overlay_path() -> str:
    """返回草地前景图路径。"""
    return _GRASS_FRONT
