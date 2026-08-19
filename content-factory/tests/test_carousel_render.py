import subprocess
from pathlib import Path

import pytest

from engines.carousel.render import webm_to_mp4

pytestmark = pytest.mark.skipif(
    subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0,
    reason="ffmpeg не установлен",
)


@pytest.fixture(scope="module")
def sample_webm(tmp_path_factory) -> Path:
    out_dir = tmp_path_factory.mktemp("cover_fixture")
    webm_path = out_dir / "cover.webm"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=320x400:duration=6:rate=10",
         "-c:v", "libvpx", str(webm_path)],
        capture_output=True, check=True,
    )
    return webm_path


def _duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def test_webm_to_mp4_without_trim_keeps_full_length(tmp_path, sample_webm):
    out = tmp_path / "full.mp4"
    webm_to_mp4(sample_webm, out)
    assert 5.5 < _duration(out) < 6.5


def test_webm_to_mp4_trims_to_last_n_seconds(tmp_path, sample_webm):
    out = tmp_path / "trimmed.mp4"
    webm_to_mp4(sample_webm, out, trim_last_seconds=2.0)
    duration = _duration(out)
    assert 1.5 < duration < 2.5, f"ожидали ~2с (обрезка хвоста записи), получили {duration}"
