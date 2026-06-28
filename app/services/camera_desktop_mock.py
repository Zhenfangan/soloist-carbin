"""桌面端相机 Mock — 弹确认框，自动生成占位图，模拟拍照流程"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .camera_service import CameraService


class DesktopCameraMock(CameraService):
    """开发用 Mock：弹确认框，确认后生成一张带时间戳的纯色占位 PNG，模拟拍照。"""

    _BASE_DIR = Path("user_data/photos")

    def take_photo(
        self,
        period: str,
        action: str,
        on_done: Callable[[Path | None], None],
    ) -> None:
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.label import Label
        from kivy.uix.popup import Popup

        period_label = {"morning": "上午", "afternoon": "下午", "evening": "晚上"}.get(period, period)
        action_label = "签到" if action == "in" else "签退"

        content = BoxLayout(orientation="vertical", spacing=12, padding=16)
        msg = Label(
            text=f"模拟拍照：{period_label}{action_label}\n\n点击「确认」生成占位图片",
            halign="center",
            valign="middle",
        )
        msg.bind(size=msg.setter("text_size"))
        btn_row = BoxLayout(size_hint_y=None, height=44, spacing=8)
        content.add_widget(msg)
        content.add_widget(btn_row)

        popup = Popup(
            title="📷 拍照打卡（桌面模拟）",
            content=content,
            size_hint=(0.8, 0.4),
            auto_dismiss=False,
        )

        def _confirm(*_: object) -> None:
            popup.dismiss()
            dest = self._generate_placeholder(period, action)
            on_done(dest)

        def _cancel(*_: object) -> None:
            popup.dismiss()
            on_done(None)

        btn_cancel = Button(text="取消")
        btn_cancel.bind(on_press=_cancel)
        btn_ok = Button(text="确认拍照")
        btn_ok.bind(on_press=_confirm)
        btn_row.add_widget(btn_cancel)
        btn_row.add_widget(btn_ok)

        popup.open()

    # ── 占位图生成 ──────────────────────────────────────────

    def _generate_placeholder(self, period: str, action: str) -> Path:
        """生成一张带标注的纯色 PNG，存入 user_data/photos/{date}/。"""
        from app.utils.clock import get_clock
        date_str = get_clock().today_str()
        dest_dir = self._BASE_DIR / date_str
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{period}_{action}.png"

        try:
            from PIL import Image, ImageDraw, ImageFont

            colors = {
                ("morning", "in"):   (255, 220, 100),
                ("morning", "out"):  (100, 200, 255),
                ("afternoon", "in"): (180, 255, 150),
                ("afternoon", "out"): (255, 160, 160),
            }
            bg = colors.get((period, action), (200, 200, 200))
            img = Image.new("RGB", (320, 320), bg)
            draw = ImageDraw.Draw(img)
            period_cn = {"morning": "上午", "afternoon": "下午", "evening": "晚上"}.get(period, period)
            action_cn = "签到" if action == "in" else "签退"
            from app.utils.clock import get_clock
            time_str = get_clock().current_time_str()[:5]
            draw.text((160, 130), f"{period_cn}{action_cn}", fill=(60, 60, 60), anchor="mm")
            draw.text((160, 175), time_str, fill=(80, 80, 80), anchor="mm")
            draw.text((160, 220), date_str, fill=(100, 100, 100), anchor="mm")
            img.save(dest)
        except Exception:
            # PIL 不可用时写入最小合法 PNG
            dest.write_bytes(_MINIMAL_PNG)

        return dest


# 1×1 透明 PNG（PIL 不可用时的 fallback）
_MINIMAL_PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
    b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
    b'\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18'
    b'\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
)
