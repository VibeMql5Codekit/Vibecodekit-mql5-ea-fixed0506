#!/usr/bin/env python3
"""Render terminal-style screenshots for the quickstart docs.

These PNGs are committed to ``docs/quickstart/img/`` and referenced from
``docs/QUICKSTART.md`` and ``docs/QUICKSTART.vi.md``. They are intentionally
generated (not captured) so they are deterministic, theme-stable, and easy
to regenerate when CLI output changes.

Run:  python scripts/tools/render_quickstart_screenshots.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "quickstart" / "img"
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

BG = (13, 17, 23)               # GitHub dark bg
FG = (230, 237, 243)            # default text
GREEN = (63, 185, 80)
RED = (248, 81, 73)
YELLOW = (210, 153, 34)
BLUE = (88, 166, 255)
MUTED = (139, 148, 158)
PROMPT = (88, 166, 255)

PADDING = 16
LINE_HEIGHT = 22
FONT_SIZE = 14
TITLE_HEIGHT = 28


def _color_for(line: str) -> tuple[int, int, int]:
    s = line.lstrip()
    if s.startswith("$"):
        return FG
    if "PASS" in s.split("—", 1)[0]:
        return GREEN
    if "WARN" in s.split("—", 1)[0]:
        return YELLOW
    if "FAIL" in s.split("—", 1)[0] or "ERROR" in s.split("—", 1)[0]:
        return RED
    if s.startswith("#") or s.startswith("//"):
        return MUTED
    return FG


def render_terminal(lines: list[str], path: Path, title: str = "bash") -> None:
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    font_bold = ImageFont.truetype(FONT_BOLD, FONT_SIZE)

    max_w = max((font.getlength(line) for line in lines), default=200)
    width = int(max_w) + 2 * PADDING
    width = max(width, 720)
    height = TITLE_HEIGHT + len(lines) * LINE_HEIGHT + 2 * PADDING

    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    # title bar
    draw.rectangle((0, 0, width, TITLE_HEIGHT), fill=(22, 27, 34))
    for i, color in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        cx = 14 + i * 18
        draw.ellipse((cx - 6, TITLE_HEIGHT // 2 - 6, cx + 6, TITLE_HEIGHT // 2 + 6),
                     fill=color)
    title_w = font.getlength(title)
    draw.text(((width - title_w) / 2, (TITLE_HEIGHT - FONT_SIZE) / 2 - 1),
              title, fill=MUTED, font=font)

    y = TITLE_HEIGHT + PADDING
    for line in lines:
        if line.startswith("$ "):
            draw.text((PADDING, y), "$", fill=PROMPT, font=font_bold)
            draw.text((PADDING + font.getlength("$ "), y), line[2:],
                      fill=FG, font=font_bold)
        else:
            draw.text((PADDING, y), line, fill=_color_for(line), font=font)
        y += LINE_HEIGHT

    OUT.mkdir(parents=True, exist_ok=True)
    img.save(path)
    print(f"wrote {path.relative_to(REPO)}  ({width}x{height})")


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    return (result.stdout + result.stderr).rstrip("\n")


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def ensure_sample_ea() -> Path:
    ea = REPO / "runtime" / "reference-ea" / "SampleEA" / "SampleEA.mq5"
    if not ea.exists():
        run(["mql5-build", "stdlib", "--name", "SampleEA",
             "--symbol", "EURUSD", "--tf", "H1",
             "--out", str(REPO / "runtime" / "reference-ea" / "SampleEA")])
    return ea


def doctor_lines() -> list[str]:
    output = run(["python", "-m", "vibecodekit_mql5.doctor"])
    head = ["$ python -m vibecodekit_mql5.doctor"]
    return head + strip_ansi(output).splitlines()[:24]


def build_lines() -> list[str]:
    ensure_sample_ea()
    head = ["$ mql5-build stdlib --name SampleEA --symbol EURUSD --tf H1 \\",
            "      --out runtime/reference-ea/SampleEA"]
    return head + [
        "Wrote 17 files to runtime/reference-ea/SampleEA/",
        "  CMagicRegistry.mqh",
        "  CMemorySafety.mqh",
        "  CMfeMaeLogger.mqh",
        "  COnnxLoader.mqh",
        "  CPipNormalizer.mqh",
        "  CRiskGuard.mqh",
        "  CSafeTradeManager.mqh",
        "  CSpreadGuard.mqh",
        "  SampleEA.mq5",
        "  Sets/default.set",
        "  README.md",
    ]


def lint_lines() -> list[str]:
    ea = ensure_sample_ea()
    output = run(["mql5-lint", str(ea.relative_to(REPO))])
    return [f"$ mql5-lint {ea.relative_to(REPO)}",
            *strip_ansi(output).splitlines()]


def trader_lines() -> list[str]:
    ea = ensure_sample_ea()
    output = run(["mql5-trader-check", str(ea.relative_to(REPO))])
    return [f"$ mql5-trader-check {ea.relative_to(REPO)}",
            *strip_ansi(output).splitlines()]


def permission_lines() -> list[str]:
    ea = ensure_sample_ea()
    output = run(["mql5-permission", "--mode", "personal",
                  str(ea.relative_to(REPO))])
    head = ["$ mql5-permission --mode personal \\",
            f"    {ea.relative_to(REPO)}"]
    return head + strip_ansi(output).splitlines()[:18]


def main() -> int:
    render_terminal(build_lines(),      OUT / "01-build.png",
                    title="terminal — mql5-build stdlib")
    render_terminal(lint_lines(),       OUT / "02-lint.png",
                    title="terminal — mql5-lint SampleEA.mq5")
    render_terminal(trader_lines(),     OUT / "03-trader-check.png",
                    title="terminal — mql5-trader-check")
    render_terminal(permission_lines(), OUT / "04-permission.png",
                    title="terminal — mql5-permission")
    return 0


if __name__ == "__main__":
    sys.exit(main())
