"""/в-телеграм — приёмка: карусель альбомом, инфографика, ролик, подпись
отдельным сообщением текстом (см. PLAN.md, шаг 7 конвейера).

В отличие от Higgsfield/ChatPlace, Telegram Bot API — открытый, стабильный,
хорошо задокументированный REST-протокол (https://core.telegram.org/bots/api),
поэтому здесь настоящий клиент, а не спека для MCP-инструмента.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import BinaryIO

import requests

from engines.common.config import require

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

API_BASE = "https://api.telegram.org/bot{token}/{method}"
TIMEOUT = 60
MAX_ALBUM_ITEMS = 10  # лимит Telegram на sendMediaGroup


class TelegramError(RuntimeError):
    pass


def _call(token: str, method: str, data: dict | None = None, files: dict | None = None) -> dict:
    url = API_BASE.format(token=token, method=method)
    resp = requests.post(url, data=data, files=files, timeout=TIMEOUT)
    payload = resp.json()
    if not payload.get("ok"):
        raise TelegramError(f"{method} вернул ошибку: {payload.get('description')}")
    return payload["result"]


def build_media_group_payload(photo_paths: list[Path]) -> tuple[list[dict], dict[str, BinaryIO]]:
    """Отдельная от send_album чистая сборка payload — тестируется без сети."""
    if not photo_paths:
        raise TelegramError("Нечего отправлять альбомом — пустой список файлов")
    if len(photo_paths) > MAX_ALBUM_ITEMS:
        raise TelegramError(f"В альбоме максимум {MAX_ALBUM_ITEMS} элементов, передано {len(photo_paths)}")

    media = []
    files: dict[str, BinaryIO] = {}
    for i, path in enumerate(photo_paths):
        attach_name = f"photo{i}"
        media.append({"type": "photo", "media": f"attach://{attach_name}"})
        files[attach_name] = open(path, "rb")  # noqa: SIM115 — закрывается вызывающим после отправки
    return media, files


def send_album(token: str, chat_id: str, photo_paths: list[Path]) -> dict:
    import json

    media, files = build_media_group_payload(photo_paths)
    try:
        return _call(token, "sendMediaGroup", data={"chat_id": chat_id, "media": json.dumps(media)}, files=files)
    finally:
        for f in files.values():
            f.close()


def send_photo(token: str, chat_id: str, photo_path: Path, caption: str | None = None) -> dict:
    with open(photo_path, "rb") as f:
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        return _call(token, "sendPhoto", data=data, files={"photo": f})


def send_video(token: str, chat_id: str, video_path: Path, caption: str | None = None) -> dict:
    with open(video_path, "rb") as f:
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        return _call(token, "sendVideo", data=data, files={"video": f})


def send_message(token: str, chat_id: str, text: str) -> dict:
    return _call(token, "sendMessage", data={"chat_id": chat_id, "text": text})


def deliver_item(item: dict, item_dir: Path, token: str, chat_id: str) -> None:
    artifacts = item.get("artifacts", {})
    slides = artifacts.get("slides") or []
    infographic = artifacts.get("infographic")
    reel_mp4 = artifacts.get("reel_mp4")
    caption = (item.get("script") or {}).get("caption") or ""

    if slides:
        photo_paths = [item_dir / s for s in slides]
        send_album(token, chat_id, photo_paths)
        print(f"Альбом отправлен: {len(photo_paths)} слайд(ов)")

    if infographic:
        send_photo(token, chat_id, item_dir / infographic)
        print("Инфографика отправлена")

    if reel_mp4:
        send_video(token, chat_id, item_dir / reel_mp4)
        print("Ролик отправлен")

    if caption:
        send_message(token, chat_id, caption)
        print("Подпись отправлена отдельным сообщением")


def main(argv: list[str] | None = None) -> int:
    from engines.common.registry import Registry, RegistryError

    parser = argparse.ArgumentParser(description="/в-телеграм — приёмка контента")
    parser.add_argument("--slug", required=True)
    args = parser.parse_args(argv)

    registry = Registry(ROOT / "registry")
    try:
        item = registry.load_item(args.slug)
    except RegistryError as exc:
        print(f"Ошибка: {exc}")
        return 1

    token = require("TELEGRAM_BOT_TOKEN")
    chat_id = require("TG_CHAT_ID")
    item_dir = registry.items_dir / args.slug

    try:
        deliver_item(item, item_dir, token, chat_id)
    except TelegramError as exc:
        registry.set_step(args.slug, "deliver", "failed")
        print(f"Ошибка доставки: {exc}")
        return 1

    registry.set_step(args.slug, "deliver", "done")
    print("Приёмка завершена")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
