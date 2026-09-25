import json
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.backend.live_stream_manager import LiveStreamManager
from src.db.models import Base, LiveStream
from src.utils.secret_store import SecretStore


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def secret_store():
    return SecretStore(Fernet.generate_key())


def stream_record(secret_store, visual, audio, **overrides):
    values = {
        "id": "stream-test",
        "title": "Test stream",
        "status": "draft",
        "rtmp_url": "rtmp://localhost/live",
        "stream_key_encrypted": secret_store.encrypt("secret-stream-key"),
        "background_type": "videos",
        "visual_paths_json": json.dumps([str(visual)]),
        "audio_paths_json": json.dumps([str(audio)]),
        "settings_json": json.dumps(
            {
                "audio_mode": "replace",
                "resolution": "1280x720",
                "fps": 30,
                "video_bitrate": 2500,
                "audio_bitrate": 128,
                "visualizer_enabled": True,
                "style": "bars",
                "visualizer_position": "bottom",
                "spectrum_width": 960,
                "spectrum_height": 180,
                "gradient_colors": ["#c7ff2e", "#ff654a"],
            }
        ),
        "loop": True,
        "shuffle": False,
        "auto_restart": True,
        "retry_count": 0,
        "max_retries": 5,
    }
    values.update(overrides)
    return LiveStream(**values)


def test_create_stream_encrypts_key_at_rest(tmp_path, session_factory, secret_store):
    visual = tmp_path / "visual.mp4"
    audio = tmp_path / "audio.mp3"
    visual.write_bytes(b"video")
    audio.write_bytes(b"audio")
    manager = LiveStreamManager(
        session_factory=session_factory,
        secret_store=secret_store,
        ffmpeg_path="ffmpeg",
        media_roots=[tmp_path],
        temp_root=tmp_path / "temp",
    )

    stream = manager.create_stream(
        {
            "id": "encrypted",
            "title": "Encrypted",
            "status": "draft",
            "stream_key": "plain-secret",
            "rtmp_url": "rtmp://localhost/live",
            "background_type": "videos",
            "visual_paths": [str(visual)],
            "audio_paths": [str(audio)],
            "settings": {"audio_mode": "replace"},
        }
    )

    assert stream.stream_key_encrypted != "plain-secret"
    assert "plain-secret" not in stream.stream_key_encrypted
    assert secret_store.decrypt(stream.stream_key_encrypted) == "plain-secret"


def test_command_uses_infinite_input_loop_and_live_visualizer(tmp_path, secret_store):
    visual = tmp_path / "visual.mp4"
    audio = tmp_path / "audio.m4a"
    visual.write_bytes(b"video")
    audio.write_bytes(b"audio")
    manager = LiveStreamManager(
        secret_store=secret_store,
        ffmpeg_path="ffmpeg",
        media_roots=[tmp_path],
        temp_root=tmp_path / "temp",
    )

    command, temp_files = manager.build_command(
        stream_record(secret_store, visual, audio)
    )
    command_text = " ".join(command)

    assert command.count("-stream_loop") == 2
    assert "showfreqs=" in command_text
    assert "[1:a]" in command_text
    assert command[-1] == "rtmp://localhost/live/secret-stream-key"
    assert temp_files[0].read_text(encoding="utf-8").count("file ") == 1
    assert len(temp_files) == 1
    assert str(audio) in command


def test_visualizer_dimensions_are_clamped_to_output_resolution(secret_store):
    manager = LiveStreamManager(secret_store=secret_store, ffmpeg_path="ffmpeg")

    filters, _, _ = manager._build_filters(
        "videos",
        {
            "audio_mode": "replace",
            "resolution": "854x480",
            "visualizer_enabled": True,
            "spectrum_width": 960,
            "spectrum_height": 600,
        },
    )

    assert "showfreqs=s=854x480" in filters


