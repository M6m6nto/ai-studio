"""/конвейер — статус по карточке + автопродвижение того, что не требует нового
ввода от человека/агента (ref при наличии ключа, превью карусели, локальная
запись гайда, план воронки, доставка в Telegram при наличии ключей). Всё, что
упирается в точку остановки (CLAUDE.md), не трогает — только печатает, что
делать дальше.

    python -m engines.pipeline.cli --slug <slug>            # продвигает и печатает статус
    python -m engines.pipeline.cli --slug <slug> --dry-run  # только статус, ничего не делает
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engines.common.config import optional  # noqa: E402
from engines.common.registry import Registry, RegistryError  # noqa: E402
from engines.pipeline.advisor import AUTO, BLOCKED, DONE, plan_next_actions  # noqa: E402

_RUNNERS = {}


def _register_runners():
    """Импорт под-движков откладываем до вызова, чтобы --dry-run не требовал
    их зависимостей (например, Pillow для бейджа) при простом статусе."""
    if _RUNNERS:
        return
    from engines.carousel.cli import main as carousel_main
    from engines.funnel.cli import main as funnel_main
    from engines.guide.cli import main as guide_main
    from engines.ref.cli import main as ref_main
    from tools.tg_deliver import main as deliver_main

    _RUNNERS.update({
        "ref": lambda slug: ref_main(["--slug", slug]),
        "carousel": lambda slug: carousel_main(["--slug", slug, "--preview"]),
        "guide": lambda slug: guide_main(["--slug", slug]),
        "funnel": lambda slug: funnel_main(["--slug", slug, "--plan"]),
        "deliver": lambda slug: deliver_main(["--slug", slug]),
    })


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="/конвейер")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--dry-run", action="store_true", help="только статус, не выполнять авто-шаги")
    args = parser.parse_args(argv)

    registry = Registry(ROOT / "registry")
    try:
        item = registry.load_item(args.slug)
    except RegistryError as exc:
        print(f"Ошибка: {exc}")
        return 1

    has_rapidapi_key = bool(optional("RAPIDAPI_KEY"))
    has_telegram_creds = bool(optional("TELEGRAM_BOT_TOKEN")) and bool(optional("TG_CHAT_ID"))

    if not args.dry_run:
        _register_runners()
        # Один проход: выполняем то, что стало auto ПОСЛЕ предыдущего шага в этом
        # же прогоне (например guide=done открывает funnel), поэтому крутим до
        # тех пор, пока список auto-действий не опустеет.
        for _ in range(len(_RUNNERS) + 1):
            item = registry.load_item(args.slug)
            actions = plan_next_actions(item, has_rapidapi_key, has_telegram_creds)
            auto_now = [a for a in actions if a.kind == AUTO]
            if not auto_now:
                break
            for action in auto_now:
                print(f"→ автозапуск: {action.step}")
                runner = _RUNNERS[action.step]
                code = runner(args.slug)
                if code != 0:
                    print(f"  {action.step} завершился с ошибкой (код {code}), останавливаюсь")
                    break

    item = registry.load_item(args.slug)
    actions = plan_next_actions(item, has_rapidapi_key, has_telegram_creds)

    print(f"\nСтатус «{args.slug}» ({item['codeword']} — {item['topic'].get('title', '')}):")
    for a in actions:
        marker = {DONE: "✓", AUTO: "→", BLOCKED: "⏸"}[a.kind]
        print(f"  {marker} {a.step:<9} {a.message}")

    if all(a.kind == DONE for a in actions):
        print("\nГотово целиком — все звенья пройдены.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
