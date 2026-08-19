"""`make smoke` — проверяет окружение до того, как разработчик упрётся в это на полпути."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_BINARIES = ["python3", "ffmpeg"]
OPTIONAL_BINARIES = ["node", "npx"]
REQUIRED_ENV_KEYS = ["RAPIDAPI_KEY"]
OPTIONAL_ENV_KEYS = [
    "GOOGLE_SA_JSON", "CHATPLACE_TOKEN", "TELEGRAM_BOT_TOKEN",
    "DEPLOY_SERVER", "DEPLOY_DOMAIN",
]


def check_binaries() -> list[str]:
    problems = []
    for binary in REQUIRED_BINARIES:
        if shutil.which(binary) is None:
            problems.append(f"нет в PATH: {binary} (обязателен)")
    for binary in OPTIONAL_BINARIES:
        if shutil.which(binary) is None:
            print(f"  ~ нет в PATH: {binary} (нужен со стадии S2, карусель/рендер)")
    return problems


def check_python_deps() -> list[str]:
    problems = []
    for mod in ("requests", "dotenv", "PIL"):
        try:
            __import__(mod)
        except ImportError:
            problems.append(f"python-модуль не установлен: {mod} (pip install -r requirements.txt)")
    return problems


def check_env() -> list[str]:
    from engines.common import config

    problems = []
    env_path = ROOT / ".env"
    if not env_path.exists():
        print(f"  ~ нет {env_path} — скопируй .env.example и заполни ключи")
        return problems
    for key in REQUIRED_ENV_KEYS:
        try:
            config.require(key)
        except config.ConfigError as exc:
            problems.append(str(exc))
    for key in OPTIONAL_ENV_KEYS:
        if not config.optional(key):
            print(f"  ~ не задан {key} (нужен на более позднем этапе)")
    return problems


def check_registry() -> list[str]:
    from engines.common.registry import Registry

    try:
        Registry(ROOT / "registry")
    except Exception as exc:  # noqa: BLE001 — smoke-check должен ловить любую поломку
        return [f"реестр не инициализируется: {exc}"]
    return []


def main() -> int:
    sys.path.insert(0, str(ROOT))
    print("== content-factory smoke ==")
    problems: list[str] = []

    print("-- бинарники --")
    problems += check_binaries()

    print("-- python-зависимости --")
    problems += check_python_deps()

    print("-- .env --")
    problems += check_env()

    print("-- реестр --")
    problems += check_registry()

    if problems:
        print("\nFAIL:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("\nOK — можно запускать /тренды и /реф")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
