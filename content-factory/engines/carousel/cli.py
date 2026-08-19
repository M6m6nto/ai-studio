"""/карусель — спек → превью (стоп на приёмке) → полный рендер.

Шаг 1, обязательная остановка:
    python -m engines.carousel.cli --slug <slug> --preview

Шаг 2, только после ручной приёмки макета (step carousel=review):
    python -m engines.carousel.cli --slug <slug> --render

--force пропускает проверку review (для повторных прогонов в разработке).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engines.carousel import gen  # noqa: E402
from engines.carousel.render import RenderError, run_screenshot, webm_to_mp4  # noqa: E402
from engines.carousel.spec import CarouselSpecError, build_spec  # noqa: E402
from engines.common.registry import Registry, RegistryError  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="/карусель")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--preview", action="store_true", help="спек + статичное превью, стоп на приёмке")
    parser.add_argument("--render", action="store_true", help="полный рендер: 8 PNG + инфографика + MP4-обложка")
    parser.add_argument("--force", action="store_true", help="пропустить проверку, что макет принят")
    parser.add_argument("--cover-ms", type=int, default=2500, help="длительность анимации обложки")
    args = parser.parse_args(argv)

    if args.preview == args.render:
        print("Укажи ровно один режим: --preview или --render")
        return 1

    registry = Registry(ROOT / "registry")
    try:
        item = registry.load_item(args.slug)
    except RegistryError as exc:
        print(f"Ошибка: {exc}")
        return 1

    try:
        slides, infographic = build_spec(item)
    except CarouselSpecError as exc:
        print(f"Ошибка спека: {exc}")
        return 1

    item_dir = registry.items_dir / args.slug / "carousel"
    html_dir = item_dir / "html"
    png_dir = item_dir / "png"
    video_dir = item_dir / "video"

    if args.preview:
        registry.set_step(args.slug, "carousel", "running")
        manifest = gen.build_manifest(slides, infographic, html_dir, png_dir, video_dir, cover_ms=1)
        # для превью не пишем финальные PNG в png_dir — кладём в отдельную превью-папку,
        # чтобы --render потом не путался с уже принятыми файлами
        preview_dir = item_dir / "preview"
        for s in manifest["slides"]:
            if s.get("out"):
                s["out"] = s["out"].replace(str(png_dir), str(preview_dir))
            if s.get("stillOut"):
                s["stillOut"] = s["stillOut"].replace(str(png_dir), str(preview_dir))
            s["animated"] = False  # в превью обложка тоже статичный кадр — не тратим время на видео
            s.pop("videoDir", None)
            s.pop("videoOut", None)
            s.pop("durationMs", None)
            if "out" not in s:
                s["out"] = s.pop("stillOut")

        manifest_path = item_dir / "preview_manifest.json"
        gen.write_manifest(manifest, manifest_path)
        try:
            run_screenshot(manifest_path)
        except RenderError as exc:
            registry.set_step(args.slug, "carousel", "failed")
            print(f"Рендер превью не удался: {exc}")
            return 1

        registry.set_step(args.slug, "carousel", "review")
        print(f"Макет готов: {preview_dir}")
        print("Прими макет глазами, потом: --render (или --render --force без проверки)")
        return 0

    # --render
    current_status = registry.load_item(args.slug)["steps"]["carousel"]
    if current_status != "review" and not args.force:
        print(f"Шаг carousel сейчас «{current_status}», а не «review». "
              "Сначала --preview и приёмка макета, либо передай --force.")
        return 1

    registry.set_step(args.slug, "carousel", "running")
    manifest = gen.build_manifest(slides, infographic, html_dir, png_dir, video_dir, cover_ms=args.cover_ms)
    manifest_path = item_dir / "render_manifest.json"
    gen.write_manifest(manifest, manifest_path)

    try:
        run_screenshot(manifest_path)
        cover_webm = video_dir / "cover.webm"
        cover_mp4 = item_dir / "cover.mp4"
        webm_to_mp4(cover_webm, cover_mp4, trim_last_seconds=args.cover_ms / 1000)
    except RenderError as exc:
        registry.set_step(args.slug, "carousel", "failed")
        print(f"Рендер не удался: {exc}")
        return 1

    item = registry.load_item(args.slug)
    slide_pngs = [str((png_dir / f"slide-{s.index}.png").relative_to(registry.items_dir / args.slug))
                  for s in slides]
    item["artifacts"]["slides"] = slide_pngs
    item["artifacts"]["infographic"] = str((png_dir / "infographic.png").relative_to(registry.items_dir / args.slug))
    item["artifacts"]["carousel_mp4"] = str(cover_mp4.relative_to(registry.items_dir / args.slug))
    registry.save_item(item)
    registry.set_step(args.slug, "carousel", "done")

    print(f"Готово: {len(slide_pngs)} слайдов + инфографика + анимированная обложка ({cover_mp4})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
