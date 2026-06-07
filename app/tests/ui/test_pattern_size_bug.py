"""防 size=(w, h) 同 pattern bug 退化的全 codebase grep 测试。

每一个 Rectangle(pos=(x + w - bw, y), size=...) 在凸起暗面 right / 凹陷亮面 right
位置都应该是 size=(bw, h), 不能是 size=(w, h) (会画一个全宽矩形覆盖出去)。

历史上 wave 1 + Task 5 漏掉了 14 处, Phase 2 Batch A 一次修干净。
"""

from __future__ import annotations

import re
from pathlib import Path


# 项目根 — 测试运行时 PWD 是项目根
PROJECT_ROOT = Path(__file__).resolve().parents[3]
UI_DIR = PROJECT_ROOT / "app" / "ui"

# 匹配 Rectangle(pos=(x + w - bw, y), size=(w, h)) — 没有 bw 的 w
BAD_PATTERN = re.compile(
    r"Rectangle\(\s*pos=\(x\s*\+\s*w\s*-\s*bw,\s*y\),\s*size=\(w,\s*h\)\s*\)"
)


def test_no_w_h_size_in_right_edge_rectangle() -> None:
    """全 app/ui/ 下没有 Rectangle(pos=(x+w-bw, y), size=(w, h)) — 必须是 size=(bw, h)。"""
    violations: list[str] = []
    for path in UI_DIR.rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(content.splitlines(), start=1):
            if BAD_PATTERN.search(line):
                violations.append(f"{path.relative_to(PROJECT_ROOT)}:{lineno}: {line.strip()}")

    assert violations == [], (
        "发现同 pattern size=(w, h) bug, 应为 (bw, h):\n  " + "\n  ".join(violations)
    )
