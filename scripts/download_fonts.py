"""下载像素字体文件到 app/ui/assets/fonts/ 目录。"""

from __future__ import annotations

import os
import sys
import urllib.request
import zipfile
from pathlib import Path

FONTS_DIR = Path(__file__).parent.parent / "app" / "ui" / "assets" / "fonts"

FONT_URLS = {
    "PressStart2P-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/pressstart2p/PressStart2P-Regular.ttf",
    "Silkscreen-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/silkscreen/Silkscreen-Regular.ttf",
    "Silkscreen-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/silkscreen/Silkscreen-Bold.ttf",
}


def download_font(url: str, dest: Path) -> bool:
    """下载单个字体文件。"""
    print(f"  Downloading {dest.name}...")
    try:
        urllib.request.urlretrieve(url, str(dest))
        print(f"    OK ({dest.stat().st_size} bytes)")
        return True
    except Exception as e:
        print(f"    Failed: {e}")
        return False


def main() -> int:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)

    success = 0
    for filename, url in FONT_URLS.items():
        dest = FONTS_DIR / filename
        if dest.exists():
            print(f"  {filename} already exists, skipping.")
            success += 1
            continue
        if download_font(url, dest):
            success += 1

    print(f"\nDownloaded {success}/{len(FONT_URLS)} fonts.")
    return 0 if success == len(FONT_URLS) else 1


if __name__ == "__main__":
    sys.exit(main())
