"""UI 测试 conftest — 设置 Kivy headless 后端。"""

from __future__ import annotations

from kivy.config import Config

Config.set("graphics", "backend", "offscreen")
Config.set("input", "emulate", "mouses")
