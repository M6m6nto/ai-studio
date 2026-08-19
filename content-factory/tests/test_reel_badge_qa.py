from pathlib import Path

from engines.reel.badge import render_badge
from engines.reel.qa import similarity


def test_render_badge_creates_rgba_png(tmp_path):
    from PIL import Image

    out = render_badge("Poddubotsky AI", tmp_path / "badge.png")
    assert out.exists()
    img = Image.open(out)
    assert img.mode == "RGBA"
    assert img.width > 0 and img.height > 0


def test_render_badge_scales_with_text_length(tmp_path):
    short = render_badge("A", tmp_path / "short.png")
    long_ = render_badge("Значительно более длинный текст бейджа", tmp_path / "long.png")
    from PIL import Image
    assert Image.open(long_).width > Image.open(short).width


def test_similarity_identical_text_is_one():
    assert similarity("привет мир", "привет мир") == 1.0


def test_similarity_empty_strings_is_zero():
    assert similarity("", "что-то") == 0.0
    assert similarity("что-то", "") == 0.0


def test_similarity_ignores_case_and_whitespace_layout():
    assert similarity("Привет   МИР", "привет мир") == 1.0


def test_similarity_partial_match_is_between_zero_and_one():
    score = similarity("привет дорогой мир", "привет мир")
    assert 0.0 < score < 1.0
