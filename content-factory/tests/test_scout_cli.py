import json

from engines.common.registry import Registry
from engines.scout.cli import main as scout_main


def test_pick_creates_item_with_full_topic_provenance(tmp_path, monkeypatch):
    monkeypatch.setattr("engines.scout.cli.ROOT", tmp_path)
    fixture = "tests/fixtures/donor_posts_sample.json"

    code = scout_main(["--niche", "тест", "--fixtures", fixture, "--pick", "1"])
    assert code == 0

    registry = Registry(tmp_path / "registry")
    items = registry.list_items()
    assert len(items) == 1
    item = registry.load_item(items[0]["slug"])

    topic = item["topic"]
    assert topic["ref_url"], "должна сохраниться ссылка на референс"
    assert topic["ref_post_id"], "должен сохраниться id поста"
    assert topic["ref_account"], "должен сохраниться донор-аккаунт — нужен для sheets_sync и /реф"
    assert topic["niche"] == "тест"