def test_image_playlist_has_durations_and_rejects_keep_audio(tmp_path, secret_store):
    image = tmp_path / "cover.jpg"
    audio = tmp_path / "audio.mp3"
    image.write_bytes(b"image")
    audio.write_bytes(b"audio")
    manager = LiveStreamManager(
        secret_store=secret_store,
        ffmpeg_path="ffmpeg",
        media_roots=[tmp_path],
        temp_root=tmp_path / "temp",
    )
    settings = {
        "audio_mode": "replace",
        "image_duration": 7.5,
        "resolution": "1280x720",
        "visualizer_enabled": False,
    }
    stream = stream_record(
        secret_store,
        image,
        audio,
        background_type="images",
        settings_json=json.dumps(settings),
    )

    _, temp_files = manager.build_command(stream)
    concat = temp_files[0].read_text(encoding="utf-8")
    assert "duration 7.500" in concat
    assert concat.count("file ") == 2

    settings["audio_mode"] = "keep"
    stream.settings_json = json.dumps(settings)
    with pytest.raises(ValueError, match="replacement audio"):
        manager.build_command(stream)


def test_media_outside_configured_roots_is_rejected(tmp_path, secret_store):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    visual = tmp_path / "outside.mp4"
    audio = allowed / "audio.mp3"
    visual.write_bytes(b"video")
    audio.write_bytes(b"audio")
    manager = LiveStreamManager(
        secret_store=secret_store,
        ffmpeg_path="ffmpeg",
        media_roots=[allowed],
        temp_root=tmp_path / "temp",
    )

    with pytest.raises(ValueError, match="outside configured storage roots"):
        manager.build_command(stream_record(secret_store, visual, audio))


def test_preflight_rejects_video_without_required_audio(
    tmp_path, secret_store, monkeypatch
):
    visual = tmp_path / "silent.mp4"
    audio = tmp_path / "music.mp3"
    visual.write_bytes(b"video")
    audio.write_bytes(b"audio")
    manager = LiveStreamManager(
        secret_store=secret_store,
        ffmpeg_path="ffmpeg",
        ffprobe_path="ffprobe",
        media_roots=[tmp_path],
        temp_root=tmp_path / "temp",
    )
    stream = stream_record(secret_store, visual, audio)
    settings = json.loads(stream.settings_json)
    settings["audio_mode"] = "mix"
    stream.settings_json = json.dumps(settings)

    monkeypatch.setattr(
        manager,
        "_probe_stream_types",
        lambda path: {"audio"} if path == audio else {"video"},
    )

    with pytest.raises(ValueError, match="has no audio stream"):
        manager.preflight(stream)


def test_invalid_preflight_does_not_enter_retry_loop(
    tmp_path, session_factory, secret_store, monkeypatch
):
    visual = tmp_path / "visual.mp4"
    audio = tmp_path / "audio.mp3"
    visual.write_bytes(b"video")
    audio.write_bytes(b"audio")
    manager = LiveStreamManager(
        session_factory=session_factory,
        secret_store=secret_store,
        ffmpeg_path="ffmpeg",
        ffprobe_path="ffprobe",
        media_roots=[tmp_path],
        temp_root=tmp_path / "temp",
    )
    manager.create_stream(
        {
            "id": "invalid-preflight",
            "title": "Invalid",
            "status": "starting",
            "stream_key": "secret",
            "rtmp_url": "rtmp://localhost/live",
            "background_type": "videos",
            "visual_paths": [str(visual)],
            "audio_paths": [str(audio)],
            "settings": {"audio_mode": "replace"},
            "auto_restart": True,
            "max_retries": 10,
        }
    )
    monkeypatch.setattr(
        manager, "preflight", lambda stream: (_ for _ in ()).throw(ValueError("bad media"))
    )

    runtime = {"process": None, "cancelled": False, "finished": False}
    manager._runtimes["invalid-preflight"] = runtime
    manager._run("invalid-preflight", runtime)

    with session_factory() as db:
        stored = db.get(LiveStream, "invalid-preflight")
        assert stored.status == "error"
        assert stored.retry_count == 0
        assert stored.error_message == "bad media"
    assert "invalid-preflight" not in manager._retry_timers
