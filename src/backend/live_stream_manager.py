import json
import logging
import os
import random
import shutil
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from sqlalchemy import select

from src.db.database import DATA_DIR, SessionLocal
from src.db.models import LiveStream, LiveStreamLog
from src.utils.secret_store import SecretStore

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".flv"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma"}
TERMINAL_STATUSES = {"stopped", "error", "completed"}
RECOVERABLE_STATUSES = {"starting", "live", "retrying", "recovering"}


class LiveStreamManager:
    def __init__(
        self,
        session_factory=SessionLocal,
        secret_store: Optional[SecretStore] = None,
        ffmpeg_path: Optional[str] = None,
        ffprobe_path: Optional[str] = None,
        media_roots: Optional[Sequence[Path]] = None,
        temp_root: Optional[Path] = None,
        popen_factory=subprocess.Popen,
    ):
        self.session_factory = session_factory
        self.secret_store = secret_store or SecretStore()
        self.ffmpeg_path = ffmpeg_path or os.getenv("FFMPEG_PATH") or shutil.which("ffmpeg")
        self.ffprobe_path = (
            ffprobe_path or os.getenv("FFPROBE_PATH") or shutil.which("ffprobe")
        )
        self.media_roots = [
            Path(root).resolve()
            for root in (
                media_roots
                or self._configured_media_roots()
            )
        ]
        self.temp_root = Path(temp_root or (DATA_DIR / "live_temp")).resolve()
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self.popen_factory = popen_factory
        self._lock = threading.RLock()
        self._runtimes: Dict[str, Dict] = {}
        self._retry_timers: Dict[str, threading.Timer] = {}

    @staticmethod
    def _configured_media_roots() -> List[Path]:
        roots = [Path("uploads"), Path("generations")]
        configured = os.getenv("AUTOTUBE_MEDIA_ROOTS", "")
        roots.extend(Path(item) for item in configured.split(os.pathsep) if item.strip())
        return roots

    def create_stream(self, payload: Dict) -> LiveStream:
        stream_id = payload["id"]
        stream_key = payload["stream_key"].strip()
        settings = payload.get("settings", {})
        stream = LiveStream(
            id=stream_id,
            title=payload.get("title", "Untitled stream").strip() or "Untitled stream",
            status=payload.get("status", "draft"),
            rtmp_url=payload["rtmp_url"].rstrip("/"),
            stream_key_encrypted=self.secret_store.encrypt(stream_key),
            background_type=payload.get("background_type", "videos"),
            visual_paths_json=json.dumps(payload.get("visual_paths", [])),
            audio_paths_json=json.dumps(payload.get("audio_paths", [])),
            settings_json=json.dumps(settings),
            loop=payload.get("loop", True),
            shuffle=payload.get("shuffle", False),
            auto_restart=payload.get("auto_restart", True),
            retry_count=0,
            max_retries=payload.get("max_retries", 10),
            scheduled_start=payload.get("scheduled_start"),
            scheduled_stop=payload.get("scheduled_stop"),
        )
        with self.session_factory() as db:
            db.add(stream)
            db.commit()
            db.refresh(stream)
            db.expunge(stream)
        self.add_log(stream_id, "Stream configuration created.")
        return stream

    def start(self, stream_id: str, is_retry: bool = False) -> None:
        with self._lock:
            current = self._runtimes.get(stream_id)
            if current and not current.get("finished"):
                raise RuntimeError("Stream is already starting or running.")

            timer = self._retry_timers.pop(stream_id, None)
            if timer:
                timer.cancel()

            with self.session_factory() as db:
                stream = db.get(LiveStream, stream_id)
                if stream is None:
                    raise LookupError("Stream not found.")
                if stream.status == "scheduled" and not is_retry:
                    stream.status = "starting"
                elif stream.status in {"stopping", "stopped"} and is_retry:
                    return
                else:
                    stream.status = "starting"
                stream.error_message = None
                stream.pid = None
                if not is_retry:
                    stream.retry_count = 0
                db.commit()

            runtime = {"process": None, "cancelled": False, "finished": False}
            thread = threading.Thread(
                target=self._run, args=(stream_id, runtime), daemon=True, name=f"live-{stream_id[:8]}"
            )
            runtime["thread"] = thread
            self._runtimes[stream_id] = runtime
            thread.start()

    def stop(self, stream_id: str) -> bool:
        with self.session_factory() as db:
            stream = db.get(LiveStream, stream_id)
            if stream is None:
                raise LookupError("Stream not found.")
            if stream.status in TERMINAL_STATUSES:
                return False
            stream.status = "stopping"
            db.commit()

        with self._lock:
            timer = self._retry_timers.pop(stream_id, None)
            if timer:
                timer.cancel()
            runtime = self._runtimes.get(stream_id)
            if runtime:
                runtime["cancelled"] = True
                process = runtime.get("process")
                if process and process.poll() is None:
                    process.terminate()
            else:
                self._set_terminal_state(stream_id, "stopped", None)
        self.add_log(stream_id, "Stop requested by user.")
        return True

    def restart(self, stream_id: str) -> None:
        self.stop(stream_id)
        runtime = self._runtimes.get(stream_id)
        thread = runtime.get("thread") if runtime else None
        if thread:
            thread.join(timeout=8)
        self.start(stream_id)

    def recover(self) -> None:
        with self.session_factory() as db:
            streams = db.execute(
                select(LiveStream).where(LiveStream.status.in_(RECOVERABLE_STATUSES))
            ).scalars().all()
            recover_ids = [stream.id for stream in streams if stream.auto_restart]
            for stream in streams:
                if not stream.auto_restart:
                    stream.status = "stopped"
                    stream.pid = None
                    stream.stopped_at = datetime.now(timezone.utc)
            db.commit()

        for stream_id in recover_ids:
            self.add_log(stream_id, "Recovering stream after backend restart.", "WARNING")
            try:
                self.start(stream_id, is_retry=True)
            except Exception as exc:
                self._mark_error(stream_id, str(exc))

    def shutdown(self) -> None:
        with self._lock:
            timers = list(self._retry_timers.values())
            self._retry_timers.clear()
            runtimes = list(self._runtimes.items())

        for timer in timers:
            timer.cancel()

        for stream_id, runtime in runtimes:
            with self.session_factory() as db:
                stream = db.get(LiveStream, stream_id)
                if stream:
                    stream.status = "recovering" if stream.auto_restart else "stopped"
                    stream.pid = None
                    db.commit()
            runtime["cancelled"] = True
            process = runtime.get("process")
            if process and process.poll() is None:
                process.terminate()

    def build_command(self, stream: LiveStream) -> Tuple[List[str], List[Path]]:
        if not self.ffmpeg_path:
            raise RuntimeError("FFmpeg is not installed or FFMPEG_PATH is not configured.")

        settings = json.loads(stream.settings_json or "{}")
        visuals = self._resolve_media_paths(
            json.loads(stream.visual_paths_json or "[]"),
            IMAGE_EXTENSIONS if stream.background_type == "images" else VIDEO_EXTENSIONS,
        )
        audios = self._resolve_media_paths(
            json.loads(stream.audio_paths_json or "[]"), AUDIO_EXTENSIONS
        )
        if not visuals:
            raise ValueError("At least one visual source is required.")

        if stream.shuffle:
            random.shuffle(visuals)
            random.shuffle(audios)

        audio_mode = settings.get("audio_mode", "replace")
        if stream.background_type == "images" and audio_mode != "replace":
            raise ValueError("Image backgrounds require replacement audio.")
        if audio_mode in {"replace", "mix"} and not audios:
            raise ValueError("The selected audio mode requires at least one audio file.")

        self._validate_rtmp_url(stream.rtmp_url)
        stream_dir = self.temp_root / stream.id
        stream_dir.mkdir(parents=True, exist_ok=True)
        visual_concat = stream_dir / "visuals.txt"
        self._write_concat(
            visual_concat,
            visuals,
            image_duration=float(settings.get("image_duration", 8.0))
            if stream.background_type == "images"
            else None,
        )
        temp_files = [visual_concat]

        command = [
            self.ffmpeg_path,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-progress",
            "pipe:1",
            "-stats_period",
            "5",
            "-re",
        ]
        if stream.loop:
            command.extend(["-stream_loop", "-1"])
        command.extend(["-f", "concat", "-safe", "0", "-i", str(visual_concat)])

        if audios and audio_mode != "keep":
            audio_concat = stream_dir / "audio.txt"
            self._write_concat(audio_concat, audios)
            temp_files.append(audio_concat)
            command.append("-re")
            if stream.loop:
                command.extend(["-stream_loop", "-1"])
            command.extend(["-f", "concat", "-safe", "0", "-i", str(audio_concat)])

        filter_complex, video_label, audio_label = self._build_filters(
            stream.background_type, settings
        )
        command.extend(
            [
                "-filter_complex",
                filter_complex,
                "-map",
                video_label,
                "-map",
                audio_label,
                "-c:v",
                "libx264",
                "-preset",
                settings.get("preset", "veryfast"),
                "-tune",
                "zerolatency",
                "-profile:v",
                "high",
                "-level",
                "4.1",
                "-b:v",
                f"{int(settings.get('video_bitrate', 2500))}k",
                "-maxrate",
                f"{int(settings.get('video_bitrate', 2500) * 1.1)}k",
                "-bufsize",
                f"{int(settings.get('video_bitrate', 2500) * 2)}k",
                "-pix_fmt",
                "yuv420p",
                "-g",
                str(int(settings.get("fps", 30)) * 2),
                "-keyint_min",
                str(int(settings.get("fps", 30))),
                "-sc_threshold",
                "0",
                "-c:a",
                "aac",
                "-b:a",
                f"{int(settings.get('audio_bitrate', 128))}k",
                "-ar",
                "44100",
                "-ac",
                "2",
            ]
        )
        if not stream.loop:
            command.append("-shortest")
        rtmp_target = f"{stream.rtmp_url}/{self.secret_store.decrypt(stream.stream_key_encrypted)}"
        command.extend(["-f", "flv", "-flvflags", "no_duration_filesize", rtmp_target])
        return command, temp_files

    def preflight(self, stream: LiveStream) -> None:
        """Verify that selected files expose the streams required by the FFmpeg graph."""
        if not self.ffprobe_path:
            raise RuntimeError("FFprobe is not installed or FFPROBE_PATH is not configured.")

        settings = json.loads(stream.settings_json or "{}")
        visuals = self._resolve_media_paths(
            json.loads(stream.visual_paths_json or "[]"),
            IMAGE_EXTENSIONS if stream.background_type == "images" else VIDEO_EXTENSIONS,
        )
        audios = self._resolve_media_paths(
            json.loads(stream.audio_paths_json or "[]"), AUDIO_EXTENSIONS
        )
        for path in visuals:
            streams = self._probe_stream_types(path)
            if "video" not in streams:
                raise ValueError(f"Visual source has no video stream: {path.name}")
            if (
                stream.background_type == "videos"
                and settings.get("audio_mode", "replace") in {"keep", "mix"}
                and "audio" not in streams
            ):
                raise ValueError(
                    f"Video source has no audio stream required by audio mode: {path.name}"
                )
        for path in audios:
            if "audio" not in self._probe_stream_types(path):
                raise ValueError(f"Audio source has no audio stream: {path.name}")

    def _probe_stream_types(self, path: Path) -> set:
        result = subprocess.run(
            [
                self.ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "unknown probe error").strip()
            raise ValueError(f"Cannot inspect media file {path.name}: {detail[:300]}")
        try:
            payload = json.loads(result.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError(f"FFprobe returned invalid data for {path.name}.") from exc
        return {
            item.get("codec_type")
            for item in payload.get("streams", [])
            if item.get("codec_type")
        }
    def _build_filters(self, background_type: str, settings: Dict) -> Tuple[str, str, str]:
        width, height = self._parse_resolution(settings.get("resolution", "1280x720"))
        fps = self._bounded_int(settings.get("fps", 30), 15, 60)
        music_volume = self._bounded_float(settings.get("music_volume", 1.0), 0.0, 3.0)
        original_volume = self._bounded_float(
            settings.get("original_audio_volume", 0.35), 0.0, 3.0
        )
        audio_mode = settings.get("audio_mode", "replace")

        parts = [
            f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps={fps},setsar=1,format=yuv420p[background]"
        ]
        if audio_mode == "replace":
            parts.append(
                f"[1:a]aresample=44100,asetpts=N/SR/TB,volume={music_volume:.3f}[baseaudio]"
            )
        elif audio_mode == "mix":
            parts.extend(
                [
                    f"[0:a]aresample=44100,volume={original_volume:.3f}[original]",
                    f"[1:a]aresample=44100,volume={music_volume:.3f}[music]",
                    "[original][music]amix=inputs=2:duration=longest:normalize=0[baseaudio]",
                ]
            )
        elif audio_mode == "keep":
            parts.append(
                f"[0:a]aresample=44100,asetpts=N/SR/TB,volume={original_volume:.3f}[baseaudio]"
            )
        else:
            raise ValueError("Unsupported audio mode.")

        if not settings.get("visualizer_enabled", True):
            parts.extend(["[background]null[vout]", "[baseaudio]anull[aout]"])
            return ";".join(parts), "[vout]", "[aout]"

        visual_width = self._bounded_int(settings.get("spectrum_width", int(width * 0.75)), 80, width)
        visual_height = self._bounded_int(
            settings.get("spectrum_height", int(height * 0.2)), 40, height
        )
        opacity = self._bounded_float(settings.get("opacity", 0.94), 0.05, 1.0)
        panel_opacity = self._bounded_float(settings.get("panel_opacity", 0.35), 0.0, 0.9)
        sensitivity = self._bounded_float(settings.get("sensitivity", 4.0), 0.1, 12.0)
        position = settings.get("visualizer_position", "bottom")
        y_position = {
            "top": 40,
            "center": max(0, (height - visual_height) // 2),
            "bottom": max(0, height - visual_height - 40),
        }.get(position, max(0, height - visual_height - 40))
        colors = self._ffmpeg_colors(settings.get("gradient_colors", ["#c7ff2e", "#ff654a"]))
        style = settings.get("style", "bars")

        if style == "wave":
            visual_filter = (
                f"showwaves=s={visual_width}x{visual_height}:mode=cline:"
                f"colors={colors}:scale=sqrt"
            )
        elif style == "spectrum":
            visual_filter = (
                f"showspectrum=s={visual_width}x{visual_height}:mode=combined:"
                "color=intensity:slide=scroll:scale=log"
            )
        else:
            visual_filter = (
                f"showfreqs=s={visual_width}x{visual_height}:mode=bar:"
                f"colors={colors}:fscale=log:ascale=sqrt:win_size=2048"
            )

        parts.append("[baseaudio]asplit=2[aout][visualaudio]")
        parts.append(
            f"[visualaudio]volume={sensitivity:.3f},{visual_filter},"
            f"format=rgba,colorchannelmixer=aa={opacity:.3f}[visualizer]"
        )
        background_label = "background"
        if panel_opacity > 0:
            panel_y = max(0, y_position - 12)
            panel_height = min(height - panel_y, visual_height + 24)
            parts.append(
                f"[background]drawbox=x=(iw-{visual_width + 24})/2:y={panel_y}:"
                f"w={visual_width + 24}:h={panel_height}:color=black@{panel_opacity:.3f}:t=fill[panel]"
            )
            background_label = "panel"
        parts.append(
            f"[{background_label}][visualizer]overlay=x=(W-w)/2:y={y_position}:"
            "shortest=1:format=auto[vout]"
        )
        return ";".join(parts), "[vout]", "[aout]"

    def _run(self, stream_id: str, runtime: Dict) -> None:
        process = None
        temp_files: List[Path] = []
        try:
            with self.session_factory() as db:
                stream = db.get(LiveStream, stream_id)
                if stream is None:
                    return
                self.preflight(stream)
                command, temp_files = self.build_command(stream)

            if runtime.get("cancelled"):
                self._set_terminal_state(stream_id, "stopped", None)
                return

            self.add_log(stream_id, "Starting FFmpeg process.")
            process = self.popen_factory(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
            )
            runtime["process"] = process
            with self.session_factory() as db:
                stream = db.get(LiveStream, stream_id)
                if stream is None:
                    process.terminate()
                    return
                stream.status = "live"
                stream.pid = process.pid
                stream.started_at = stream.started_at or datetime.now(timezone.utc)
                stream.stopped_at = None
                stream.error_message = None
                db.commit()
            self.add_log(stream_id, f"Stream is live (PID {process.pid}).", "SUCCESS")

            last_heartbeat = 0.0
            if process.stdout:
                for raw_line in process.stdout:
                    line = raw_line.strip()
                    if not line:
                        continue
                    if "=" not in line or line.startswith(("error=", "warning=")):
                        self.add_log(stream_id, line[:2000], "FFMPEG")
                    now = datetime.now(timezone.utc).timestamp()
                    if now - last_heartbeat >= 30:
                        self._touch(stream_id)
                        last_heartbeat = now

            return_code = process.wait()
            self._handle_exit(stream_id, return_code, runtime)
        except (ValueError, RuntimeError) as exc:
            logger.exception("Live stream %s has an invalid configuration", stream_id)
            if process is None:
                self._mark_error(stream_id, str(exc))
            else:
                self.add_log(stream_id, str(exc), "ERROR")
                self._handle_exit(stream_id, -1, runtime, str(exc))
        except Exception as exc:
            logger.exception("Live stream %s failed", stream_id)
            self.add_log(stream_id, str(exc), "ERROR")
            self._handle_exit(stream_id, -1, runtime, str(exc))
        finally:
            runtime["finished"] = True
            with self._lock:
                current = self._runtimes.get(stream_id)
                if current is runtime:
                    self._runtimes.pop(stream_id, None)
            self._cleanup_temp_files(temp_files)

    def _handle_exit(
        self, stream_id: str, return_code: int, runtime: Dict, error: Optional[str] = None
    ) -> None:
        with self.session_factory() as db:
            stream = db.get(LiveStream, stream_id)
            if stream is None:
                return
            current_status = stream.status
            stream.pid = None

            if current_status == "recovering":
                db.commit()
                return
            if runtime.get("cancelled") or current_status in {"stopping", "stopped"}:
                stream.status = "stopped"
                stream.stopped_at = datetime.now(timezone.utc)
                db.commit()
                return
            if return_code == 0:
                stream.status = "completed"
                stream.stopped_at = datetime.now(timezone.utc)
                db.commit()
                return

            message = error or f"FFmpeg exited with code {return_code}."
            stream.error_message = message
            if stream.auto_restart and stream.retry_count < stream.max_retries:
                stream.retry_count += 1
                retry_count = stream.retry_count
                stream.status = "retrying"
                db.commit()
                delay = min(2 * (1.5 ** (retry_count - 1)), 30)
                self.add_log(
                    stream_id,
                    f"{message} Retrying in {delay:.1f}s ({retry_count}/{stream.max_retries}).",
                    "WARNING",
                )
                timer = threading.Timer(delay, self._retry_start, args=(stream_id,))
                timer.daemon = True
                with self._lock:
                    self._retry_timers[stream_id] = timer
                timer.start()
                return

            stream.status = "error"
            stream.stopped_at = datetime.now(timezone.utc)
            db.commit()

    def _retry_start(self, stream_id: str) -> None:
        with self._lock:
            self._retry_timers.pop(stream_id, None)
        try:
            self.start(stream_id, is_retry=True)
        except Exception as exc:
            self._mark_error(stream_id, str(exc))

    def _mark_error(self, stream_id: str, message: str) -> None:
        self._set_terminal_state(stream_id, "error", message)
        self.add_log(stream_id, message, "ERROR")

    def _set_terminal_state(
        self, stream_id: str, status: str, error_message: Optional[str]
    ) -> None:
        with self.session_factory() as db:
            stream = db.get(LiveStream, stream_id)
            if stream:
                stream.status = status
                stream.pid = None
                stream.error_message = error_message
                stream.stopped_at = datetime.now(timezone.utc)
                db.commit()

    def _touch(self, stream_id: str) -> None:
        with self.session_factory() as db:
            stream = db.get(LiveStream, stream_id)
            if stream:
                stream.updated_at = datetime.now(timezone.utc)
                db.commit()

    def add_log(self, stream_id: str, message: str, level: str = "INFO") -> None:
        with self.session_factory() as db:
            db.add(
                LiveStreamLog(
                    stream_id=stream_id,
                    level=level[:16],
                    message=message[:4000],
                )
            )
            db.commit()
            stale_ids = db.execute(
                select(LiveStreamLog.id)
                .where(LiveStreamLog.stream_id == stream_id)
                .order_by(LiveStreamLog.id.desc())
                .offset(200)
            ).scalars().all()
            if stale_ids:
                db.query(LiveStreamLog).filter(LiveStreamLog.id.in_(stale_ids)).delete(
                    synchronize_session=False
                )
                db.commit()

    def _resolve_media_paths(
        self, values: Iterable[str], allowed_extensions: set
    ) -> List[Path]:
        resolved = []
        allow_local = os.getenv("AUTOTUBE_ALLOW_LOCAL_PATHS", "false").lower() == "true"
        for value in values:
            path = Path(value).expanduser().resolve()
            if not path.is_file():
                raise ValueError(f"Media file not found: {path.name}")
            if path.suffix.lower() not in allowed_extensions:
                raise ValueError(f"Unsupported media type: {path.suffix}")
            if not allow_local and not any(self._is_relative_to(path, root) for root in self.media_roots):
                raise ValueError(
                    f"Media file is outside configured storage roots: {path.name}"
                )
            resolved.append(path)
        return resolved

    @staticmethod
    def _is_relative_to(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False

    @staticmethod
    def _write_concat(
        destination: Path, paths: Sequence[Path], image_duration: Optional[float] = None
    ) -> None:
        lines = []
        for path in paths:
            escaped = path.as_posix().replace("'", "'\\''")
            lines.append(f"file '{escaped}'")
            if image_duration is not None:
                duration = min(max(image_duration, 0.5), 120.0)
                lines.append(f"duration {duration:.3f}")
        if image_duration is not None and paths:
            escaped = paths[-1].as_posix().replace("'", "'\\''")
            lines.append(f"file '{escaped}'")
        destination.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _validate_rtmp_url(value: str) -> None:
        parsed = urlparse(value)
        if parsed.scheme not in {"rtmp", "rtmps"} or not parsed.netloc:
            raise ValueError("RTMP URL must use rtmp:// or rtmps://.")

    @staticmethod
    def _parse_resolution(value: str) -> Tuple[int, int]:
        try:
            width, height = (int(part) for part in value.lower().split("x", 1))
        except (TypeError, ValueError):
            raise ValueError("Resolution must use WIDTHxHEIGHT format.")
        if width < 320 or height < 240 or width > 3840 or height > 2160:
            raise ValueError("Resolution is outside the supported range.")
        return width, height

    @staticmethod
    def _ffmpeg_colors(colors: Iterable[str]) -> str:
        result = []
        for color in list(colors)[:4]:
            value = str(color).strip().lstrip("#")
            if len(value) != 6 or any(char not in "0123456789abcdefABCDEF" for char in value):
                raise ValueError("Visualizer colors must be six-digit hex values.")
            result.append(f"0x{value.upper()}")
        return "|".join(result or ["0xC7FF2E"])

    @staticmethod
    def _bounded_int(value, minimum: int, maximum: int) -> int:
        number = int(value)
        if number < minimum or number > maximum:
            raise ValueError(f"Value must be between {minimum} and {maximum}.")
        return number

    @staticmethod
    def _bounded_float(value, minimum: float, maximum: float) -> float:
        number = float(value)
        if number < minimum or number > maximum:
            raise ValueError(f"Value must be between {minimum} and {maximum}.")
        return number

    @staticmethod
    def _cleanup_temp_files(paths: Iterable[Path]) -> None:
        parents = set()
        for path in paths:
            parents.add(path.parent)
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        for parent in parents:
            try:
                parent.rmdir()
            except OSError:
                pass
