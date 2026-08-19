import subprocess
from pathlib import Path

import pytest

from engines.reel import compose

pytestmark = pytest.mark.skipif(
    subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0,
    reason="ffmpeg не установлен",
)


@pytest.fixture(scope="module")
def sample_video(tmp_path_factory) -> Path:
    out_dir = tmp_path_factory.mktemp("compose_fixture")
    video_path = out_dir / "sample.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=320x568:duration=4:rate=10",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
         "-pix_fmt", "yuv420p", str(video_path)],
        capture_output=True, check=True,
    )
    return video_path


def _duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def test_cut_segment_produces_correct_duration(tmp_path, sample_video):
    out = compose.cut_segment(sample_video, 0.5, 2.0, tmp_path / "seg.mp4")
    assert 1.3 < _duration(out) < 1.7


def test_fallback_pipeline_two_segments_concat_and_native_audio(tmp_path, sample_video):
    """Без сгенерированных сцен: оба сегмента — локальный b-roll, склейка +
    родной звук должны отработать без ошибок и дать видео нужной длины."""
    seg1 = compose.cut_segment(sample_video, 0.0, 1.5, tmp_path / "seg1.mp4")
    seg2 = compose.cut_segment(sample_video, 1.5, 3.0, tmp_path / "seg2.mp4")
    assembled = compose.concat_clips([seg1, seg2], tmp_path / "assembled.mp4")
    assert 2.7 < _duration(assembled) < 3.3

    # родной звук — извлечём звуковую дорожку исходника отдельно и наложим поверх
    audio = tmp_path / "audio.aac"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(sample_video), "-vn", "-c:a", "aac", str(audio)],
        capture_output=True, check=True,
    )
    with_audio = compose.mux_native_audio(assembled, audio, tmp_path / "with_audio.mp4")
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type",
         "-of", "csv=p=0", str(with_audio)],
        capture_output=True, text=True, check=True,
    )
    assert "audio" in result.stdout


def test_overlay_badge_keeps_video_dimensions(tmp_path, sample_video):
    from engines.reel.badge import render_badge

    badge_path = render_badge("Test", tmp_path / "badge.png")
    out = compose.overlay_badge(sample_video, badge_path, tmp_path / "with_badge.mp4")
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height",
         "-of", "csv=p=0", str(out)],
        capture_output=True, text=True, check=True,
    )
    assert result.stdout.strip() == "320,568"
