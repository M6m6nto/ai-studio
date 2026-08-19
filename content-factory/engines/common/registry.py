"""Реестр — единственный источник правды о состоянии контент-единиц.

registry/items/<slug>/item.json  — карточка одной единицы контента
registry/index.jsonl             — по строке на единицу (для быстрого листинга)
registry/codewords.json          — занятые кодовые слова (uniqueness)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STEPS = ("trend", "ref", "carousel", "guide", "reel", "funnel", "deliver")
STEP_STATUSES = ("todo", "running", "review", "done", "failed", "blocked")


def slugify(title: str) -> str:
    """Транслитерация не делаем — берём латиницу/цифры, остальное схлопываем в дефис."""
    ascii_only = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower())
    slug = re.sub(r"-{2,}", "-", ascii_only).strip("-")
    return slug or "item"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class RegistryError(RuntimeError):
    pass


class CodewordTakenError(RegistryError):
    def __init__(self, word: str):
        super().__init__(f"Кодовое слово «{word}» уже занято")
        self.word = word


@dataclass
class Registry:
    root: Path

    @property
    def items_dir(self) -> Path:
        return self.root / "items"

    @property
    def index_path(self) -> Path:
        return self.root / "index.jsonl"

    @property
    def codewords_path(self) -> Path:
        return self.root / "codewords.json"

    def __post_init__(self) -> None:
        self.items_dir.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self.index_path.touch()
        if not self.codewords_path.exists():
            self.codewords_path.write_text("{}", encoding="utf-8")

    # -- codewords ---------------------------------------------------

    def _load_codewords(self) -> dict[str, str]:
        return json.loads(self.codewords_path.read_text(encoding="utf-8") or "{}")

    def is_codeword_taken(self, word: str) -> bool:
        return word.strip().upper() in self._load_codewords()

    def taken_codewords(self) -> set[str]:
        return set(self._load_codewords().keys())

    def reserve_codeword(self, word: str, slug: str) -> None:
        word = word.strip().upper()
        codewords = self._load_codewords()
        if word in codewords and codewords[word] != slug:
            raise CodewordTakenError(word)
        codewords[word] = slug
        self.codewords_path.write_text(
            json.dumps(codewords, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # -- items ---------------------------------------------------------

    def item_path(self, slug: str) -> Path:
        return self.items_dir / slug / "item.json"

    def exists(self, slug: str) -> bool:
        return self.item_path(slug).exists()

    def new_item(self, title: str, source: str, codeword: str, niche: str | None = None) -> dict[str, Any]:
        slug = slugify(title)
        base_slug, n = slug, 2
        while self.exists(slug):
            slug = f"{base_slug}-{n}"
            n += 1

        self.reserve_codeword(codeword, slug)

        item: dict[str, Any] = {
            "slug": slug,
            "codeword": codeword.strip().upper(),
            "topic": {"title": title, "source": source, "niche": niche, "picked_at": _now()},
            "ref": {},
            "script": {},
            "artifacts": {},
            "steps": {step: "todo" for step in STEPS},
            "cost": {"higgsfield_credits": 0, "rapidapi_calls": 0},
        }
        self.save_item(item)
        return item

    def load_item(self, slug: str) -> dict[str, Any]:
        path = self.item_path(slug)
        if not path.exists():
            raise RegistryError(f"Карточка «{slug}» не найдена в реестре")
        return json.loads(path.read_text(encoding="utf-8"))

    def save_item(self, item: dict[str, Any]) -> None:
        slug = item["slug"]
        path = self.item_path(slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        item["updated_at"] = _now()
        path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
        self._reindex(item)

    def set_step(self, slug: str, step: str, status: str) -> dict[str, Any]:
        if step not in STEPS:
            raise RegistryError(f"Неизвестный шаг «{step}», ожидались: {STEPS}")
        if status not in STEP_STATUSES:
            raise RegistryError(f"Неизвестный статус «{status}», ожидались: {STEP_STATUSES}")
        item = self.load_item(slug)
        item["steps"][step] = status
        self.save_item(item)
        return item

    def list_items(self) -> list[dict[str, Any]]:
        items = []
        for path in sorted(self.items_dir.glob("*/item.json")):
            items.append(json.loads(path.read_text(encoding="utf-8")))
        return items

    def _reindex(self, item: dict[str, Any]) -> None:
        """Переписывает index.jsonl из содержимого items/ — просто и без гонок при append.

        item.json к этому моменту уже сохранён на диск, поэтому просто перечитываем всё.
        """
        rows = []
        for path in sorted(self.items_dir.glob("*/item.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            rows.append({
                "slug": data["slug"],
                "codeword": data["codeword"],
                "title": data["topic"].get("title"),
                "steps": data["steps"],
                "updated_at": data.get("updated_at"),
            })
        self.index_path.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""),
            encoding="utf-8",
        )
