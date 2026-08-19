from pathlib import Path

import pytest

from tools import tg_deliver


def make_files(tmp_path, names):
    paths = []
    for name in names:
        p = tmp_path / name
        p.write_bytes(b"fake")
        paths.append(p)
    return paths


def test_build_media_group_payload_basic(tmp_path):
    paths = make_files(tmp_path, ["a.png", "b.png", "c.png"])
    media, files = tg_deliver.build_media_group_payload(paths)
    try:
        assert len(media) == 3
        assert all(m["type"] == "photo" for m in media)
        assert media[0]["media"] == "attach://photo0"
        assert set(files.keys()) == {"photo0", "photo1", "photo2"}
    finally:
        for f in files.values():
            f.close()


def test_build_media_group_payload_empty_raises():
    with pytest.raises(tg_deliver.TelegramError):
        tg_deliver.build_media_group_payload([])


def test_build_media_group_payload_too_many_raises(tmp_path):
    paths = make_files(tmp_path, [f"p{i}.png" for i in range(11)])
    with pytest.raises(tg_deliver.TelegramError):
        tg_deliver.build_media_group_payload(paths)


def test_deliver_item_sends_album_infographic_video_and_caption(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(tg_deliver, "send_album", lambda token, chat, paths: calls.append(("album", paths)))
    monkeypatch.setattr(tg_deliver, "send_photo", lambda token, chat, path, caption=None: calls.append(("photo", path)))
    monkeypatch.setattr(tg_deliver, "send_video", lambda token, chat, path, caption=None: calls.append(("video", path)))
    monkeypatch.setattr(tg_deliver, "send_message", lambda token, chat, text: calls.append(("message", text)))

    item_dir = tmp_path
    (item_dir / "carousel").mkdir()
    for i in range(1, 9):
        (item_dir / "carousel" / f"slide-{i}.png").write_bytes(b"x")
    (item_dir / "carousel" / "infographic.png").write_bytes(b"x")
    (item_dir / "reel_final.mp4").write_bytes(b"x")

    item = {
        "artifacts": {
            "slides": [f"carousel/slide-{i}.png" for i in range(1, 9)],
            "infographic": "carousel/infographic.png",
            "reel_mp4": "reel_final.mp4",
        },
        "script": {"caption": "Подпись к посту"},
    }

    tg_deliver.deliver_item(item, item_dir, token="t", chat_id="c")

    kinds = [c[0] for c in calls]
    assert kinds == ["album", "photo", "video", "message"]
    assert calls[-1] == ("message", "Подпись к посту")


def test_deliver_item_skips_missing_artifacts(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(tg_deliver, "send_album", lambda *a, **k: calls.append("album"))
    monkeypatch.setattr(tg_deliver, "send_photo", lambda *a, **k: calls.append("photo"))
    monkeypatch.setattr(tg_deliver, "send_video", lambda *a, **k: calls.append("video"))
    monkeypatch.setattr(tg_deliver, "send_message", lambda *a, **k: calls.append("message"))

    item = {"artifacts": {}, "script": {}}
    tg_deliver.deliver_item(item, tmp_path, token="t", chat_id="c")

    assert calls == []
