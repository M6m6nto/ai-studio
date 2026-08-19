"""Публикация страницы гайда: пишем в guides/<slug>/ корневого сайта, при наличии
DEPLOY_SERVER/DEPLOY_DOMAIN гоняем существующий deploy.sh, проверяем 200.

Жёсткое правило конвейера (см. CLAUDE.md): шаг guide становится "done" только
после подтверждённого 200 на реальном URL. Без деплоя (нет ключей) — "review":
страница готова локально, но воронку заводить рано.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import requests

from engines.common.config import optional

SITE_ROOT = Path(__file__).resolve().parents[2].parent  # .../ai-studio (родитель content-factory)


class DeployError(RuntimeError):
    pass


def write_guide_page(slug: str, html: str, infographic_src: Path | None) -> Path:
    guide_dir = SITE_ROOT / "guides" / slug
    guide_dir.mkdir(parents=True, exist_ok=True)
    index_path = guide_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")

    if infographic_src and infographic_src.exists():
        shutil.copy2(infographic_src, guide_dir / "infographic.png")

    return index_path


def deploy_remote() -> bool:
    server = optional("DEPLOY_SERVER")
    domain = optional("DEPLOY_DOMAIN")
    if not server or not domain:
        return False

    result = subprocess.run(
        ["bash", str(SITE_ROOT / "deploy.sh")],
        env={"DOMAIN": domain, "SERVER": server, **_current_env()},
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise DeployError(f"deploy.sh упал: {result.stderr[-1000:]}")
    return True


def _current_env() -> dict[str, str]:
    import os
    return dict(os.environ)


def check_status(url: str, timeout: float = 10.0) -> int | None:
    try:
        resp = requests.head(url, timeout=timeout, allow_redirects=True)
        if resp.status_code == 405:  # некоторые серверы не поддерживают HEAD
            resp = requests.get(url, timeout=timeout)
        return resp.status_code
    except requests.RequestException:
        return None
