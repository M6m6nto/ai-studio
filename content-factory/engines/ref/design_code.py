"""Черновое текстовое описание дизайн-кода по кадрам — доминирующие цвета,
формат, светлота. Не заменяет взгляд человека, но экономит первый проход.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image


def _dominant_colors(image: Image.Image, n: int = 3) -> list[tuple[int, int, int]]:
    small = image.convert("RGB").resize((64, 64))
    palette = small.quantize(colors=n, method=Image.MEDIANCUT).convert("RGB")
    colors = palette.getcolors(64 * 64) or []
    colors.sort(key=lambda c: c[0], reverse=True)
    return [c[1] for c in colors[:n]]


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def describe_frames(frame_paths: list[Path]) -> str:
    if not frame_paths:
        return "Кадры не найдены — дизайн-код не построен."

    sample = frame_paths[:: max(1, len(frame_paths) // 4)][:4]
    lines = []
    for path in sample:
        with Image.open(path) as img:
            w, h = img.size
            colors = _dominant_colors(img)
            avg_brightness = sum(sum(c) for c in colors) / (3 * len(colors) * 255)
            tone = "светлый" if avg_brightness > 0.6 else "тёмный" if avg_brightness < 0.35 else "средний"
            lines.append(
                f"{path.name}: {w}x{h}, палитра {', '.join(_hex(c) for c in colors)}, тон {tone}"
            )

    aspect = None
    with Image.open(frame_paths[0]) as first:
        w, h = first.size
        aspect = "вертикаль 9:16" if h > w else "квадрат/горизонталь"

    return f"Формат: {aspect}. Кадры ({len(sample)} из {len(frame_paths)}):\n" + "\n".join(lines)
