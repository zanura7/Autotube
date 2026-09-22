"""Regression coverage for generator routes and real FFmpeg renders."""
import io
import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from src.api.routes import generator as routes
from src.db.database import Base
from src.db.models import Project
from src.backend.audio_visualizer import AudioVisualizer
from src.backend.video_generator import VideoGenerator


@pytest.fixture
def media(tmp_path):
    image = tmp_path / "background.png"
    Image.new("RGB", (320, 180), (30, 80, 110)).save(image)
    audio = tmp_path / "audio.wav"
    import math
    import struct
    with wave.open(str(audio), "wb") as f:
        f.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        f.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / 16000)))
                               for i in range(16000)))
    return image, audio


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_engine("sqlite:///" + str(tmp_path / "test.db"),
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    monkeypatch.setattr(routes, "SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(routes, "GENERATIONS", tmp_path / "generations")
    monkeypatch.setattr(routes, "UPLOADS", tmp_path / "uploads")
    app = FastAPI()
    app.include_router(routes.router)
    with TestClient(app) as client:
        yield client
    engine.dispose()


def request_for(media, **kwargs):
    image, audio = media
    return dict(mode="simple", output_name="result.mp4", bg_path=str(image),
                audio_path=str(audio), **kwargs)


@pytest.mark.parametrize("field,value", [
    ("mode", "unknown"), ("output_name", "../outside.mp4"),
    ("output_name", "CON.mp4"), ("audio_path", None),
    ("bg_path", "missing.png"), ("output_name", "video.avi"),
])
def test_invalid_requests_do_not_queue(client, media, field, value):
    payload = request_for(media)
    payload[field] = value
    assert client.post("/generator/start", json=payload).status_code == 422
    with routes.SessionLocal() as db:
        assert db.query(Project).count() == 0


def test_visualizer_rejects_video_in_image_list(client, media):
    image, audio = media
    video = image.with_suffix(".mp4")
    video.write_bytes(b"invalid video")
    payload = request_for(media)
    payload.update(mode="visualizer", background_type="images", image_files=[str(video)])
    assert client.post("/generator/start", json=payload).status_code == 422


def test_visualizer_image_background_rejects_mix_mode(client, media):
    payload = request_for(media)
    payload.update(mode="visualizer", background_type="images",
                   image_files=[str(media[0])], audio_mode="mix")
    assert client.post("/generator/start", json=payload).status_code == 422


def test_upload_names_cannot_escape_or_overwrite(client):
    first = client.post("/generator/upload", files={"file": ("../same.wav", b"first", "audio/wav")})
    second = client.post("/generator/upload", files={"file": ("../same.wav", b"second", "audio/wav")})
    assert first.status_code == second.status_code == 200
    a, b = Path(first.json()["path"]), Path(second.json()["path"])
    assert a != b and a.parent == routes.UPLOADS.resolve()
    assert a.read_bytes() == b"first" and b.read_bytes() == b"second"
    assert client.post("/generator/upload", files={"file": ("empty.wav", b"", "audio/wav")}).status_code == 422


@pytest.mark.parametrize("mode", ["simple", "visualizer", "mixer", "loop"])
def test_output_is_recorded_and_downloadable(client, media, mode):
    payload = request_for(media)
    payload["mode"] = mode
    if mode == "mixer":
        payload.update(image_folder=str(media[0].parent), audio_files=[str(media[1])])
    if mode == "loop":
        video = media[0].with_suffix(".mp4")
        video.write_bytes(b"source")
        payload["bg_path"] = str(video)
    targets = {
        "simple": "src.backend.video_generator.VideoGenerator.generate_video",
        "visualizer": "src.backend.audio_visualizer.AudioVisualizer.render_composition",
        "mixer": "src.backend.advanced_image_mixer.AdvancedImageMixer.generate_video",
        "loop": "src.backend.loop_creator.LoopCreator.create_loop",
    }
    def render(renderer, **kwargs):
        output = (Path(kwargs["output_path"]) if mode == "visualizer" else
                  Path(kwargs["output_file"]) if mode == "mixer" else
                  renderer.output_folder / kwargs["output_filename"])
        output.write_bytes(b"rendered video")
        return True
    with patch(targets[mode], autospec=True, side_effect=render):
        responses = [client.post("/generator/start", json=payload).json() for _ in range(2)]
    assert responses[0]["output"] != responses[1]["output"]
    for data in responses:
        status = client.get(f"/generator/{data['project_id']}").json()
        assert status["status"] == "Completed"
        assert Path(status["file_path"]).is_relative_to(routes.GENERATIONS.resolve())
        assert client.get(f"/generator/{data['project_id']}/download").content == b"rendered video"


def test_renderer_exception_marks_failed(client, media):
    with patch.object(VideoGenerator, "generate_video", side_effect=RuntimeError("render broke")):
        data = client.post("/generator/start", json=request_for(media)).json()
    assert client.get(f"/generator/{data['project_id']}").json()["status"] == "Failed"
    assert client.get(f"/generator/{data['project_id']}/download").status_code == 404


def probe_output(output, expected_duration=1.0):
    assert output.is_file() and output.stat().st_size > 0
    result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                             "-of", "json", str(output)], capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    assert {s["codec_type"] for s in data["streams"]} == {"audio", "video"}
    video = next(s for s in data["streams"] if s["codec_type"] == "video")
    assert (video["width"], video["height"], video["pix_fmt"]) == (320, 180, "yuv420p")
    assert expected_duration - 0.15 <= float(data["format"]["duration"]) <= expected_duration + 0.2


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
@pytest.mark.parametrize("style", ["Classic Bar", "Rounded Bar", "Mirror Bar", "Fire", "Smooth Wave"])
def test_visualizer_real_render(tmp_path, media, style):
    output = tmp_path / "visualizer.mp4"
    result = AudioVisualizer(tmp_path).render(*media, output_path=output,
                                             resolution="320x180", style=style)
    assert result == output
    probe_output(output)


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
def test_visualizer_with_rotated_pulsing_logo(tmp_path, media):
    output = tmp_path / "logo.mp4"
    result = AudioVisualizer(tmp_path).render(*media, output_path=output,
        resolution="320x180", logo_path=media[0], logo_size=64, logo_rotation=45, logo_pulse=True)
    assert result == output
    probe_output(output)


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
@pytest.mark.parametrize(("transition", "transition_duration"), [
    ("none", 0.0), ("fade", 0.2), ("crossfade", 0.2),
])
def test_visualizer_slideshow_composition(tmp_path, media, transition, transition_duration):
    second = tmp_path / "second.png"
    Image.new("RGB", (280, 200), (160, 45, 80)).save(second)
    output = tmp_path / f"slideshow_{transition}.mp4"
    result = AudioVisualizer(tmp_path).render_composition(
        output_path=output,
        background_type="images",
        image_paths=[str(media[0]), str(second)],
        audio_path=str(media[1]),
        image_duration=0.6,
        transition_type=transition,
        transition_duration=transition_duration,
        resolution="320x180",
        spectrum_width=260,
        spectrum_height=60,
    )
    assert result == output
    probe_output(output)
    assert not list(tmp_path.glob("*.slideshow.mp4"))


def create_source_video(path, duration=0.55):
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x183153:s=320x180:r=25:d={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=220:sample_rate=16000:duration={duration}",
        "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(path),
    ], capture_output=True, check=True)


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
@pytest.mark.parametrize(("audio_mode", "shorter_mode", "expected_duration"), [
    ("replace", "loop", 1.0),
    ("replace", "freeze", 1.0),
    ("mix", "loop", 1.0),
    ("keep", "loop", 0.55),
])
def test_visualizer_video_audio_modes(tmp_path, media, audio_mode, shorter_mode, expected_duration):
    source = tmp_path / "source.mp4"
    create_source_video(source)
    output = tmp_path / f"{audio_mode}_{shorter_mode}.mp4"
    result = AudioVisualizer(tmp_path).render_composition(
        output_path=output,
        background_type="video",
        video_path=str(source),
        audio_path=str(media[1]),
        audio_mode=audio_mode,
        video_shorter_mode=shorter_mode,
        resolution="320x180",
        spectrum_width=260,
        spectrum_height=60,
    )
    assert result == output
    probe_output(output, expected_duration)


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
@pytest.mark.parametrize("effect", ["zoom", "pan", "fade", "none"])
def test_generator_real_render(tmp_path, media, effect):
    image, audio = media
    output = tmp_path / "video.mp4"
    assert VideoGenerator(tmp_path).render_video(audio, image, output, 1, "320x180",
                                                 is_image=True, image_effect=effect)
    probe_output(output)

