"""Скачивание исходного поста через social-download-all-in-one (RapidAPI).

В offline/dev-режиме (без ключа или для тестов) используется --source-file —
локальный mp4 вместо похода в сеть, остальной пайплайн /реф работает одинаково.
"""
from __future__ import annotations

from pathlib import Path

import requests

from engines.common.config import require

BASE_URL = "https://social-download-all-in-one.p.rapidapi.com"
HOST = "social-download-all-in-one.p.rapidapi.com"
TIMEOUT = 30


class DownloadError(RuntimeError):
    pass


def resolve_media_url(post_url: str, api_key: str | None = None) -> str:
    api_key = api_key or require("RAPIDAPI_KEY")
    resp = requests.post(
        f"{BASE_URL}/v1/social/autolink",
        headers={"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": HOST},
        json={"url": post_url},
        timeout=TIMEOUT,
    )
    if resp.status_code != 200:
        raise DownloadError(f"social-download-all-in-one вернул {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    medias = data.get("medias") or []
    if not medias:
        raise DownloadError(f"Нет доступных медиа для {post_url}")
    # приоритет — самое высокое качество видео
    medias.sort(key=lambda m: m.get("quality") or "", reverse=True)
    return medias[0]["url"]


def download_to(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=TIMEOUT) as resp:
        if resp.status_code != 200:
            raise DownloadError(f"Не удалось скачать файл: {resp.status_code}")
        with dest.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 16):
                f.write(chunk)
    return dest


def fetch_source(post_url: str, dest: Path, api_key: str | None = None) -> Path:
    media_url = resolve_media_url(post_url, api_key=api_key)
    return download_to(media_url, dest)
