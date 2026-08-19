"""Пословная расшифровка для нарезки по границам слов — отдельно от целостной
расшифровки в /реф (engines.ref.transcript), т.к. здесь нужны таймкоды на
каждое слово (whisper --word_timestamps True --output_format json), а не
только текст.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from engines.common.config import optional


class AsrError(RuntimeError):
    pass


def transcribe_words(audio_path: Path, out_dir: Path) -> Path | None:
    """Возвращает путь к whisper JSON с word-level таймкодами, либо None,
    если ASR недоступен (нет бинарника) — тогда /рилс --plan попросит
    подать таймкоды вручную через --words-json."""
    binary = optional("WHISPER_BIN", "whisper")
    if not binary or shutil.which(binary) is None:
        return None

    out_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [binary, str(audio_path), "--word_timestamps", "True",
         "--output_format", "json", "--output_dir", str(out_dir)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None

    json_path = out_dir / (audio_path.stem + ".json")
    return json_path if json_path.exists() else None