@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
@pytest.mark.parametrize("image_count", [1, 2, 3])
def test_mixer_full_render_with_wav(tmp_path, media, image_count):
    from src.backend.advanced_image_mixer import AdvancedImageMixer
    for i in range(1, image_count):
        Image.new("RGB", (240 + i * 10, 160), (i * 50, 30, 140)).save(tmp_path / f"image{i}.png")
    output = tmp_path / "mixer.mp4"
    assert AdvancedImageMixer(tmp_path).generate_video(
        str(tmp_path), [str(media[1])], str(output), resolution="320x180")
    probe_output(output)


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
def test_simple_full_pipeline(tmp_path, media):
    assert VideoGenerator(tmp_path).generate_video(
        audio_folder=str(media[1]), visual_path=str(media[0]),
        resolution="320x180", output_filename="full.mp4")
    probe_output(tmp_path / "full.mp4")
    assert (tmp_path / "full.chapters.txt").is_file()


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
def test_mixer_chunked_pipeline(tmp_path, media, monkeypatch):
    import src.backend.advanced_image_mixer as mixer_module
    monkeypatch.setattr(mixer_module, "IMAGES_PER_CHUNK", 2)
    for i in range(1, 3):
        Image.new("RGB", (320, 180), (i * 50, 30, 140)).save(tmp_path / f"image{i}.png")
    output = tmp_path / "chunked.mp4"
    assert mixer_module.AdvancedImageMixer(tmp_path).generate_video(
        str(tmp_path), [str(media[1])], str(output), resolution="320x180")
    probe_output(output)

