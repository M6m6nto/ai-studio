"""Контроль качества готового ролика: повторная расшифровка и сверка со скриптом
(CLAUDE.md: приёмка ролика — одна из четырёх точек, где участвует человек;
здесь — механическая проверка, которая эту приёмку готовит, а не заменяет).
"""
from __future__ import annotations

import difflib
from pathlib import Path

from engines.ref import frames, transcript


class QAError(RuntimeError):
    pass


def resync_transcript(video_path: Path, work_dir: Path) -> str | None:
    audio_path = work_dir / "qa_audio.wav"
    frames.extract_audio(video_path, audio_path)
    return transcript.transcribe(audio_path)


def similarity(expected_text: str, actual_text: str) -> float:
    a = " ".join(expected_text.lower().split())
    b = " ".join(actual_text.lower().split())
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()
