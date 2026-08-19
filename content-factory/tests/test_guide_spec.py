import pytest

from engines.guide.spec import GuideSpecError, build_guide_content


def make_item(**overrides):
    item = {
        "codeword": "СЛОВО",
        "topic": {"title": "Тема гайда", "ref_url": "https://example.com/post"},
        "script": {"body": "Первое предложение. " * 20},
    }
    item.update(overrides)
    return item


def test_build_guide_content_has_required_fields():
    content = build_guide_content(make_item())
    assert content["title"] == "Тема гайда"
    assert content["codeword"] == "СЛОВО"
    assert content["source_url"] == "https://example.com/post"
    assert content["lead"]
    assert content["body"]


def test_lead_is_shorter_than_body():
    content = build_guide_content(make_item())
    assert len(content["lead"]) < len(content["body"])


def test_empty_body_raises():
    item = make_item(script={"body": ""})
    with pytest.raises(GuideSpecError):
        build_guide_content(item)


def test_missing_ref_url_is_none_not_crash():
    item = make_item(topic={"title": "Тема без ссылки"})
    content = build_guide_content(item)
    assert content["source_url"] is None
