"""Фирменный бейдж в угол кадра — тем же тоном, что и badge на карусели/сайте.

Рендерится через PIL (не браузер): бейдж простой и статичный, не стоит платить
холодным стартом Chromium ради одной надписи в углу. Шрифт Inter локально не
установлен — берём DejaVu Sans Bold, визуально близкий sans-serif; при желании
можно подложить .ttf Inter в assets/ и переключить FONT_PATH.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
BG = (19, 26, 42, 235)       # --surface, почти непрозрачный
BORDER = (255, 255, 255, 40)  # var(--border)
TEXT = (230, 234, 242, 255)   # var(--text)


def render_badge(text: str, out_path: Path, font_size: int = 34, pad_x: int = 28, pad_y: int = 16) -> Path:
    font = ImageFont.truetype(FONT_PATH, font_size)
    dummy = Image.new("RGBA", (1, 1))
    bbox = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

    w, h = text_w + pad_x * 2, text_h + pad_y * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    radius = h // 2
    draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=BG, outline=BORDER, width=2)
    draw.text((pad_x - bbox[0], pad_y - bbox[1]), text, font=font, fill=TEXT)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path
