"""Загрузка ключей из .env с понятными ошибками при отсутствии."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ConfigError(RuntimeError):
    """Нужного ключа нет в окружении — сообщение объясняет, где его взять."""


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT / ".env", override=False)


_load_dotenv()

_HINTS = {
    "RAPIDAPI_KEY": "rapidapi.com — подписки real-time-instagram-scraper-api1 и "
                    "social-download-all-in-one, см. .env.example",
    "GOOGLE_SA_JSON": "сервисный аккаунт Google Cloud, путь к JSON-ключу",
    "CHATPLACE_TOKEN": "кабинет ChatPlace, раздел API/интеграции",
    "TELEGRAM_BOT_TOKEN": "@BotFather",
}


def require(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        hint = _HINTS.get(key, "см. .env.example")
        raise ConfigError(f"Не задан {key} в .env ({hint})")
    return value


def optional(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)
