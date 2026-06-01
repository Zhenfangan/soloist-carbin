"""Soloist Cabin Pro — Kivy/KivyMD APP 入口"""

from __future__ import annotations

from kivy.config import Config

Config.set("graphics", "width", "400")
Config.set("graphics", "height", "700")

# Kivy Config must be set before importing kivy modules
from kivymd.app import MDApp  # noqa: E402
from kivymd.uix.boxlayout import MDBoxLayout  # noqa: E402
from kivymd.uix.label import MDLabel  # noqa: E402
from kivymd.uix.screen import MDScreen  # noqa: E402

from app.db import init_db  # noqa: E402


class MainScreen(MDScreen):  # type: ignore[misc]
    """主界面占位"""

    def __init__(self, **kwargs):  # type: ignore[no-untyped-def]
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation="vertical", padding=20, spacing=20)
        layout.add_widget(
            MDLabel(
                text="Soloist Cabin Pro",
                font_style="H4",
                halign="center",
            )
        )
        layout.add_widget(
            MDLabel(
                text="自律打卡，从今天开始",
                font_style="Subtitle1",
                halign="center",
            )
        )
        self.add_widget(layout)


class SoloistCabinApp(MDApp):  # type: ignore[misc]
    """Soloist Cabin Pro 主 APP"""

    def build(self) -> MainScreen:
        self.title = "Soloist Cabin Pro"
        init_db()
        return MainScreen()  # type: ignore[no-untyped-call]


def main() -> None:
    SoloistCabinApp().run()


if __name__ == "__main__":
    main()
