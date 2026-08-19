"""/тренды — обходит доноров, ранжирует темы, отсеивает занятые кодовые слова.

Offline-режим (без RAPIDAPI_KEY, для разработки и тестов):
    python -m engines.scout.cli --niche "ии-инструменты" --fixtures tests/fixtures/donor_posts_sample.json

Live-режим (нужен RAPIDAPI_KEY в .env):
    python -m engines.scout.cli --niche "ии-инструменты"

Выбор темы и создание карточки:
    python -m engines.scout.cli --niche "ии-инструменты" --fixtures ... --pick 1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engines.common.registry import Registry  # noqa: E402
from engines.scout.rank import Post, rank_topics  # noqa: E402


def load_donors(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["donors"]


def posts_from_fixture(path: Path) -> list[Post]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    posts = []
    for account, items in raw.items():
        for it in items:
            posts.append(Post(
                post_id=it["post_id"], account=account, title=it["title"], url=it["url"],
                likes=it.get("likes", 0), comments=it.get("comments", 0),
                saves=it.get("saves", 0), views=it.get("views", 0),
                followers=it.get("followers", 0),
            ))
    return posts


def posts_from_rapidapi(donors: list[dict], per_account: int) -> list[Post]:
    from engines.scout.rapidapi_client import InstagramScraperClient

    client = InstagramScraperClient()
    posts = []
    for donor in donors:
        if donor["platform"] != "Instagram" or not donor["account"]:
            continue
        for raw in client.account_posts(donor["account"], limit=per_account):
            posts.append(Post(
                post_id=str(raw.get("id", "")), account=donor["account"],
                title=raw.get("caption", "")[:80], url=raw.get("permalink", ""),
                likes=raw.get("like_count", 0), comments=raw.get("comment_count", 0),
                saves=raw.get("save_count", 0), views=raw.get("play_count", 0),
                followers=donor.get("followers") or 0,
            ))
    return posts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="/тренды — поиск и ранжирование тем")
    parser.add_argument("--niche", required=True, help="ниша (пока — метка карточки, не фильтр доноров)")
    parser.add_argument("--donors-file", default=str(ROOT / "registry" / "donors.json"))
    parser.add_argument("--fixtures", help="offline: json с постами доноров вместо живого RapidAPI")
    parser.add_argument("--per-account", type=int, default=12)
    parser.add_argument("--top", type=int, default=4)
    parser.add_argument("--pick", type=int, help="индекс темы из списка (с 1) — создать карточку в реестре")
    args = parser.parse_args(argv)

    registry = Registry(ROOT / "registry")
    taken = registry.taken_codewords()

    if args.fixtures:
        posts = posts_from_fixture(Path(args.fixtures))
    else:
        donors = load_donors(Path(args.donors_file))
        posts = posts_from_rapidapi(donors, args.per_account)

    candidates = rank_topics(posts, taken, top=args.top)

    if not candidates:
        print("Кандидатов не найдено (либо всё занято по кодовым словам, либо нет постов).")
        return 1

    if args.pick is None:
        print(f"Топ-{len(candidates)} тем по нише «{args.niche}»:\n")
        for i, c in enumerate(candidates, start=1):
            print(f"{i}. [{c['codeword']}] {c['title']}")
            print(f"   ER={c['er']}  viral_ratio={c['viral_ratio']}  views={c['views']}  @{c['account']}")
            print(f"   {c['url']}")
        print("\nВыбери тему: повтори команду с --pick N")
        return 0

    if not (1 <= args.pick <= len(candidates)):
        print(f"--pick должен быть от 1 до {len(candidates)}")
        return 1

    chosen = candidates[args.pick - 1]
    item = registry.new_item(
        title=chosen["title"], source="instagram", codeword=chosen["codeword"], niche=args.niche,
    )
    item["topic"]["ref_post_id"] = chosen["post_id"]
    item["topic"]["ref_url"] = chosen["url"]
    item["topic"]["er"] = chosen["er"]
    item["topic"]["viral_ratio"] = chosen["viral_ratio"]
    registry.save_item(item)
    registry.set_step(item["slug"], "trend", "done")

    print(f"Создана карточка: registry/items/{item['slug']}/item.json")
    print(f"Кодовое слово: {item['codeword']}")
    print(f"Дальше: python -m engines.ref.cli --slug {item['slug']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
