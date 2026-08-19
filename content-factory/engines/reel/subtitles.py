"""Кинетик-титры: слова появляются по одному синхронно с речью, а не статичной
плашкой. Реализовано через ASS-субтитры с \\k-тегами (karaoke-timing) — формат,
который ffmpeg умеет вжигать в кадр нативно через фильтр `subtitles=`.
"""
from __future__ import annotations

from pathlib import Path

from engines.reel.words import Segment

_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Kinetic,Inter,64,&H00E6EAF2,&H002DD4BF,&H00131A2A,&H00000000,1,0,0,0,100,100,0,0,1,4,0,2,60,60,220,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _ts(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def _centiseconds(delta: float) -> int:
    return max(0, round(delta * 100))


def segment_to_ass_line(segment: Segment) -> str:
    """Одна событие ASS на сегмент, но текст внутри — по слову через \\k<centisec>,
    поэтому в кадре слова подсвечиваются/появляются по очереди, а не разом."""
    parts = []
    for word in segment.words:
        duration_cs = _centiseconds(word.end - word.start)
        parts.append(f"{{\\k{duration_cs}}}{word.text}")
    text = " ".join(parts)
    return f"Dialogue: 0,{_ts(segment.start)},{_ts(segment.end)},Kinetic,,0,0,0,,{text}"


def build_ass(segments: list[Segment]) -> str:
    lines = [segment_to_ass_line(seg) for seg in segments]
    return _HEADER + "\n".join(lines) + "\n"


def write_ass(segments: list[Segment], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_ass(segments), encoding="utf-8")
    return path
