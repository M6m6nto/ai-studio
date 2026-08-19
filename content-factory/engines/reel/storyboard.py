"""Раскадровка строится на реальных кадрах исходника (CLAUDE.md), не на фантазии
модели. Здесь только механика: кадр на сегмент + манифест для генерации сцен.

Сама генерация фона (Higgsfield MCP) — не отсюда: движок не имеет доступа к
Higgsfield как к REST API (это MCP-инструмент в диалоге агента), поэтому манифест
только описывает, что нужно сгенерировать, а сам вызов агент делает в разговоре
и результат подаёт обратно в /рилс --compose --scene N=путь.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from engines.reel.words import Segment


class StoryboardError(RuntimeError):
    pass


def grab_frame(video_path: Path, at_second: float, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["ffmpeg", "-y", "-ss", str(at_second), "-i", str(video_path), "-frames:v", "1", str(out_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise StoryboardError(f"ffmpeg не смог взять кадр на {at_second}с из {video_path}: {result.stderr[-400:]}")
    return out_path


def build_storyboard(segments: list[Segment], source_video: Path, frames_dir: Path) -> dict:
    entries = []
    for seg in segments:
        mid = (seg.start + seg.end) / 2
        frame_path = frames_dir / f"segment-{seg.index}.png"
        grab_frame(source_video, mid, frame_path)
        entries.append({
            "index": seg.index,
            "start": seg.start,
            "end": seg.end,
            "duration": round(seg.duration, 2),
            "text": seg.text,
            "reference_frame": str(frame_path),
            "scene_clip": None,  # заполняется после ручной/агентской генерации в Higgsfield
        })
    return {"segments": entries}


def write_storyboard(manifest: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_storyboard(path: Path) -> dict:
    if not path.exists():
        raise StoryboardError(f"Сториборд не найден: {path}. Сначала запусти /рилс --plan")
    return json.loads(path.read_text(encoding="utf-8"))
