"""Чистая логика: по состоянию карточки решает, что можно продвинуть
автоматически (без нового ввода от человека/агента), а что упирается в
точку остановки. Не трогает диск и сеть — поэтому легко тестируется.

Точки остановки — по CLAUDE.md: выбор темы (вне этого модуля, до создания
карточки), приёмка макета карусели, запись видео, приёмка ролика. Плюс шаги,
для которых нужно суждение агента (заполнить script, завести воронку в
ChatPlace, сгенерировать сцены в Higgsfield) — тоже blocked, не auto.
"""
from __future__ import annotations

from dataclasses import dataclass

AUTO = "auto"
BLOCKED = "blocked"
DONE = "done"


@dataclass(frozen=True)
class Action:
    step: str
    kind: str  # AUTO | BLOCKED | DONE
    message: str


def _has_script(item: dict) -> bool:
    return bool((item.get("script") or {}).get("body"))


def plan_ref(item: dict, has_rapidapi_key: bool) -> Action:
    status = item["steps"]["ref"]
    if status == "done" or status == "review":
        return Action("ref", DONE if status == "done" else BLOCKED, (
            "готово" if status == "done" else
            "проверь ref.verified_claims и transcript (агент сверяет по первоисточнику), затем можно двигаться дальше"
        ))
    if status in ("failed",):
        return Action("ref", BLOCKED, "шаг ref упал — разберись руками, потом перезапусти /реф")
    # todo
    if not item["topic"].get("ref_url"):
        return Action("ref", BLOCKED, "нет topic.ref_url — запусти /реф --source-file <локальный файл>")
    if not has_rapidapi_key:
        return Action("ref", BLOCKED, "нет RAPIDAPI_KEY — запусти /реф --source-file <локальный файл> вручную")
    return Action("ref", AUTO, "можно скачать и разобрать референс: /реф")


def plan_carousel(item: dict) -> Action:
    status = item["steps"]["carousel"]
    if status == "done":
        return Action("carousel", DONE, "готово")
    if status == "review":
        return Action("carousel", BLOCKED, "прими макет карусели глазами (carousel/preview/), потом --render")
    if status == "failed":
        return Action("carousel", BLOCKED, "рендер карусели упал — разберись руками")
    if not _has_script(item):
        return Action("carousel", BLOCKED, "заполни item.script.body (агент пишет копирайт по ref), потом карусель")
    return Action("carousel", AUTO, "можно построить превью карусели: /карусель --preview")


def plan_guide(item: dict) -> Action:
    status = item["steps"]["guide"]
    if status == "done":
        return Action("guide", DONE, "готово, страница отдаёт 200")
    if status == "review":
        return Action("guide", BLOCKED, "страница написана локально — задеплой (/гайд --deploy) и подтверди 200")
    if status == "failed":
        return Action("guide", BLOCKED, "деплой/проверка 200 упала — разберись руками")
    if not _has_script(item):
        return Action("guide", BLOCKED, "заполни item.script.body, потом гайд")
    return Action("guide", AUTO, "можно записать страницу гайда локально: /гайд")


def plan_reel(item: dict) -> Action:
    status = item["steps"]["reel"]
    if status == "done":
        return Action("reel", DONE, "готово")
    if status == "failed":
        return Action("reel", BLOCKED, "сборка ролика упала — разберись руками")
    if status == "todo":
        return Action("reel", BLOCKED, "запиши 20–40 сек по суфлёру, потом /рилс --plan --source-file <видео>")
    # review: либо ждём сцены, либо ждём приёмку черновика
    if item.get("artifacts", {}).get("reel_draft_mp4"):
        return Action("reel", BLOCKED, "прими готовый ролик на слух: /рилс --accept")
    return Action("reel", BLOCKED, "сгенерируй сцены в Higgsfield по storyboard.json (диалог с агентом), потом /рилс --compose")


def plan_funnel(item: dict) -> Action:
    status = item["steps"]["funnel"]
    if status == "done":
        return Action("funnel", DONE, "готово")
    if status == "review":
        return Action("funnel", BLOCKED, "заведи воронку в ChatPlace по сценарию (диалог с агентом), потом --set-funnel-id")
    if status == "failed":
        return Action("funnel", BLOCKED, "разберись руками")
    if item["steps"]["guide"] != "done":
        return Action("funnel", BLOCKED, "ждёт guide=done (подтверждённый 200) — это жёсткая очерёдность")
    return Action("funnel", AUTO, "можно построить сценарий воронки: /воронка --plan")


def plan_deliver(item: dict, has_telegram_creds: bool) -> Action:
    status = item["steps"]["deliver"]
    if status == "done":
        return Action("deliver", DONE, "готово")
    if status == "failed":
        return Action("deliver", BLOCKED, "доставка в Telegram упала — разберись руками")
    if item["steps"]["carousel"] != "done" or item["steps"]["reel"] != "done":
        return Action("deliver", BLOCKED, "ждёт carousel=done и reel=done")
    if not has_telegram_creds:
        return Action("deliver", BLOCKED, "нет TELEGRAM_BOT_TOKEN/TG_CHAT_ID в .env")
    return Action("deliver", AUTO, "можно сдать в Telegram: /в-телеграм")


def plan_next_actions(item: dict, has_rapidapi_key: bool, has_telegram_creds: bool) -> list[Action]:
    return [
        plan_ref(item, has_rapidapi_key),
        plan_carousel(item),
        plan_guide(item),
        plan_reel(item),
        plan_funnel(item),
        plan_deliver(item, has_telegram_creds),
    ]
