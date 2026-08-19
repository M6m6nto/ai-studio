"""Собирает данные для шаблона гайда из карточки — без сети и рендера, легко тестировать."""
from __future__ import annotations

import textwrap


class GuideSpecError(RuntimeError):
    pass


def build_guide_content(item: dict) -> dict:
    script = item.get("script") or {}
    ref = item.get("ref") or {}
    topic = item.get("topic") or {}

    body = (script.get("body") or "").strip()
    if not body:
        raise GuideSpecError(
            "item.script.body пуст — гайду нечего рассказывать. Заполни script перед /гайд."
        )

    title = topic.get("title", "")
    lead = textwrap.shorten(body, width=160, placeholder="…")

    return {
        "title": title,
        "lead": lead,
        "body": body,
        "codeword": item.get("codeword", ""),
        "source_url": topic.get("ref_url"),
    }
