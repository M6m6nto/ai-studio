import pytest

from engines.funnel.spec import FunnelSpecError, build_funnel_spec


def make_item(**overrides):
    item = {
        "slug": "test-item",
        "codeword": "СЛОВО",
        "topic": {"title": "Тема"},
        "script": {"caption": "Подпись."},
        "artifacts": {"guide_url": "https://example.com/guides/test-item/"},
    }
    item.update(overrides)
    return item


def test_build_funnel_spec_has_trigger_matching_codeword():
    spec = build_funnel_spec(make_item())
    assert spec["trigger"]["value"] == "СЛОВО"
    assert spec["trigger"]["type"] == "keyword"


def test_build_funnel_spec_welcome_button_points_to_guide_url():
    spec = build_funnel_spec(make_item())
    welcome = spec["steps"][0]
    assert welcome["kind"] == "welcome"
    assert welcome["button"]["url"] == "https://example.com/guides/test-item/"


def test_build_funnel_spec_has_reminder_and_offer_steps():
    kinds = [s["kind"] for s in build_funnel_spec(make_item())["steps"]]
    assert "reminder" in kinds
    assert "offer" in kinds


def test_build_funnel_spec_offer_uses_custom_reminder_hours():
    spec = build_funnel_spec(make_item(), reminder_hours=6.0)
    offer = next(s for s in spec["steps"] if s["kind"] == "offer")
    assert offer["delay_hours"] == 6.0


def test_build_funnel_spec_missing_guide_url_raises():
    item = make_item(artifacts={})
    with pytest.raises(FunnelSpecError):
        build_funnel_spec(item)


def test_build_funnel_spec_missing_codeword_raises():
    item = make_item(codeword="")
    with pytest.raises(FunnelSpecError):
        build_funnel_spec(item)


def test_build_funnel_spec_autoresponder_uses_codeword():
    spec = build_funnel_spec(make_item())
    assert spec["autoresponder"]["trigger_keyword"] == "СЛОВО"
