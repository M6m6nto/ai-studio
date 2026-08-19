import subprocess
from pathlib import Path

import pytest

from engines.ref import design_code, frames

pytestmark = pytest.mark.skipif(
    subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0,
    reason="ffmpeg не установлен",
)


@pytest.fixture(scope="module")
def sample_video(tmp_path_factory) -> Path:
    out_dir = tmp_path_factory.mktemp("ref_fixture")
    video_path = out_dir / "sample.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=320x568:duration=2:rate=10",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
         "-pix_fmt", "yuv420p", str(video_path)],
        capture_output=True, check=True,
    )
    return video_path


def test_extract_frames_produces_pngs(tmp_path, sample_video):
    out_dir = tmp_path / "frames"
    paths = frames.extract_frames(sample_video, out_dir, every_sec=1.0)
    assert len(paths) >= 1
    assert all(p.suffix == ".png" for p in paths)


def test_extract_audio_produces_wav(tmp_path, sample_video):
    out_path = tmp_path / "audio" / "source.wav"
    result = frames.extract_audio(sample_video, out_path)
    assert result.exists()
    assert result.stat().st_size > 0


def test_probe_duration_matches_generated_length(sample_video):
    duration = frames.probe_duration(sample_video)
    assert 1.5 < duration < 2.5


def test_describe_frames_reports_vertical_aspect(tmp_path, sample_video):
    frame_paths = frames.extract_frames(sample_video, tmp_path / "frames", every_sec=0.5)
    description = design_code.describe_frames(frame_paths)
    assert "вертикаль" in description
    assert "#" in description  # есть хотя бы один hex-цвет


def test_describe_frames_empty_input():
    assert "не найдены" in design_code.describe_frames([])
