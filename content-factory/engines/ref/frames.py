"""Нарезка кадров из исходника через ffmpeg — для дизайн-кода и раскадровки."""
from __future__ import annotations

import subprocess
from pathlib import Path


class FramesError(RuntimeError):
    pass


def probe_duration(video_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise FramesError(f"ffprobe не смог прочитать {video_path}: {result.stderr.strip()}")
    return float(result.stdout.strip())


def extract_frames(video_path: Path, out_dir: Path, every_sec: float = 1.0) -> list[Path]:
    """Кадр раз в every_sec секунд, PNG, пронумерованы по порядку."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = out_dir / "frame-%04d.png"
    fps = 1.0 / every_sec
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(video_path), "-vf", f"fps={fps}", str(pattern)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise FramesError(f"ffmpeg не смог нарезать кадры из {video_path}: {result.stderr[-500:]}")
    return sorted(out_dir.glob("frame-*.png"))


def extract_audio(video_path: Path, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-acodec", "pcm_s16le",
         "-ar", "16000", "-ac", "1", str(out_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise FramesError(f"ffmpeg не смог извлечь звук из {video_path}: {result.stderr[-500:]}")
    return out_path
