"""Сценарий воронки — чистая структура данных, без сети. Создание самой
воронки в ChatPlace — MCP-инструмент в диалоге агента (см. вводные материалы:
"Сервис для воронок из кодовых слов с MCP: ChatPlace"), поэтому здесь нет
REST-клиента к ChatPlace — только спека, которую агент передаёт инструменту.
"""
from __future__ import annotations


class FunnelSpecError(RuntimeError):
    pass


def build_funnel_spec(item: dict, reminder_hours: float = 18.0) -> dict:
    script = item.get("script") or {}
    topic = item.get("topic") or {}
    artifacts = item.get("artifacts") or {}
    codeword = item.get("codeword", "")
    guide_url = artifacts.get("guide_url")

    if not guide_url:
        raise FunnelSpecError(
            "item.artifacts.guide_url пуст — воронка не заводится без живой страницы "
            "гайда (сначала /гайд --deploy, дождись 200)."
        )
    if not codeword:
        raise FunnelSpecError("item.codeword пуст — воронке нечем триггериться")

    caption = script.get("caption") or f"Пришлю разбор по кодовому слову «{codeword}»."

    return {
        "trigger": {"type": "keyword", "value": codeword, "case_sensitive": False},
        "steps": [
            {
                "kind": "welcome",
                "text": f"Привет! Ты написал(а) «{codeword}» — вот обещанный разбор.",
                "button": {"text": "Открыть разбор", "url": guide_url},
            },
            {"kind": "link_card", "title": topic.get("title", ""), "url": guide_url},
            {"kind": "tag", "name": f"clicked:{codeword.lower()}"},
            {"kind": "conversion_event", "name": f"funnel:{item.get('slug', codeword.lower())}"},
            {
                "kind": "reminder",
                "condition": "not_opened",
                "delay_hours": 24,
                "text": "Не потерялось — вот ссылка ещё раз.",
                "button": {"text": "Открыть разбор", "url": guide_url},
            },
            {
                "kind": "offer",
                "condition": "opened",
                "delay_hours": reminder_hours,
                "text": caption,
            },
        ],
        "autoresponder": {
            "trigger_keyword": codeword,
            "reply_template": f"Спасибо! Уже отправил(а) в личные сообщения «{codeword}» — держи 👀",
        },
    }
