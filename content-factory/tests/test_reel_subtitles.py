from engines.reel.subtitles import _centiseconds, _ts, build_ass, segment_to_ass_line
from engines.reel.words import Segment, Word


def make_segment(index=1) -> Segment:
    words = (
        Word(text="Привет", start=0.0, end=0.4),
        Word(text="мир", start=0.45, end=0.8),
    )
    return Segment(index=index, start=0.0, end=0.8, text="Привет мир", words=words)


def test_ts_formats_hours_minutes_seconds():
    assert _ts(0) == "0:00:00.00"
    assert _ts(65.5) == "0:01:05.50"
    assert _ts(3661.25) == "1:01:01.25"


def test_ts_clamps_negative_to_zero():
    assert _ts(-1) == "0:00:00.00"


def test_centiseconds_rounds_to_nearest():
    assert _centiseconds(0.4) == 40
    assert _centiseconds(0.004) == 0
    assert _centiseconds(-1) == 0


def test_segment_to_ass_line_has_per_word_karaoke_tags():
    line = segment_to_ass_line(make_segment())
    assert line.startswith("Dialogue: 0,0:00:00.00,0:00:00.80,Kinetic,,0,0,0,,")
    assert "{\\k40}Привет" in line
    assert "{\\k35}мир" in line  # 0.8-0.45=0.35s -> 35cs


def test_build_ass_includes_header_and_all_segments():
    segments = [make_segment(1), make_segment(2)]
    ass = build_ass(segments)
    assert "[V4+ Styles]" in ass
    assert ass.count("Dialogue:") == 2


def test_build_ass_is_valid_style_line_format():
    ass = build_ass([make_segment()])
    assert "Style: Kinetic,Inter,64" in ass
