"""Расшифровка звука исходника.

ASR-сервис не зафиксирован практикумом — движок не привязывается к конкретному
провайдеру. Если в PATH есть whisper-совместимый бинарник (WHISPER_BIN, по
умолчанию `whisper`), используем его. Иначе честно возвращаем None и оставляем
явный TODO в карточке — расшифровку тогда правит человек/агент в диалоге,
а не выдумывает скрипт.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from engines.common.config import optional

PENDING_NOTE = (
    "Автоматическая расшифровка недоступна (нет WHISPER_BIN в PATH). "
    "Вставь расшифровку вручную в item.json -> ref.transcript и отметь шаг ref=review."
)


def transcribe(audio_path: Path) -> str | None:
    binary = optional("WHISPER_BIN", "whisper")
    if not binary or shutil.which(binary) is None:
        return None

    result = subprocess.run(
        [binary, str(audio_path), "--output_format", "txt", "--output_dir", str(audio_path.parent)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None

    txt_path = audio_path.with_suffix(".txt")
    if not txt_path.exists():
        return None
    return txt_path.read_text(encoding="utf-8").strip()
