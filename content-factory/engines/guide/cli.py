"""/гайд — пишет страницу разбора в стиле сайта, кладёт в guides/<slug>/, при наличии
DEPLOY_SERVER/DEPLOY_DOMAIN деплоит и проверяет 200. Шаг помечается "done" только
после подтверждённого 200 — это условие старта /воронка (см. CLAUDE.md).

Без ключей деплоя:
    python -m engines.guide.cli --slug <slug>
    → страница пишется локально в guides/<slug>/, шаг = review

С деплоем (нужны DEPLOY_SERVER/DEPLOY_DOMAIN в .env):
    python -m engines.guide.cli --slug <slug> --deploy

Проверка против произвольного URL (например, для теста на локальном http.server):
    python -m engines.guide.cli --slug <slug> --check-url http://127.0.0.1:8000/guides/<slug>/
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engines.common.registry import Registry, RegistryError  # noqa: E402
from engines.guide import deploy, render_html  # noqa: E402
from engines.guide.spec import GuideSpecError, build_guide_content  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="/гайд")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--deploy", action="store_true", help="прогнать deploy.sh (нужны DEPLOY_SERVER/DEPLOY_DOMAIN)")
    parser.add_argument("--check-url", help="проверить 200 по этому URL вместо https://DEPLOY_DOMAIN/guides/<slug>/")
    args = parser.parse_args(argv)

    registry = Registry(ROOT / "registry")
    try:
        item = registry.load_item(args.slug)
    except RegistryError as exc:
        print(f"Ошибка: {exc}")
        return 1

    try:
        content = build_guide_content(item)
    except GuideSpecError as exc:
        print(f"Ошибка: {exc}")
        return 1

    registry.set_step(args.slug, "guide", "running")

    infographic_rel = None
    infographic_src = None
    infographic_arti = item.get("artifacts", {}).get("infographic")
    if infographic_arti:
        infographic_src = registry.items_dir / args.slug / infographic_arti
        infographic_rel = "./infographic.png"

    html = render_html.render_guide(
        title=content["title"], lead=content["lead"], body=content["body"],
        codeword=content["codeword"], source_url=content["source_url"],
        infographic_rel=infographic_rel,
    )
    index_path = deploy.write_guide_page(args.slug, html, infographic_src)
    print(f"Страница записана: {index_path}")

    item["artifacts"]["guide_url"] = None
    registry.save_item(item)

    if args.deploy:
        try:
            deployed = deploy.deploy_remote()
        except deploy.DeployError as exc:
            registry.set_step(args.slug, "guide", "failed")
            print(f"Деплой не удался: {exc}")
            return 1
        if not deployed:
            registry.set_step(args.slug, "guide", "review")
            print("Не заданы DEPLOY_SERVER/DEPLOY_DOMAIN в .env — деплой пропущен, страница только локально.")
            return 0

    check_url = args.check_url
    if not check_url and args.deploy:
        from engines.common.config import optional
        domain = optional("DEPLOY_DOMAIN")
        if domain:
            check_url = f"https://{domain}/guides/{args.slug}/"

    if not check_url:
        registry.set_step(args.slug, "guide", "review")
        print("Страница готова локально. Задеплой (--deploy) и проверь 200, прежде чем запускать /воронка.")
        return 0

    status = deploy.check_status(check_url)
    if status == 200:
        item = registry.load_item(args.slug)
        item["artifacts"]["guide_url"] = check_url
        registry.save_item(item)
        registry.set_step(args.slug, "guide", "done")
        print(f"200 OK: {check_url} — можно запускать /воронка")
        return 0

    registry.set_step(args.slug, "guide", "failed")
    print(f"Страница не отдаёт 200 (получено: {status}) — /воронка заблокирована, пока это не починится.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
