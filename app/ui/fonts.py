"""全局字体加载器 — 注册秋叶圆体 为全局默认字体，默认粗体，并注册彩色 emoji。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from kivy.core.text import LabelBase
from kivy.uix.label import Label as KivyLabel

_FONT_DIR = (Path(__file__).parent / "assets" / "fonts").resolve()
_FONT_PATH = _FONT_DIR / "QiuYeYuanTi-16.ttf"

# Windows 自带 Segoe UI Emoji（彩色 emoji 字体）
#
# 曾尝试加入 /system/fonts/NotoColorEmoji.ttf 修复安卓真机 emoji 显示成方块的
# 问题, 但真机测试出现启动即崩溃循环 (logcat: Fatal signal 11 SIGSEGV,
# tid=Jit thread pool) —— Kivy 的 SDL2_ttf/FreeType 文字渲染管线对
# NotoColorEmoji 使用的 CBDT/CBLC 彩色位图字形表兼容性差, 是已知的崩溃诱因。
# 显示成方块是外观问题, 崩溃是致命问题, 两害相权已回退, 不要重新加入
# 这个字体路径, 除非先验证目标设备的 Kivy 版本明确支持彩色位图字体。
_EMOJI_FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/seguiemj.ttf"),
    Path("C:/Windows/Fonts/segoeuiemoji.ttf"),
]

_Label___init__ = KivyLabel.__init__


def _label_init_bold(self: KivyLabel, **kwargs: object) -> None:
    kwargs.setdefault("bold", True)
    _Label___init__(self, **kwargs)


# ── 文字超采样 ────────────────────────────────────────────────────────────
# 真机把 420 逻辑画布用 ScatterLayout 整体线性放大约 2.57x, 文字先按逻辑小字号
# 光栅化再被 GPU 拉大 → 边缘发糊。超采样: 光栅化时 font_size×SS 得到 SS 倍分辨率
# 的高清字形, 渲染后把 texture_size÷SS 压回(布局占用分毫不变), 经 Scatter ×SS
# 放大后高清纹理 1:1 呈现, 不糊。SS 由 main.py 按真机整体缩放比设入; 桌面/测试
# 锁定 420 窗口 → SS=1 → 全程退化为纯透传, 渲染与全量测试均不受影响。
_supersample_scale: float = 1.0
_orig_texture_update = KivyLabel.texture_update


def set_supersample_scale(scale: float) -> None:
    """设置全局文字超采样系数(通常 = 真机整体缩放比)。main.py 算出 scale 后调用。"""
    global _supersample_scale
    _supersample_scale = scale


def get_supersample_scale() -> float:
    """当前文字超采样系数; 默认 1.0(不超采样)。"""
    return _supersample_scale


def _supersample_texture_update(
    label: Any, orig: Callable[..., None], ss: float, *largs: Any
) -> None:
    """以 ss 倍分辨率光栅化 label 文字, 渲染后把绘制矩形压回 1x。

    只临时改 core label 的 options['font_size'] / usersize(普通 dict/属性, 改动
    不触发 widget property 事件 → 无递归、无持续重绘), 渲染后立即在 finally 还原。
    ss<=1 时纯透传; texture 为 None(空文本)时跳过压回, 不崩。
    """
    if ss <= 1.0:
        orig(label, *largs)
        return
    core = label._label
    opts = core.options
    orig_fs = opts.get("font_size")
    orig_usersize = list(core.usersize) if core.usersize is not None else core.usersize
    if orig_fs is not None:
        opts["font_size"] = orig_fs * ss
    if core.usersize is not None:
        core.usersize = [v * ss if v is not None else v for v in core.usersize]
    try:
        orig(label, *largs)
    finally:
        opts["font_size"] = orig_fs
        core.usersize = orig_usersize
    tex = label.texture
    if tex is not None:
        label.texture_size = [tex.size[0] / ss, tex.size[1] / ss]


def _ss_texture_update(self: KivyLabel, *largs: Any) -> None:
    """安装到 Kivy Label.texture_update 的全局补丁 — 读运行时超采样系数。"""
    _supersample_texture_update(self, _orig_texture_update, _supersample_scale, *largs)


# Kivy 用 Clock.create_trigger(self.texture_update) + WeakMethod 调度纹理刷新,
# WeakMethod 靠函数 __name__ 做 getattr(instance, name) 回调 → 补丁函数名必须仍是
# 'texture_update', 否则 Clock.tick 时抛 AttributeError(实例上没有 _ss_texture_update)。
_ss_texture_update.__name__ = "texture_update"
_ss_texture_update.__qualname__ = "Label.texture_update"


def apply_global_font() -> None:
    """注册秋叶圆体 为 Kivy 全局默认字体 + 默认粗体 + 彩色 emoji 字体。

    Kivy 所有 Label 默认 font_name='Roboto'，先清除内置注册，
    再用秋叶圆体 覆盖 Roboto 名字。必须在创建任何 Widget 之前调用。

    额外注册 'emoji' 字体名指向 Segoe UI Emoji；标签里通过
    markup `[font=emoji]🎯[/font]` 即可显示彩色 emoji。
    """
    if not _FONT_PATH.exists():
        return

    font_path_str = str(_FONT_PATH)

    if "Roboto" in LabelBase._fonts:
        del LabelBase._fonts["Roboto"]

    LabelBase.register(name="Roboto", fn_regular=font_path_str)

    # 全局默认粗体 (合成粗体, 无需 Bold 字重文件)
    KivyLabel.__init__ = _label_init_bold  # type: ignore[method-assign]

    # 全局文字超采样补丁 — 真机文字按屏幕像素高清光栅化; SS=1(桌面/测试)时纯透传
    KivyLabel.texture_update = _ss_texture_update  # type: ignore[method-assign]

    # 注册 emoji 字体（Windows Segoe UI Emoji）
    for emoji_path in _EMOJI_FONT_CANDIDATES:
        if emoji_path.exists():
            LabelBase.register(name="emoji", fn_regular=str(emoji_path))
            break


def emj(char: str) -> str:
    """包装 emoji 字符为 markup —— 标签需 markup=True 才生效。

    若 emoji 字体未注册（如测试环境跳过了 apply_global_font），
    返回纯字符避免 Label 渲染时找不到 emoji.ttf 报错。
    """
    if "emoji" not in LabelBase._fonts:
        return char
    return f"[font=emoji]{char}[/font]"
