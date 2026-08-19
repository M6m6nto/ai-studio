"""/реф — скачивает пост, режет кадры, снимает расшифровку (если доступна),
строит черновой дизайн-код. Проверку утверждений по первоисточнику
(verified_claims) оставляет агенту — это шаг суждения, не автоматики.

Offline/dev (без RAPIDAPI_KEY, локальный файл вместо скачивания):
    python -m engines.ref.cli --slug <slug> --source-file path/to/video.mp4

Live (нужен RAPIDAPI_KEY, берёт ref_url из карточки):
    python -m engines.ref.cli --slug <slug>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engines.common.registry import Registry, RegistryError  # noqa: E402
from engines.ref import design_code, frames, transcript  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="/реф — разбор референса по теме")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--source-file", help="offline: локальный mp4 вместо скачивания по ref_url")
    parser.add_argument("--every-sec", type=float, default=1.0, help="шаг нарезки кадров")
    args = parser.parse_args(argv)

    registry = Registry(ROOT / "registry")
    try:
        item = registry.load_item(args.slug)
    except RegistryError as exc:
        print(f"Ошибка: {exc}")
        return 1

    registry.set_step(args.slug, "ref", "running")
    item_dir = registry.items_dir / args.slug
    raw_dir = item_dir / "raw"
    frames_dir = item_dir / "frames"

    if args.source_file:
        source_path = Path(args.source_file)
        if not source_path.exists():
            print(f"Файл не найден: {source_path}")
            return 1
    else:
        from engines.ref.download import DownloadError, fetch_source

        ref_url = item["topic"].get("ref_url")
        if not ref_url:
            print("В карточке нет topic.ref_url — либо передай --source-file, либо создай тему через /тренды")
            return 1
        try:
            source_path = fetch_source(ref_url, raw_dir / "source.mp4")
        except DownloadError as exc:
            registry.set_step(args.slug, "ref", "failed")
            print(f"Скачивание не удалось: {exc}")
            return 1

    frame_paths = frames.extract_frames(source_path, frames_dir, every_sec=args.every_sec)
    audio_path = frames.extract_audio(source_path, item_dir / "audio" / "source.wav")

    transcript_text = transcript.transcribe(audio_path)
    design = design_code.describe_frames(frame_paths)

    try:
        source_repr = str(source_path.relative_to(item_dir))
    except ValueError:
        source_repr = str(source_path)  # источник вне карточки (например, --source-file снаружи)

    item["ref"] = {
        "source_file": source_repr,
        "frames_count": len(frame_paths),
        "design_code": design,
        "transcript": transcript_text or transcript.PENDING_NOTE,
        "verified_claims": [],
    }
    registry.save_item(item)

    if transcript_text is None:
        registry.set_step(args.slug, "ref", "review")
        print("Кадры и дизайн-код готовы. Расшифровка требует ручного шага — см. transcript.PENDING_NOTE.")
    else:
        registry.set_step(args.slug, "ref", "review")
        print("Кадры, расшифровка и дизайн-код готовы. Шаг ref помечен review — проверь факты по первоисточнику.")

    print(f"Кадров: {len(frame_paths)}  Карточка: registry/items/{args.slug}/item.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
