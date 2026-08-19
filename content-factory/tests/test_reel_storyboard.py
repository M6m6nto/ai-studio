import subprocess
from pathlib import Path

import pytest

from engines.reel.storyboard import StoryboardError, build_storyboard, load_storyboard, write_storyboard
from engines.reel.words import Segment, Word

pytestmark = pytest.mark.skipif(
    subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0,
    reason="ffmpeg не установлен",
)


@pytest.fixture(scope="module")
def sample_video(tmp_path_factory) -> Path:
    out_dir = tmp_path_factory.mktemp("storyboard_fixture")
    video_path = out_dir / "sample.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=320x568:duration=3:rate=10",
         "-pix_fmt", "yuv420p", str(video_path)],
        capture_output=True, check=True,
    )
    return video_path


def make_segments() -> list[Segment]:
    words = (Word("раз", 0.0, 0.5), Word("два", 0.5, 1.0))
    return [Segment(index=1, start=0.0, end=1.0, text="раз два", words=words)]


def test_build_storyboard_extracts_frame_per_segment(tmp_path, sample_video):
    manifest = build_storyboard(make_segments(), sample_video, tmp_path / "frames")
    assert len(manifest["segments"]) == 1
    entry = manifest["segments"][0]
    assert Path(entry["reference_frame"]).exists()
    assert entry["scene_clip"] is None
    assert entry["text"] == "раз два"


def test_write_and_load_storyboard_roundtrip(tmp_path, sample_video):
    manifest = build_storyboard(make_segments(), sample_video, tmp_path / "frames")
    path = write_storyboard(manifest, tmp_path / "storyboard.json")
    loaded = load_storyboard(path)
    assert loaded == manifest


def test_load_missing_storyboard_raises(tmp_path):
    with pytest.raises(StoryboardError):
        load_storyboard(tmp_path / "nope.json")
