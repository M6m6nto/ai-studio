"""Учёт расхода на единицу контента — item.cost уже есть в схеме (registry.py),
здесь только запись и агрегация по реестру.
"""
from __future__ import annotations

from engines.common.registry import Registry


def record_cost(registry: Registry, slug: str, key: str, amount: float) -> dict:
    item = registry.load_item(slug)
    cost = item.setdefault("cost", {})
    cost[key] = round(cost.get(key, 0) + amount, 4)
    registry.save_item(item)
    return item


def summarize(registry: Registry) -> dict:
    """Суммарный расход по всем карточкам реестра, по ключам cost и по slug."""
    totals: dict[str, float] = {}
    per_item: dict[str, dict[str, float]] = {}
    for item in registry.list_items():
        slug = item["slug"]
        cost = item.get("cost", {})
        per_item[slug] = cost
        for key, value in cost.items():
            totals[key] = round(totals.get(key, 0) + value, 4)
    return {"totals": totals, "per_item": per_item}
