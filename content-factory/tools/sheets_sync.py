"""Реестр ↔ Google-таблица «[Контент-завод] Poddubotsky», лист продакшна
(колонки: Дата, Источник, Название, Скрипт, Описание, Статус, Исходный скрипт,
Ссылка на исходное видео, Аккаунт, ID поста) — не меняем формат листа, чтобы не
сломать текущий рабочий процесс (см. PLAN.md, S5).

Маппинг item -> строка и обратно — чистые функции, тестируются без сети.
Обращение к самой таблице — через тонкий адаптер SheetsClient; реальная
реализация (Google Sheets API v4 + сервисный аккаунт) импортирует
google-auth/google-api-python-client лениво, только когда её действительно
создают, чтобы модуль был импортируем и без этих (опциональных) зависимостей.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Protocol

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

COLUMNS = [
    "Дата", "Источник", "Название", "Скрипт", "Описание", "Статус",
    "Исходный скрипт", "Ссылка на исходное видео", "Аккаунт", "ID поста",
]

_STATUS_LABELS = {
    "done": "Готово",
    "review": "На проверке",
    "running": "В работе",
    "failed": "Ошибка",
    "blocked": "Заблокировано",
    "todo": "Новый",
}


def _overall_status(item: dict) -> str:
    steps = item.get("steps", {})
    if steps.get("deliver") == "done":
        return _STATUS_LABELS["done"]
    if any(s == "failed" for s in steps.values()):
        return _STATUS_LABELS["failed"]
    if any(s == "running" for s in steps.values()):
        return _STATUS_LABELS["running"]
    if any(s == "review" for s in steps.values()):
        return _STATUS_LABELS["review"]
    return _STATUS_LABELS["todo"]


def item_to_row(item: dict) -> list[str]:
    """Карточка реестра -> строка листа продакшна, в существующем порядке колонок."""
    topic = item.get("topic", {})
    script = item.get("script", {})
    ref = item.get("ref", {})
    date = (item.get("updated_at") or "")[:10]
    return [
        date,
        topic.get("source", ""),
        topic.get("title", ""),
        script.get("body", ""),
        script.get("caption", ""),
        _overall_status(item),
        ref.get("transcript", ""),
        topic.get("ref_url", ""),
        topic.get("ref_account", ""),
        topic.get("ref_post_id", ""),
    ]


def rows_from_registry(items: list[dict]) -> list[list[str]]:
    return [item_to_row(item) for item in items]


class SheetsClient(Protocol):
    def read_rows(self, sheet_range: str) -> list[list[str]]: ...
    def write_rows(self, sheet_range: str, rows: list[list[str]]) -> None: ...


class GoogleSheetsClient:
    """Реальный клиент — Google Sheets API v4, аутентификация сервисным
    аккаунтом (GOOGLE_SA_JSON из .env). Зависимости импортируются здесь, а не
    на уровне модуля, чтобы sheets_sync можно было импортировать (и
    тестировать маппинг) без google-auth/google-api-python-client."""

    def __init__(self, spreadsheet_id: str, service_account_json: str):
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_file(
            service_account_json,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        self._service = build("sheets", "v4", credentials=creds)
        self._spreadsheet_id = spreadsheet_id

    def read_rows(self, sheet_range: str) -> list[list[str]]:
        result = self._service.spreadsheets().values().get(
            spreadsheetId=self._spreadsheet_id, range=sheet_range,
        ).execute()
        return result.get("values", [])

    def write_rows(self, sheet_range: str, rows: list[list[str]]) -> None:
        self._service.spreadsheets().values().update(
            spreadsheetId=self._spreadsheet_id, range=sheet_range,
            valueInputOption="RAW", body={"values": rows},
        ).execute()


def sync_push(client: SheetsClient, items: list[dict], sheet_range: str) -> int:
    """Реестр -> таблица (перезаписывает диапазон целиком строками из реестра,
    заголовок не трогаем — sheet_range должен начинаться со следующей строки
    после Format-заголовка)."""
    rows = rows_from_registry(items)
    client.write_rows(sheet_range, rows)
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    from engines.common.config import optional, require
    from engines.common.registry import Registry

    parser = argparse.ArgumentParser(description="Синхронизация реестра с Google-таблицей (push)")
    parser.add_argument("--range", default="Продакшн!A2:J", help="диапазон листа под данные (без заголовка)")
    args = parser.parse_args(argv)

    spreadsheet_id = require("GOOGLE_SHEET_ID")
    sa_json = optional("GOOGLE_SA_JSON")
    if not sa_json or not Path(sa_json).exists():
        print(f"Не найден сервисный ключ по GOOGLE_SA_JSON={sa_json!r} — см. .env.example")
        return 1

    registry = Registry(ROOT / "registry")
    items = registry.list_items()
    if not items:
        print("В реестре пусто — нечего синхронизировать")
        return 0

    client = GoogleSheetsClient(spreadsheet_id, sa_json)
    n = sync_push(client, items, args.range)
    print(f"Отправлено строк: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
