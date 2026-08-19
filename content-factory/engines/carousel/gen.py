"""Спек → набор HTML-файлов + манифест для screenshot.mjs."""
from __future__ import annotations

import json
from pathlib import Path

from engines.carousel import render_html
from engines.carousel.spec import Infographic, Slide


def write_slide_html(slide: Slide, out_dir: Path, total: int, animated_cover: bool) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    page_label = f"{slide.index}/{total}"
    if slide.kind == "cover":
        html = render_html.render_cover(slide.title, slide.body, page_label, animated=animated_cover)
    elif slide.kind == "cta":
        html = render_html.render_cta(slide.title, slide.body, page_label)
    else:
        html = render_html.render_content(slide.title, slide.body, page_label)

    path = out_dir / f"slide-{slide.index}.html"
    path.write_text(html, encoding="utf-8")
    return path


def write_infographic_html(infographic: Infographic, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    html = render_html.render_infographic(infographic.title, infographic.stats)
    path = out_dir / "infographic.html"
    path.write_text(html, encoding="utf-8")
    return path


def build_manifest(slides: list[Slide], infographic: Infographic, html_dir: Path, png_dir: Path,
                    video_dir: Path, cover_ms: int = 2500) -> dict:
    total = len(slides)
    manifest_slides = []

    for slide in slides:
        html_path = write_slide_html(slide, html_dir, total, animated_cover=(slide.kind == "cover"))
        entry = {
            "html": str(html_path.resolve()),
            "width": render_html.W,
            "height": render_html.H,
            "kind": slide.kind,
        }
        if slide.kind == "cover":
            entry["animated"] = True
            entry["durationMs"] = cover_ms
            entry["videoDir"] = str(video_dir.resolve())
            entry["videoOut"] = str((video_dir / "cover.webm").resolve())
            # у анимированной обложки всё равно нужен статичный кадр-превью для ленты слайдов
            entry["stillOut"] = str((png_dir / f"slide-{slide.index}.png").resolve())
        else:
            entry["animated"] = False
            entry["out"] = str((png_dir / f"slide-{slide.index}.png").resolve())
        manifest_slides.append(entry)

    info_path = write_infographic_html(infographic, html_dir)
    manifest_slides.append({
        "html": str(info_path.resolve()),
        "width": render_html.W,
        "height": render_html.H,
        "kind": "infographic",
        "animated": False,
        "out": str((png_dir / "infographic.png").resolve()),
    })

    return {"slides": manifest_slides}


def write_manifest(manifest: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
