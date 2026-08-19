"""Слова с таймкодами → сегменты сториборда, режем строго по границам слов.

Источник таймкодов — whisper --output_format json (word_timestamps=True), формат:
{"segments": [{"words": [{"word": " привет", "start": 0.12, "end": 0.38}, ...]}]}

CLAUDE.md: максимум 3 сториборда (~30 сек) — не растягиваем эксперименты с генерацией.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float


@dataclass(frozen=True)
class Segment:
    index: int
    start: float
    end: float
    text: str
    words: tuple[Word, ...]

    @property
    def duration(self) -> float:
        return self.end - self.start


class WordsError(RuntimeError):
    pass


def load_whisper_words(json_path: Path) -> list[Word]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    words: list[Word] = []
    for seg in data.get("segments", []):
        for w in seg.get("words", []):
            text = (w.get("word") or "").strip()
            if not text:
                continue
            words.append(Word(text=text, start=float(w["start"]), end=float(w["end"])))
    if not words:
        raise WordsError("В whisper JSON нет ни одного слова с таймкодом")
    return words


def plan_segments(words: list[Word], max_segments: int = 3, max_total_seconds: float = 30.0) -> list[Segment]:
    """Делит слова на до max_segments сегментов, каждый обрывается только на границе
    слова. Суммарная длительность не превышает max_total_seconds — лишние слова в
    хвосте просто не попадают ни в один сегмент (не растягиваем сториборд).
    """
    if not words:
        raise WordsError("Нечего сегментировать — пустой список слов")

    total_available = words[-1].end - words[0].start
    total_target = min(total_available, max_total_seconds)
    per_segment = total_target / max_segments

    segments: list[Segment] = []
    cursor = 0  # индекс в words, откуда начинается следующий сегмент
    origin = words[0].start

    for seg_index in range(1, max_segments + 1):
        if cursor >= len(words):
            break
        seg_words: list[Word] = []
        target_end = origin + seg_index * per_segment
        i = cursor
        while i < len(words) and (not seg_words or words[i].end <= target_end):
            seg_words.append(words[i])
            i += 1
        if not seg_words:
            break
        segments.append(Segment(
            index=seg_index,
            start=seg_words[0].start,
            end=seg_words[-1].end,
            text=" ".join(w.text for w in seg_words),
            words=tuple(seg_words),
        ))
        cursor = i

    return segments
