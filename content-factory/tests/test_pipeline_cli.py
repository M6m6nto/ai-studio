"""Тесты на саму механику --dry-run / автопродвижение оркестратора, без
реального запуска под-движков (Playwright/ffmpeg) — те уже покрыты своими
модульными тестами. Здесь проверяем цикл "продвинуть -> перечитать статус".
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engines.common.registry import Registry
from engines.pipeline import cli as pipeline_cli


@pytest.fixture()
def registry_with_item(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline_cli, "ROOT", tmp_path)
    reg = Registry(tmp_path / "registry")
    item = reg.new_item("Тема", source="instagram", codeword="СЛОВО")
    item["script"] = {"body": "Текст.", "caption": "Подпись."}
    reg.save_item(item)
    return reg, item["slug"]


def test_dry_run_never_calls_runners(registry_with_item, monkeypatch, capsys):
    reg, slug = registry_with_item
    called = []
    monkeypatch.setattr(pipeline_cli, "_register_runners", lambda: called.append("registered"))

    code = pipeline_cli.main(["--slug", slug, "--dry-run"])

    assert code == 0
    assert called == []  # раннеры даже не импортировались
    out = capsys.readouterr().out
    assert "carousel" in out and "guide" in out


def test_auto_run_advances_step_and_marks_registry(registry_with_item, monkeypatch, capsys):
    reg, slug = registry_with_item
    calls = []

    def fake_register():
        pipeline_cli._RUNNERS.update({
            "ref": lambda s: 0,
            "carousel": lambda s: (calls.append(("carousel", s)), reg.set_step(s, "carousel", "review"), 0)[-1],
            "guide": lambda s: (calls.append(("guide", s)), reg.set_step(s, "guide", "review"), 0)[-1],
            "funnel": lambda s: 0,
            "deliver": lambda s: 0,
        })

    monkeypatch.setattr(pipeline_cli, "_register_runners", fake_register)
    monkeypatch.setattr(pipeline_cli, "optional", lambda key: None)

    code = pipeline_cli.main(["--slug", slug])

    assert code == 0
    assert ("carousel", slug) in calls
    assert ("guide", slug) in calls
    reloaded = reg.load_item(slug)
    assert reloaded["steps"]["carousel"] == "review"
    assert reloaded["steps"]["guide"] == "review"


def test_auto_run_stops_step_chain_on_runner_failure(registry_with_item, monkeypatch, capsys):
    reg, slug = registry_with_item

    def fake_register():
        pipeline_cli._RUNNERS.update({
            "ref": lambda s: 0,
            "carousel": lambda s: 1,  # падает
            "guide": lambda s: (_ for _ in ()).throw(AssertionError("guide не должен запускаться после сбоя carousel в этом же цикле")),
            "funnel": lambda s: 0,
            "deliver": lambda s: 0,
        })

    monkeypatch.setattr(pipeline_cli, "_register_runners", fake_register)
    monkeypatch.setattr(pipeline_cli, "optional", lambda key: None)

    code = pipeline_cli.main(["--slug", slug])
    assert code == 0  # сам конвейер не падает, просто останавливает цепочку и печатает статус
    out = capsys.readouterr().out
    assert "ошибкой" in out
