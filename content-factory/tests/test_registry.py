import json

import pytest

from engines.common.registry import CodewordTakenError, Registry, RegistryError, slugify


@pytest.fixture()
def reg(tmp_path):
    return Registry(tmp_path / "registry")


def test_slugify_transliterates_ascii_only():
    assert slugify("Локальный AI стек") == "ai"
    assert slugify("GitHub в промпт") == "github"
    assert slugify("") == "item"


def test_new_item_creates_card_and_reserves_codeword(reg):
    item = reg.new_item("Локальный AI стек", source="instagram", codeword="СТЕК")
    assert item["slug"]
    assert item["codeword"] == "СТЕК"
    assert item["steps"]["trend"] == "todo"
    assert reg.is_codeword_taken("стек")  # регистронезависимо
    assert reg.item_path(item["slug"]).exists()


def test_duplicate_codeword_rejected(reg):
    reg.new_item("Тема раз", source="instagram", codeword="ТЕСТ")
    with pytest.raises(CodewordTakenError):
        reg.new_item("Тема два", source="instagram", codeword="тест")


def test_duplicate_title_gets_suffixed_slug(reg):
    a = reg.new_item("Одна тема", source="instagram", codeword="ОДИН")
    b = reg.new_item("Одна тема", source="instagram", codeword="ДВА")
    assert a["slug"] != b["slug"]


def test_set_step_updates_and_persists(reg):
    item = reg.new_item("Тема", source="instagram", codeword="КОД")
    reg.set_step(item["slug"], "trend", "done")
    reloaded = reg.load_item(item["slug"])
    assert reloaded["steps"]["trend"] == "done"


def test_set_step_rejects_unknown_step(reg):
    item = reg.new_item("Тема", source="instagram", codeword="XYZ")
    with pytest.raises(RegistryError):
        reg.set_step(item["slug"], "nonexistent", "done")


def test_list_items_and_index(reg):
    reg.new_item("Тема Раз", source="instagram", codeword="РАЗ")
    reg.new_item("Тема Два", source="tiktok", codeword="ДВА")
    items = reg.list_items()
    assert {i["codeword"] for i in items} == {"РАЗ", "ДВА"}

    lines = reg.index_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    row = json.loads(lines[0])
    assert set(row) == {"slug", "codeword", "title", "steps", "updated_at"}


def test_load_missing_item_raises(reg):
    with pytest.raises(RegistryError):
        reg.load_item("does-not-exist")
