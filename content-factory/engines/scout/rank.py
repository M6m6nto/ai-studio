"""Чистые функции ранжирования тем — без сети, без модели, легко тестируются.

Формула ER и порог свежести — из PLAN.md (раздел S1):
    ER = (likes + 3*comments + 5*saves) / views
viral_ratio — во сколько раз пост облетел подписчиков аккаунта-донора.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

STOPWORDS = {
    "как", "что", "это", "для", "или", "про", "если", "чтобы", "уже", "все",
    "the", "and", "for", "with", "your", "this", "how", "why",
}


@dataclass(frozen=True)
class Post:
    post_id: str
    account: str
    title: str
    url: str
    likes: int = 0
    comments: int = 0
    saves: int = 0
    views: int = 0
    followers: int = 0


def engagement_rate(post: Post) -> float:
    if post.views <= 0:
        return 0.0
    return (post.likes + 3 * post.comments + 5 * post.saves) / post.views


def viral_ratio(post: Post) -> float:
    if post.followers <= 0:
        return 0.0
    return post.views / post.followers


def suggest_codeword(title: str) -> str:
    """Первое значимое слово темы в верхнем регистре — черновой кандидат.

    Финальное слово всё равно подтверждает человек на шаге /тренды, это только
    чтобы у кандидата было чем зарезервировать место в реестре.
    """
    words = re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", title)
    for word in words:
        if len(word) >= 3 and word.lower() not in STOPWORDS:
            return word.upper()
    return (words[0].upper() if words else "TEMA")


def rank_topics(posts: list[Post], taken_codewords: set[str], top: int = 4) -> list[dict]:
    """Сортирует по ER, отсеивает темы с уже занятым кодовым словом, берёт top-N."""
    taken = {w.strip().upper() for w in taken_codewords}
    candidates = []
    for post in posts:
        codeword = suggest_codeword(post.title)
        if codeword in taken:
            continue
        candidates.append({
            "post_id": post.post_id,
            "account": post.account,
            "title": post.title,
            "url": post.url,
            "codeword": codeword,
            "er": round(engagement_rate(post), 4),
            "viral_ratio": round(viral_ratio(post), 2),
            "views": post.views,
        })
    candidates.sort(key=lambda c: c["er"], reverse=True)
    return candidates[:top]
