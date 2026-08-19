"""/рилс — три шага с двумя точками остановки (запись видео человеком и приёмка
готового ролика, см. CLAUDE.md).

Шаг 1 — план. Человек уже записал 20–40 сек по суфлёру (стоп-точка #3):
    python -m engines.reel.cli --slug <slug> --plan --source-file raw.mp4
    (без whisper в PATH нужен готовый JSON: --words-json words.json)
    → сториборд (макс. 3 сегмента / 30с), кадры сегментов, кинетик-субтитры.
    Дальше сцены генерируются агентом через Higgsfield MCP в диалоге —
    не отсюда: у Higgsfield нет REST-ключа, только интерактивный вызов.

Шаг 2 — сборка (после того как агент принёс сгенерированные клипы):
    python -m engines.reel.cli --slug <slug> --compose \
        --scene 1=scene1.mp4 --scene 2=scene2.mp4
    (сегменты без --scene идут локальным b-roll из исходника)
    → draft.mp4: замена фона, кинетик-титры, бейдж, родной звук.

Шаг 3 — приёмка (стоп-точка #4, сверка звука со скриптом):
    python -m engines.reel.cli --slug <slug> --accept
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engines.common.registry import Registry, RegistryError  # noqa: E402
from engines.reel import asr, badge, compose, qa, storyboard, subtitles  # noqa: E402
from engines.reel.compose import ComposeError  # noqa: E402
from engines.reel.storyboard import StoryboardError  # noqa: E402
from engines.reel.words import WordsError, load_whisper_words, plan_segments  # noqa: E402


def cmd_plan(args, registry: Registry, item_dir: Path) -> int:
    from engines.ref.frames import extract_audio

    source = Path(args.source_file)
    if not source.exists():
        print(f"Файл не найден: {source}")
        return 1

    reel_dir = item_dir / "reel"
    audio_path = reel_dir / "source_audio.wav"
    extract_audio(source, audio_path)

    if args.words_json:
        words_json = Path(args.words_json)
    else:
        words_json = asr.transcribe_words(audio_path, reel_dir / "asr")
        if words_json is None:
            print("Нет whisper в PATH и не передан --words-json — нечем размечать слова по времени.")
            print("Либо поставь WHISPER_BIN, либо подготовь JSON вручную и передай --words-json.")
            return 1

    try:
        words = load_whisper_words(words_json)
        segments = plan_segments(words, max_segments=args.max_segments, max_total_seconds=args.max_seconds)
    except WordsError as exc:
        print(f"Ошибка сегментации: {exc}")
        return 1

    manifest = storyboard.build_storyboard(segments, source, reel_dir / "frames")
    storyboard.write_storyboard(manifest, reel_dir / "storyboard.json")
    subtitles.write_ass(segments, reel_dir / "kinetic.ass")

    item = registry.load_item(args.slug)
    item["reel"] = {
        "source_file": str(source),
        "segments": [
            {"index": s.index, "start": s.start, "end": s.end, "text": s.text} for s in segments
        ],
    }
    registry.save_item(item)
    registry.set_step(args.slug, "reel", "review")

    print(f"Сториборд готов: {len(segments)} сегмент(ов), {reel_dir / 'storyboard.json'}")
    print("Дальше: сгенерируй сцены под каждый segment.reference_frame через Higgsfield "
          "(агент делает это в диалоге), потом:")
    print(f"  python -m engines.reel.cli --slug {args.slug} --compose --scene 1=<путь> ...")
    return 0


def cmd_compose(args, registry: Registry, item_dir: Path) -> int:
    reel_dir = item_dir / "reel"
    try:
        manifest = storyboard.load_storyboard(reel_dir / "storyboard.json")
    except StoryboardError as exc:
        print(f"Ошибка: {exc}")
        return 1

    item = registry.load_item(args.slug)
    source = Path(item["reel"]["source_file"])
    scene_overrides = dict(pair.split("=", 1) for pair in args.scene or [])

    clips_dir = reel_dir / "clips"
    clips: list[Path] = []
    for seg in manifest["segments"]:
        idx = seg["index"]
        duration = seg["duration"]
        out_path = clips_dir / f"segment-{idx}.mp4"
        if str(idx) in scene_overrides:
            compose.normalize_clip(Path(scene_overrides[str(idx)]), duration, out_path)
        else:
            compose.cut_segment(source, seg["start"], seg["end"], out_path)
        clips.append(out_path)

    try:
        assembled = compose.concat_clips(clips, reel_dir / "assembled.mp4")
        with_audio = compose.mux_native_audio(assembled, reel_dir / "source_audio.wav", reel_dir / "with_audio.mp4")
        with_subs = compose.burn_subtitles(with_audio, reel_dir / "kinetic.ass", reel_dir / "with_subs.mp4")
        badge_path = badge.render_badge(args.badge_text, reel_dir / "badge.png")
        draft = compose.overlay_badge(with_subs, badge_path, item_dir / "reel_draft.mp4")
    except ComposeError as exc:
        registry.set_step(args.slug, "reel", "failed")
        print(f"Сборка не удалась: {exc}")
        return 1

    item = registry.load_item(args.slug)
    item["artifacts"]["reel_draft_mp4"] = str(draft.relative_to(item_dir))
    registry.save_item(item)
    registry.set_step(args.slug, "reel", "review")

    used_scenes = len(scene_overrides)
    total = len(manifest["segments"])
    print(f"Черновик готов: {draft} ({used_scenes}/{total} сегментов из сгенерированных сцен, "
          f"{total - used_scenes} — локальный b-roll)")
    print(f"Прими ролик глазами и звуком, потом: --accept")
    return 0


def cmd_accept(args, registry: Registry, item_dir: Path) -> int:
    item = registry.load_item(args.slug)
    draft_rel = item.get("artifacts", {}).get("reel_draft_mp4")
    if not draft_rel:
        print("Нет черновика — сначала --compose")
        return 1

    draft_path = item_dir / draft_rel
    expected_text = " ".join(s["text"] for s in item["reel"]["segments"])
    actual_text = qa.resync_transcript(draft_path, item_dir / "reel" / "qa")

    if actual_text is None:
        print("ASR недоступен — сверить звук со скриптом автоматически не получилось.")
        print("Прими ролик на слух вручную, затем можно принудительно завершить: --accept --force")
        if not args.force:
            return 1
        score = None
    else:
        score = qa.similarity(expected_text, actual_text)
        print(f"Сходство расшифровки со скриптом: {score:.0%}")
        if score < args.min_similarity and not args.force:
            registry.set_step(args.slug, "reel", "review")
            print(f"Ниже порога ({args.min_similarity:.0%}) — звук разошёлся со скриптом, ролик не принят.")
            print("Проверь клипы вручную или пересобери с другими сценами; либо --accept --force.")
            return 1

    final_path = item_dir / "reel_final.mp4"
    draft_path.replace(final_path)
    item = registry.load_item(args.slug)
    item["artifacts"]["reel_mp4"] = str(final_path.relative_to(item_dir))
    item["artifacts"].pop("reel_draft_mp4", None)
    if score is not None:
        item["reel"]["qa_similarity"] = round(score, 3)
    registry.save_item(item)
    registry.set_step(args.slug, "reel", "done")

    print(f"Ролик принят: {final_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="/рилс — автомонтаж ролика")
    parser.add_argument("--slug", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--compose", action="store_true")
    mode.add_argument("--accept", action="store_true")

    parser.add_argument("--source-file", help="[--plan] живое видео/аватар, записанное человеком")
    parser.add_argument("--words-json", help="[--plan] whisper JSON с word-таймкодами, если нет ASR в PATH")
    parser.add_argument("--max-segments", type=int, default=3)
    parser.add_argument("--max-seconds", type=float, default=30.0)

    parser.add_argument("--scene", action="append", help="[--compose] N=путь_к_клипу, можно несколько раз")
    parser.add_argument("--badge-text", default="Poddubotsky AI")

    parser.add_argument("--force", action="store_true", help="[--accept] принять несмотря на провал QA")
    parser.add_argument("--min-similarity", type=float, default=0.6)

    args = parser.parse_args(argv)

    registry = Registry(ROOT / "registry")
    try:
        registry.load_item(args.slug)
    except RegistryError as exc:
        print(f"Ошибка: {exc}")
        return 1

    item_dir = registry.items_dir / args.slug

    if args.plan:
        if not args.source_file:
            print("--plan требует --source-file")
            return 1
        registry.set_step(args.slug, "reel", "running")
        return cmd_plan(args, registry, item_dir)
    if args.compose:
        registry.set_step(args.slug, "reel", "running")
        return cmd_compose(args, registry, item_dir)
    return cmd_accept(args, registry, item_dir)


if __name__ == "__main__":
    raise SystemExit(main())
