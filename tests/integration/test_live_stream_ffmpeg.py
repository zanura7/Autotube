import json
import shutil
import subprocess
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from src.backend.live_stream_manager import LiveStreamManager
from src.db.models import LiveStream
from src.utils.secret_store import SecretStore


def test_ffmpeg_live_visualizer_smoke(tmp_path):
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("FFmpeg and FFprobe are required for the live visualizer smoke test.")

    video = tmp_path / "background.mp4"
    audio = tmp_path / "music.m4a"
    output = tmp_path / "stream.flv"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x18221b:s=640x360:r=30",
            "-t",
            "1.5",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(video),
        ],
        check=True,
    )
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100",
            "-t",
            "1.5",
            "-c:a",
            "aac",
            str(audio),
        ],
        check=True,
    )

    secrets = SecretStore(Fernet.generate_key())
    stream = LiveStream(
        id="smoke",
        title="Smoke",
        status="draft",
        rtmp_url="rtmp://localhost/live",
        stream_key_encrypted=secrets.encrypt("test-key"),
        background_type="videos",
        visual_paths_json=json.dumps([str(video)]),
        audio_paths_json=json.dumps([str(audio)]),
        settings_json=json.dumps(
            {
                "audio_mode": "replace",
                "resolution": "640x360",
                "fps": 30,
                "video_bitrate": 800,
                "audio_bitrate": 96,
                "visualizer_enabled": True,
                "style": "bars",
                "visualizer_position": "bottom",
                "spectrum_width": 480,
                "spectrum_height": 90,
                "sensitivity": 3,
                "opacity": 0.9,
                "panel_opacity": 0.25,
                "gradient_colors": ["#c7ff2e", "#ff654a"],
            }
        ),
        loop=True,
        shuffle=False,
        auto_restart=False,
        retry_count=0,
        max_retries=0,
    )
    manager = LiveStreamManager(
        secret_store=secrets,
        ffmpeg_path=ffmpeg,
        media_roots=[tmp_path],
        temp_root=tmp_path / "temp",
    )

    manager.preflight(stream)
    command, _ = manager.build_command(stream)
    command[-5:-5] = ["-t", "1.5"]
    command[-1] = str(output)
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0 or "progress=end" in result.stdout, result.stdout + result.stderr
    assert output.stat().st_size > 0

    probe = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,codec_name,width,height",
            "-of",
            "json",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    streams = json.loads(probe.stdout)["streams"]
    assert any(item.get("codec_name") == "h264" and item.get("width") == 640 for item in streams)
    assert any(item.get("codec_name") == "aac" for item in streams)
