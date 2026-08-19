"""/воронка — сценарий заводится только после того, как страница гайда
подтверждённо отдала 200 (см. CLAUDE.md: единственная жёсткая очерёдность
во всём конвейере).

Шаг 1 — построить сценарий (сработает только если item.artifacts.guide_url
уже проставлен командой /гайд после успешной проверки 200):
    python -m engines.funnel.cli --slug <slug> --plan

Шаг 2 — агент заводит воронку в ChatPlace через MCP-инструмент в диалоге
(REST-клиента к ChatPlace здесь нет, см. engines/funnel/spec.py) и подтверждает
результат:
    python -m engines.funnel.cli --slug <slug> --set-funnel-id <id из ChatPlace>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engines.common.registry import Registry, RegistryError  # noqa: E402
from engines.funnel.spec import FunnelSpecError, build_funnel_spec  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="/воронка")
    parser.add_argument("--slug", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--set-funnel-id", metavar="ID")
    parser.add_argument("--reminder-hours", type=float, default=18.0)
    args = parser.parse_args(argv)

    registry = Registry(ROOT / "registry")
    try:
        item = registry.load_item(args.slug)
    except RegistryError as exc:
        print(f"Ошибка: {exc}")
        return 1

    if args.plan:
        if item["steps"].get("guide") != "done":
            print(f"Шаг guide сейчас «{item['steps'].get('guide')}», а не «done» — "
                  "воронка заблокирована, пока страница гайда не отдаст 200 (см. /гайд --deploy).")
            return 1
        try:
            scenario = build_funnel_spec(item, reminder_hours=args.reminder_hours)
        except FunnelSpecError as exc:
            print(f"Ошибка: {exc}")
            return 1

        item_dir = registry.items_dir / args.slug
        scenario_path = item_dir / "funnel" / "scenario.json"
        scenario_path.parent.mkdir(parents=True, exist_ok=True)
        import json
        scenario_path.write_text(json.dumps(scenario, ensure_ascii=False, indent=2), encoding="utf-8")

        registry.set_step(args.slug, "funnel", "review")
        print(f"Сценарий готов: {scenario_path}")
        print(f"Триггер: «{scenario['trigger']['value']}». Заведи воронку в ChatPlace (MCP-инструмент "
              "в диалоге агента) по этому сценарию, потом:")
        print(f"  python -m engines.funnel.cli --slug {args.slug} --set-funnel-id <id>")
        return 0

    # --set-funnel-id
    if item["steps"].get("funnel") not in ("review", "running"):
        print(f"Шаг funnel сейчас «{item['steps'].get('funnel')}» — сначала --plan.")
        return 1

    item["artifacts"]["funnel_id"] = args.set_funnel_id
    registry.save_item(item)
    registry.set_step(args.slug, "funnel", "done")
    print(f"Воронка подтверждена: {args.set_funnel_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
