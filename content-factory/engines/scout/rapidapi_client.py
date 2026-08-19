"""Клиент для real-time-instagram-scraper-api1 на RapidAPI.

Реальный вызов делается только если задан RAPIDAPI_KEY. Без ключа CLI работает
в offline-режиме на локальных fixture-файлах (см. --fixtures в cli.py) —
так S1 можно разрабатывать и тестировать без живой подписки.
"""
from __future__ import annotations

from dataclasses import dataclass

import requests

from engines.common.config import require

BASE_URL = "https://real-time-instagram-scraper-api1.p.rapidapi.com"
HOST = "real-time-instagram-scraper-api1.p.rapidapi.com"
TIMEOUT = 20


class RapidApiError(RuntimeError):
    pass


@dataclass
class InstagramScraperClient:
    api_key: str | None = None

    def __post_init__(self) -> None:
        self.api_key = self.api_key or require("RAPIDAPI_KEY")

    def _headers(self) -> dict[str, str]:
        return {"X-RapidAPI-Key": self.api_key, "X-RapidAPI-Host": HOST}

    def account_posts(self, username: str, limit: int = 12) -> list[dict]:
        """Возвращает сырые посты аккаунта. Формат ответа зависит от тарифа RapidAPI —
        нормализация в наши Post-объекты происходит в cli.py, не здесь."""
        resp = requests.get(
            f"{BASE_URL}/posts",
            headers=self._headers(),
            params={"username": username, "limit": limit},
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            raise RapidApiError(
                f"RapidAPI вернул {resp.status_code} для @{username}: {resp.text[:200]}"
            )
        return resp.json().get("items", [])
