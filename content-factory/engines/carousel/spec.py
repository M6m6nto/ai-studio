"""Спек карусели — чистое преобразование карточки в 8 слайдов + 1 инфографика.

Копирайт (что написано на слайдах) — задача суждения, её делает модель/агент
и кладёт в item["script"] до вызова этого модуля (см. CLAUDE.md: «скилл решает,
движок исполняет»). Отсюда и требование: без заполненного script.body бросаем
понятную ошибку, а не сочиняем текст сами.
"""
from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field

SLIDE_COUNT = 8


class CarouselSpecError(RuntimeError):
    pass


@dataclass
class Slide:
    index: int
    kind: str  # "cover" | "content" | "cta"
    title: str
    body: str = ""


@dataclass
class Infographic:
    title: str
    stats: list[str] = field(default_factory=list)


def _split_body(body: str, n_chunks: int) -> list[str]:
    """Режем текст на n_chunks частей по границам предложений, не по символам."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body.strip()) if s.strip()]
    if not sentences:
        return [""] * n_chunks

    if len(sentences) <= n_chunks:
        chunks = sentences + [""] * (n_chunks - len(sentences))
        return chunks

    per_chunk = len(sentences) / n_chunks
    chunks = []
    for i in range(n_chunks):
        start = round(i * per_chunk)
        end = round((i + 1) * per_chunk)
        chunks.append(" ".join(sentences[start:end]))
    return chunks


def build_spec(item: dict) -> tuple[list[Slide], Infographic]:
    script = item.get("script") or {}
    ref = item.get("ref") or {}
    topic = item.get("topic") or {}

    hooks = script.get("hooks") or []
    body = (script.get("body") or "").strip()
    caption = script.get("caption") or ""
    claims = ref.get("verified_claims") or []
    codeword = item.get("codeword", "")

    if not body:
        raise CarouselSpecError(
            "item.script.body пуст — карусели нечего показывать. "
            "Сначала заполни script (агент пишет копирайт по ref.transcript "
            "и ref.verified_claims), потом запускай /карусель."
        )

    cover_title = hooks[0] if hooks else topic.get("title", "")
    content_slots = SLIDE_COUNT - 2  # минус обложка и CTA
    body_chunks = _split_body(body, content_slots)

    slides: list[Slide] = [Slide(index=1, kind="cover", title=cover_title, body=topic.get("title", ""))]
    for i, chunk in enumerate(body_chunks, start=2):
        slides.append(Slide(index=i, kind="content", title=f"{i - 1}", body=chunk))

    cta_body = caption or f"Напиши слово «{codeword}» в комментарии — пришлю гайд и разбор."
    slides.append(Slide(index=SLIDE_COUNT, kind="cta", title="Забирай разбор", body=cta_body))

    if claims:
        stats = claims[:6]
    else:
        # verified_claims ещё не заполнены (например, /реф не прогоняли) — не тянем один
        # обрезанный огрызок текста, а честно режем body на предложения, что есть.
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if s.strip()]
        stats = [textwrap.shorten(s, width=90, placeholder="…") for s in sentences[:4]] or [
            textwrap.shorten(body, width=90, placeholder="…")
        ]
    infographic = Infographic(title=topic.get("title", ""), stats=stats)

    return slides, infographic
