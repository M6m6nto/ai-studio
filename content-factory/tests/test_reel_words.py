import json

import pytest

from engines.reel.words import Word, WordsError, load_whisper_words, plan_segments


def make_words(n: int, word_len: float = 0.4, gap: float = 0.05) -> list[Word]:
    words = []
    t = 0.0
    for i in range(n):
        words.append(Word(text=f"w{i}", start=t, end=t + word_len))
        t += word_len + gap
    return words


def test_plan_segments_never_splits_a_word():
    words = make_words(60, word_len=0.4, gap=0.05)  # ~27s total
    segments = plan_segments(words, max_segments=3, max_total_seconds=30)
    all_texts = {w.text for seg in segments for w in seg.words}
    # каждое слово либо целиком в сегменте, либо не входит вообще
    for seg in segments:
        for w in seg.words:
            assert seg.start <= w.start and w.end <= seg.end


def test_plan_segments_respects_max_total_duration():
    words = make_words(200, word_len=0.4, gap=0.05)  # намного больше 30с
    segments = plan_segments(words, max_segments=3, max_total_seconds=30)
    total = sum(s.duration for s in segments)
    assert total <= 30.5  # небольшой допуск на границы слов


def test_plan_segments_respects_max_segments_count():
    words = make_words(200, word_len=0.4, gap=0.05)
    segments = plan_segments(words, max_segments=3, max_total_seconds=30)
    assert len(segments) <= 3


def test_plan_segments_handles_short_input_gracefully():
    words = make_words(3)
    segments = plan_segments(words, max_segments=3, max_total_seconds=30)
    assert len(segments) >= 1
    assert sum(len(s.words) for s in segments) == 3


def test_plan_segments_empty_raises():
    with pytest.raises(WordsError):
        plan_segments([])


def test_segments_are_chronological_and_non_overlapping():
    words = make_words(60)
    segments = plan_segments(words, max_segments=3, max_total_seconds=30)
    for a, b in zip(segments, segments[1:]):
        assert a.end <= b.start


def test_load_whisper_words_parses_json(tmp_path):
    payload = {
        "segments": [
            {"words": [
                {"word": " Привет", "start": 0.0, "end": 0.3},
                {"word": " мир", "start": 0.3, "end": 0.6},
            ]},
            {"words": [{"word": " .", "start": 0.6, "end": 0.6}]},  # пустое после strip
        ]
    }
    path = tmp_path / "out.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    words = load_whisper_words(path)
    assert [w.text for w in words] == ["Привет", "мир", "."]


def test_load_whisper_words_empty_raises(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"segments": []}), encoding="utf-8")
    with pytest.raises(WordsError):
        load_whisper_words(path)
