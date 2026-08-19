"""Python-обёртка над screenshot.cjs (Playwright) и ffmpeg-конвертацией видео."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

SCRIPT_PATH = Path(__file__).with_name("screenshot.cjs")
CONTENT_FACTORY_ROOT = Path(__file__).resolve().parents[2]
# Резервный путь к глобальному playwright — актуален только в этой sandbox-среде,
# где playwright установлен глобально, а не через package.json этого проекта.
FALLBACK_GLOBAL_NODE_MODULES = "/opt/node22/lib/node_modules"


class RenderError(RuntimeError):
    pass


def _node_path() -> str:
    """Предпочитаем локальный node_modules (npm install в content-factory/),
    как в реальном деплое; иначе — глобальный playwright, если он есть (эта sandbox)."""
    local = CONTENT_FACTORY_ROOT / "node_modules"
    parts = [str(local)] if local.exists() else []
    if Path(FALLBACK_GLOBAL_NODE_MODULES).exists():
        parts.append(FALLBACK_GLOBAL_NODE_MODULES)
    existing = os.environ.get("NODE_PATH")
    if existing:
        parts.append(existing)
    return ":".join(parts)


def run_screenshot(manifest_path: Path) -> str:
    env = dict(os.environ)
    env["NODE_PATH"] = _node_path()
    result = subprocess.run(
        ["node", str(SCRIPT_PATH), str(manifest_path)],
        capture_output=True, text=True, env=env,
    )
    if result.returncode != 0:
        raise RenderError(f"screenshot.cjs упал: {result.stderr[-1000:]}")
    return result.stdout


def webm_to_mp4(webm_path: Path, mp4_path: Path, trim_last_seconds: float | None = None) -> Path:
    """Конвертирует webm в mp4. Playwright пишет видео с момента создания контекста,
    поэтому в начале записи может оказаться холодный старт страницы (загрузка шрифтов
    по сети и т.п.) — это не часть задуманной анимации. trim_last_seconds обрезает
    ролик по факту, оставляя последние N секунд, а не полагается на точный тайминг записи.
    """
    mp4_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y"]
    if trim_last_seconds:
        cmd += ["-sseof", f"-{trim_last_seconds}"]
    cmd += ["-i", str(webm_path), "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(mp4_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RenderError(f"ffmpeg не смог сконвертировать {webm_path}: {result.stderr[-500:]}")
    return mp4_path
