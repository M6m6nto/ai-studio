"""Сборка готового рилса: подстановка сгенерированных сцен, вжигание кинетик-титров,
наложение бейджа, апскейл.

Замена фона реализована на уровне сегментов: там, где агент уже прогнал сегмент
через Higgsfield и дал путь к сгенерированному клипу (--scene N=путь), в монтаж
идёт он; для сегментов без сцены — честный локальный fallback на оригинальный
кусок исходника (см. CLAUDE.md: «если ничего не проходит — заменить сцену
локальным b-roll, не терять время на переборе»), а не пустой кадр или ошибка.

Все клипы таймлайна приводятся к общему видео+аудио формату (WIDTH x HEIGHT,
FPS, AAC 44.1kHz стерео — с тишиной там, где у сцены своего звука нет), иначе
`ffmpeg concat` с `-c copy` падает на несовпадении кодеков/потоков между
разноисточниковыми клипами. Родной звук исходника накладывается уже после
склейки поверх всего таймлайна одним проходом — это и есть «родной звук» из
требований к /рилс, а не микс тишины и оригинала по кусочкам.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

WIDTH, HEIGHT, FPS = 1080, 1920, 30
AUDIO_ARGS = ["-c:a", "aac", "-ar", "44100", "-ac", "2"]
VIDEO_FILTER = f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},fps={FPS}"


class ComposeError(RuntimeError):
    pass


def _run(cmd: list[str], what: str) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise ComposeError(f"{what} не удался: {result.stderr[-800:]}")


def cut_segment(source: Path, start: float, end: float, out_path: Path) -> Path:
    """Fallback-клип из оригинального исходника — если для сегмента ещё нет
    сгенерированной сцены. Звук здесь не важен: он всё равно будет заменён
    родным звуком после склейки, поэтому кодируем с тем же аудио-профилем
    просто ради совместимости потоков при concat."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _run(
        ["ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", str(source),
         "-vf", VIDEO_FILTER, "-c:v", "libx264", "-pix_fmt", "yuv420p",
         *AUDIO_ARGS, str(out_path)],
        f"вырезка сегмента {start}-{end}",
    )
    return out_path


def normalize_clip(clip: Path, duration: float, out_path: Path) -> Path:
    """Приводит сгенерированный клип (может быть без звука, другого разрешения
    и длины) к формату таймлайна: обрезает/зацикливает по длительности сегмента,
    добавляет тихую аудио-дорожку нужного формата для совместимости с concat."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _run(
        ["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(clip),
         "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
         "-t", str(duration), "-vf", VIDEO_FILTER, "-c:v", "libx264", "-pix_fmt", "yuv420p",
         *AUDIO_ARGS, "-shortest", str(out_path)],
        f"нормализация сгенерированного клипа {clip.name}",
    )
    return out_path


def concat_clips(clips: list[Path], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    list_file = out_path.with_suffix(".txt")
    list_file.write_text("".join(f"file '{c.resolve()}'\n" for c in clips), encoding="utf-8")
    _run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
         "-c", "copy", str(out_path)],
        "склейка сегментов",
    )
    return out_path


def mux_native_audio(video_path: Path, audio_source: Path, out_path: Path) -> Path:
    """Заменяет звук всей склеенной дорожки на родной звук исходника (обрезая
    его по длине видео) — «родной звук» из требований к /рилс одним проходом,
    а не кусочно по сегментам."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _run(
        ["ffmpeg", "-y", "-i", str(video_path), "-i", str(audio_source),
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", *AUDIO_ARGS,
         "-shortest", str(out_path)],
        "наложение родного звука",
    )
    return out_path


def burn_subtitles(video_path: Path, ass_path: Path, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _run(
        ["ffmpeg", "-y", "-i", str(video_path), "-vf", f"subtitles={ass_path}",
         "-c:a", "copy", str(out_path)],
        "вжигание кинетик-титров",
    )
    return out_path


def overlay_badge(video_path: Path, badge_path: Path, out_path: Path, margin: int = 48) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _run(
        ["ffmpeg", "-y", "-i", str(video_path), "-i", str(badge_path),
         "-filter_complex", f"overlay=x={margin}:y={margin}",
         "-c:a", "copy", str(out_path)],
        "наложение бейджа",
    )
    return out_path


def upscale_placeholder(video_path: Path, out_path: Path, width: int = WIDTH, height: int = HEIGHT) -> Path:
    """Локальный апскейл через lanczos-фильтр ffmpeg. Настоящий AI-апскейл
    (Higgsfield upscale_video) — отдельный шаг агента в диалоге, не отсюда;
    этот проход нужен только когда исходный материал мельче целевого размера."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _run(
        ["ffmpeg", "-y", "-i", str(video_path), "-vf", f"scale={width}:{height}:flags=lanczos",
         "-c:a", "copy", str(out_path)],
        "локальный апскейл",
    )
    return out_path
