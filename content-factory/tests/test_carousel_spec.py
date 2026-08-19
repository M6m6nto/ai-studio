import pytest

from engines.carousel.spec import SLIDE_COUNT, CarouselSpecError, build_spec


def make_item(**overrides):
    item = {
        "codeword": "ТЕСТ",
        "topic": {"title": "Тестовая тема"},
        "ref": {"verified_claims": []},
        "script": {
            "hooks": ["Хук раз"],
            "body": " ".join([f"Предложение номер {i}." for i in range(1, 13)]),
            "caption": "Подпись к посту.",
        },
    }
    item.update(overrides)
    return item


def test_build_spec_produces_eight_slides():
    slides, infographic = build_spec(make_item())
    assert len(slides) == SLIDE_COUNT
    assert slides[0].kind == "cover"
    assert slides[-1].kind == "cta"
    assert all(s.kind == "content" for s in slides[1:-1])


def test_cover_uses_first_hook():
    slides, _ = build_spec(make_item())
    assert slides[0].title == "Хук раз"


def test_cover_falls_back_to_topic_title_without_hooks():
    item = make_item()
    item["script"]["hooks"] = []
    slides, _ = build_spec(item)
    assert slides[0].title == "Тестовая тема"


def test_empty_body_raises():
    item = make_item()
    item["script"]["body"] = ""
    with pytest.raises(CarouselSpecError):
        build_spec(item)


def test_infographic_prefers_verified_claims():
    item = make_item(ref={"verified_claims": ["Факт раз", "Факт два"]})
    _, infographic = build_spec(item)
    assert infographic.stats == ["Факт раз", "Факт два"]


def test_infographic_falls_back_to_body_sentences_without_claims():
    _, infographic = build_spec(make_item())
    assert len(infographic.stats) > 1  # не один огрызок, а несколько предложений


def test_short_body_pads_content_slots_without_crashing():
    item = make_item()
    item["script"]["body"] = "Одно предложение."
    slides, _ = build_spec(item)
    assert len(slides) == SLIDE_COUNT