def test_mixer_does_not_duplicate_images_on_windows(tmp_path, media):
    from src.backend.advanced_image_mixer import AdvancedImageMixer
    assert AdvancedImageMixer(tmp_path).get_image_files(str(tmp_path)) == [media[0]]


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
def test_mixer_concatenates_mixed_audio_formats(tmp_path, media):
    from src.backend.advanced_image_mixer import AdvancedImageMixer
    compressed = tmp_path / "second.mp3"
    subprocess.run(["ffmpeg", "-y", "-i", str(media[1]), "-ar", "44100", "-ac", "2",
                    str(compressed)], capture_output=True, check=True)
    mixer = AdvancedImageMixer(tmp_path)
    output = mixer.concatenate_audio([str(media[1]), str(compressed)])
    assert output is not None
    assert 1.9 <= mixer.get_audio_duration(output) <= 2.2

@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
@pytest.mark.parametrize("suffix", [".aac", ".wma"])
def test_generator_accepts_supported_audio_streams(tmp_path, media, suffix):
    output = tmp_path / ("source" + suffix)
    subprocess.run(["ffmpeg", "-y", "-i", str(media[1]), str(output)],
                   capture_output=True, check=True)
    generator = VideoGenerator(tmp_path)
    assert generator.is_valid_audio_file(output)
    assert generator.get_audio_duration(output) > 0
