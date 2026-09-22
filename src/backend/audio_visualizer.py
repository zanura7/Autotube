"""
Audio Visualizer Backend
Render a thumbnail-based MP4 with audio-reactive spectrum overlays.
"""

import subprocess
import math
import random
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence, Tuple

from utils.constants import DEFAULT_AUDIO_BITRATE, DEFAULT_RESOLUTION, TIMEOUT_VIDEO_RENDER, VIDEO_CRF_DEFAULT, VIDEO_PRESET_DEFAULT
from utils.enhanced_logger import create_enhanced_logger
from utils.ffmpeg_checker import get_ffmpeg_path

ProgressCallback = Optional[Callable[[float, str], None]]


class AudioVisualizer:
    """FFmpeg-powered audio visualizer renderer."""

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"}
    AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma"}
    VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}
    STYLE_GROUPS = {
        "Classic Bar": "bars",
        "Rounded Bar": "bars",
        "Mirror Bar": "bars",
        "Gradient Bar": "bars",
        "3D Bar": "bars",
        "Fire": "spectrum",
        "Particle": "spectrum",
        "Equalizer Grid": "bars",
        "Diamond Bars": "bars",
        "Hex Grid": "spectrum",
        "Chevron Bars": "bars",
        "Pulse Grid": "spectrum",
        "Smooth Wave": "wave",
        "Dual Wave": "wave",
        "Neon Wave": "wave",
        "Pulse Wave": "wave",
        "Mirror Wave": "wave",
        "Ribbon Wave": "wave",
        "Circle Ring": "circle",
        "Circle Bars": "circle",
        "Double Ring": "circle",
        "Radial": "circle",
        "Orbit": "circle",
        "Glow Pulse": "circle",
        "Beat Ring": "circle",
        "Spiral Galaxy": "circle",
        "Starburst": "circle",
        "Radar Web": "circle",
        "Ripple Rings": "circle",
        "Constellation": "circle",
    }

    def __init__(self, output_folder, console_log=None, config=None):
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.console_log = console_log
        self.config = config
        self.logger = create_enhanced_logger(console_log)
        self.ffmpeg_path = get_ffmpeg_path(config)
        self.ffprobe_path = self._get_ffprobe_path()

    def render(
        self,
        thumbnail_path,
        audio_path,
        output_path=None,
        resolution: str = DEFAULT_RESOLUTION,
        style: str = "Classic Bar",
        align: str = "Center",
        spectrum_width: int = 650,
        spectrum_height: int = 180,
        bar_count: int = 64,
        sensitivity: float = 1.5,
        opacity: float = 1.0,
        x_offset: int = 0,
        y_offset: int = 0,
        gradient_colors: Sequence[str] = ("#28e6ae", "#ff3434", "#f4ef2e"),
        logo_path=None,
        logo_size: int = 180,
        logo_opacity: float = 0.9,
        logo_rotation: float = 0.0,
        logo_pulse: bool = False,
        effect: str = "None",
        progress_callback: ProgressCallback = None,
    ) -> Optional[Path]:
        """Render an MP4 visualizer."""
        thumbnail = self._require_file(thumbnail_path, self.IMAGE_EXTENSIONS, "thumbnail")
        audio = self._require_file(audio_path, self.AUDIO_EXTENSIONS, "audio")
        logo = self._optional_file(logo_path, self.IMAGE_EXTENSIONS, "logo")
        output = Path(output_path) if output_path else self._default_output("audio_visualizer", ".mp4")
        width, height = self._parse_resolution(resolution)
        duration = self.get_duration(audio)

        spectrum_width = self._clamp_int(spectrum_width, 80, width)
        spectrum_height = self._clamp_int(spectrum_height, 40, height)
        bar_count = self._clamp_int(bar_count, 8, 256)
        sensitivity = max(0.1, min(float(sensitivity), 5.0))
        opacity = max(0.05, min(float(opacity), 1.0))
        logo_size = self._clamp_int(logo_size, 24, min(width, height))
        logo_opacity = max(0.05, min(float(logo_opacity), 1.0))

        if progress_callback:
            progress_callback(0.1, "Preparing visualizer render...")

        filter_complex, video_label = self._build_filter(
            width=width,
            height=height,
            style=style,
            align=align,
            spectrum_width=spectrum_width,
            spectrum_height=spectrum_height,
            bar_count=bar_count,
            sensitivity=sensitivity,
            opacity=opacity,
            x_offset=x_offset,
            y_offset=y_offset,
            gradient_colors=gradient_colors,
            logo=logo,
            logo_size=logo_size,
            logo_opacity=logo_opacity,
            logo_rotation=logo_rotation,
            logo_pulse=logo_pulse,
            effect=effect,
        )

        cmd = [self.ffmpeg_path, "-y", "-loop", "1", "-i", str(thumbnail), "-i", str(audio)]
        if logo:
            cmd.extend(["-loop", "1", "-i", str(logo)])

        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", video_label,
            "-map", "1:a:0",
            "-t", f"{duration:.3f}",
            "-c:v", "libx264",
            "-preset", VIDEO_PRESET_DEFAULT,
            "-crf", str(VIDEO_CRF_DEFAULT),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", DEFAULT_AUDIO_BITRATE,
            "-shortest",
            str(output),
        ])

        return self._run(cmd, output, progress_callback)

    def render_composition(
        self,
        output_path,
        background_type: str = "images",
        image_paths: Optional[Sequence[str]] = None,
        video_path=None,
        audio_path=None,
        audio_mode: str = "replace",
        video_shorter_mode: str = "loop",
        image_order: str = "sequential",
        image_duration: float = 6.0,
        transition_type: str = "crossfade",
        transition_duration: float = 0.8,
        resolution: str = DEFAULT_RESOLUTION,
        style: str = "Classic Bar",
        position: str = "bottom",
        spectrum_width: int = 1400,
        spectrum_height: int = 210,
        bar_count: int = 64,
        sensitivity: float = 8.0,
        opacity: float = 0.94,
        panel_opacity: float = 0.38,
        gradient_colors: Sequence[str] = ("#c7ff2e", "#ff654a"),
        music_volume: float = 1.0,
        original_audio_volume: float = 0.35,
        progress_callback: ProgressCallback = None,
    ) -> Optional[Path]:
        """Render a visualizer over an image slideshow or a source video."""
        output = Path(output_path)
        width, height = self._parse_resolution(resolution)
        background_type = str(background_type or "images").lower()
        audio_mode = str(audio_mode or "replace").lower()
        video_shorter_mode = str(video_shorter_mode or "loop").lower()
        if background_type not in {"images", "video"}:
            raise ValueError("Background type must be images or video.")
        if audio_mode not in {"replace", "mix", "keep"}:
            raise ValueError("Audio mode must be replace, mix, or keep.")
        if video_shorter_mode not in {"loop", "freeze"}:
            raise ValueError("Video shorter mode must be loop or freeze.")
        if style not in self.STYLE_GROUPS:
            raise ValueError("Unsupported visualizer style.")

        spectrum_width = self._clamp_int(spectrum_width, 80, width)
        spectrum_height = self._clamp_int(spectrum_height, 40, height)
        bar_count = self._clamp_int(bar_count, 8, 256)
        sensitivity = max(0.1, min(float(sensitivity), 12.0))
        opacity = max(0.05, min(float(opacity), 1.0))
        panel_opacity = max(0.0, min(float(panel_opacity), 0.9))
        music_volume = max(0.0, min(float(music_volume), 3.0))
        original_audio_volume = max(0.0, min(float(original_audio_volume), 3.0))

        audio = None
        if audio_mode != "keep" or background_type == "images":
            audio = self._require_file(audio_path, self.AUDIO_EXTENSIONS, "audio")
        elif audio_path:
            audio = self._optional_file(audio_path, self.AUDIO_EXTENSIONS, "audio")

        temp_slideshow = None
        if progress_callback:
            progress_callback(0.05, "Preparing visualizer sources...")

        try:
            if background_type == "images":
                if audio_mode == "keep":
                    raise ValueError("Keep original audio is only available for video backgrounds.")
                images = [self._require_file(path, self.IMAGE_EXTENSIONS, "image")
                          for path in (image_paths or [])]
                if not images:
                    raise ValueError("Select at least one background image.")
                if len(images) > 100:
                    raise ValueError("A maximum of 100 images is supported.")
                temp_slideshow = output.parent / f".{output.stem}-{uuid.uuid4().hex}.slideshow.mp4"
                self._create_slideshow_cycle(
                    images, temp_slideshow, width, height, image_order,
                    image_duration, transition_type, transition_duration,
                )
                target_duration = self.get_duration(audio)
                cmd = [self.ffmpeg_path, "-y", "-stream_loop", "-1", "-i", str(temp_slideshow),
                       "-i", str(audio)]
                audio_input = 1
                freeze_video = False
            else:
                video = self._require_file(video_path, self.VIDEO_EXTENSIONS, "video")
                video_duration = self.get_duration(video)
                has_audio = self.has_audio_stream(video)
                if audio_mode in {"keep", "mix"} and not has_audio:
                    raise ValueError(f"Video has no audio stream for {audio_mode} mode.")
                target_duration = video_duration if audio_mode == "keep" else self.get_duration(audio)
                should_extend = target_duration > video_duration + 0.05
                cmd = [self.ffmpeg_path, "-y"]
                if should_extend and video_shorter_mode == "loop":
                    cmd.extend(["-stream_loop", "-1"])
                cmd.extend(["-i", str(video)])
                if audio_mode != "keep":
                    cmd.extend(["-i", str(audio)])
                audio_input = 0 if audio_mode == "keep" else 1
                freeze_video = should_extend and video_shorter_mode == "freeze"

            filter_complex, video_label, audio_label = self._build_composition_filter(
                width=width,
                height=height,
                target_duration=target_duration,
                audio_mode=audio_mode,
                audio_input=audio_input,
                freeze_video=freeze_video,
                style=style,
                position=position,
                spectrum_width=spectrum_width,
                spectrum_height=spectrum_height,
                bar_count=bar_count,
                sensitivity=sensitivity,
                opacity=opacity,
                panel_opacity=panel_opacity,
                gradient_colors=gradient_colors,
                music_volume=music_volume,
                original_audio_volume=original_audio_volume,
            )
            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", video_label,
                "-map", audio_label,
                "-t", f"{target_duration:.3f}",
                "-c:v", "libx264",
                "-preset", VIDEO_PRESET_DEFAULT,
                "-crf", str(VIDEO_CRF_DEFAULT),
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", DEFAULT_AUDIO_BITRATE,
                "-movflags", "+faststart",
                "-shortest",
                str(output),
            ])
            return self._run(cmd, output, progress_callback)
        finally:
            if temp_slideshow:
                temp_slideshow.unlink(missing_ok=True)

    def _create_slideshow_cycle(
        self,
        image_paths: Sequence[Path],
        output: Path,
        width: int,
        height: int,
        image_order: str,
        image_duration: float,
        transition_type: str,
        transition_duration: float,
    ) -> None:
        images = list(image_paths)
        if image_order not in {"sequential", "random"}:
            raise ValueError("Image order must be sequential or random.")
        if image_order == "random":
            random.shuffle(images)
        image_duration = max(0.5, min(float(image_duration), 120.0))
        transition_type = str(transition_type or "none").lower()
        if transition_type not in {"none", "fade", "crossfade"}:
            raise ValueError("Unsupported image transition.")
        transition_duration = max(0.0, min(float(transition_duration), image_duration - 0.1))

        cmd = [self.ffmpeg_path, "-y"]
        for image in images:
            cmd.extend(["-loop", "1", "-t", f"{image_duration:.3f}", "-i", str(image)])
        parts = []
        for index in range(len(images)):
            parts.append(
                f"[{index}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},setsar=1,fps=25,format=yuv420p,"
                f"trim=duration={image_duration:.3f},setpts=PTS-STARTPTS[s{index}]"
            )
        if len(images) == 1:
            final_label = "[s0]"
            cycle_duration = image_duration
        elif transition_type == "none" or transition_duration <= 0:
            inputs = "".join(f"[s{i}]" for i in range(len(images)))
            parts.append(f"{inputs}concat=n={len(images)}:v=1:a=0[slide]")
            final_label = "[slide]"
            cycle_duration = image_duration * len(images)
        else:
            transition = "fadeblack" if transition_type == "fade" else "fade"
            previous = "s0"
            for index in range(1, len(images)):
                output_label = f"xf{index}"
                offset = index * (image_duration - transition_duration)
                parts.append(
                    f"[{previous}][s{index}]xfade=transition={transition}:"
                    f"duration={transition_duration:.3f}:offset={offset:.3f}[{output_label}]"
                )
                previous = output_label
            final_label = f"[{previous}]"
            cycle_duration = image_duration * len(images) - transition_duration * (len(images) - 1)
        cmd.extend([
            "-filter_complex", ";".join(parts),
            "-map", final_label,
            "-t", f"{cycle_duration:.3f}",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", str(output),
        ])
        output.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_VIDEO_RENDER)
        if result.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
            self.logger.log_ffmpeg_error(result.returncode, result.stderr, "Visualizer slideshow")
            raise RuntimeError("Could not create the image slideshow.")

    def _build_composition_filter(
        self,
        width: int,
        height: int,
        target_duration: float,
        audio_mode: str,
        audio_input: int,
        freeze_video: bool,
        style: str,
        position: str,
        spectrum_width: int,
        spectrum_height: int,
        bar_count: int,
        sensitivity: float,
        opacity: float,
        panel_opacity: float,
        gradient_colors: Sequence[str],
        music_volume: float,
        original_audio_volume: float,
    ) -> Tuple[str, str, str]:
        duration = f"{target_duration:.3f}"
        background_filters = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1,fps=25"
        )
        if freeze_video:
            background_filters += f",tpad=stop_mode=clone:stop_duration={duration}"
        background_filters += f",trim=duration={duration},setpts=PTS-STARTPTS,format=rgba"

        position = str(position or "bottom").lower()
        if position == "top":
            overlay_y = min(65, max(0, height - spectrum_height))
        elif position == "center":
            overlay_y = max(0, (height - spectrum_height) // 2)
        else:
            overlay_y = max(0, height - spectrum_height - 65)
        panel_width = min(width, spectrum_width + 80)
        panel_height = min(height, spectrum_height + 36)
        panel_x = max(0, (width - panel_width) // 2)
        panel_y = max(0, min(height - panel_height, overlay_y - 18))

        parts = [f"[0:v]{background_filters}[bg]"]
        if audio_mode == "mix":
            parts.extend([
                f"[0:a]volume={original_audio_volume:.3f}[original]",
                f"[{audio_input}:a]volume={music_volume:.3f}[music]",
                f"[original][music]amix=inputs=2:duration=longest:dropout_transition=2,"
                f"atrim=duration={duration},asetpts=PTS-STARTPTS[program]",
            ])
        else:
            volume = original_audio_volume if audio_mode == "keep" else music_volume
            parts.append(
                f"[{audio_input}:a]volume={volume:.3f},atrim=duration={duration},"
                f"asetpts=PTS-STARTPTS[program]"
            )
        parts.append("[program]asplit=2[visualaudio][outaudio]")

        colors = self._format_colors(gradient_colors)
        style_kind = self.STYLE_GROUPS.get(style, "bars")
        if style_kind == "wave":
            parts.append(
                f"[visualaudio]volume={sensitivity:.3f},showwaves=s={spectrum_width}x{spectrum_height}:"
                f"mode=line:r=25:colors={colors},format=rgba,colorkey=0x000000:0.08:0.05,"
                f"colorchannelmixer=aa={opacity:.3f}[viz]"
            )
        elif style_kind == "spectrum":
            parts.append(
                f"[visualaudio]volume={sensitivity:.3f},showspectrum=s={spectrum_width}x{spectrum_height}:"
                f"slide=scroll:mode=combined:color=intensity:scale=sqrt,format=rgba,"
                f"colorkey=0x000000:0.08:0.05,colorchannelmixer=aa={opacity:.3f}[viz]"
            )
        else:
            render_height = max(1, spectrum_height // 2) if style == "Mirror Bar" else spectrum_height
            parts.append(
                f"[visualaudio]volume={sensitivity:.3f},showfreqs=s={bar_count}x{render_height}:r=25:"
                f"mode=bar:ascale=sqrt:fscale=log:win_size=2048:colors={colors},format=rgba,"
                f"scale={spectrum_width}:{render_height}:flags=neighbor,"
                f"colorkey=0x000000:0.08:0.05,colorchannelmixer=aa={opacity:.3f}[bars]"
            )
            if style == "Mirror Bar":
                parts.extend([
                    "[bars]split[top][bottom]",
                    "[bottom]vflip[flipped]",
                    f"[top][flipped]vstack,scale={spectrum_width}:{spectrum_height}[viz]",
                ])
            elif style == "Rounded Bar":
                parts.append("[bars]gblur=sigma=0.7[viz]")
            else:
                parts.append("[bars]null[viz]")

        base_label = "bg"
        if panel_opacity > 0:
            parts.append(
                f"[bg]drawbox=x={panel_x}:y={panel_y}:w={panel_width}:h={panel_height}:"
                f"color=black@{panel_opacity:.3f}:t=fill[panel]"
            )
            base_label = "panel"
        parts.append(
            f"[{base_label}][viz]overlay=(W-w)/2:{overlay_y}:format=auto,format=yuv420p[v]"
        )
        return ";".join(parts), "[v]", "[outaudio]"

    def get_duration(self, media_path) -> float:
        cmd = [
            self.ffprobe_path,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"Could not read duration for {media_path}")
        duration = float(result.stdout.strip())
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("Media duration must be a positive finite number.")
        return duration

    def has_audio_stream(self, media_path) -> bool:
        cmd = [
            self.ffprobe_path, "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=index", "-of", "csv=p=0", str(media_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return result.returncode == 0 and bool(result.stdout.strip())

    def _build_filter(
        self,
        width: int,
        height: int,
        style: str,
        align: str,
        spectrum_width: int,
        spectrum_height: int,
        bar_count: int,
        sensitivity: float,
        opacity: float,
        x_offset: int,
        y_offset: int,
        gradient_colors: Sequence[str],
        logo: Optional[Path],
        logo_size: int,
        logo_opacity: float,
        logo_rotation: float,
        logo_pulse: bool,
        effect: str,
    ) -> Tuple[str, str]:
        colors = self._format_colors(gradient_colors)
        style_kind = self.STYLE_GROUPS.get(style, "bars")
        parts = [
            f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1,format=rgba[bg]"
        ]

        if style_kind == "wave":
            visual_filter = (
                f"[1:a]volume={sensitivity:.3f},showwaves=s={spectrum_width}x{spectrum_height}:"
                f"mode=line:r=25:colors={colors},format=rgba,colorchannelmixer=aa={opacity:.3f}[viz]"
            )
        elif style_kind == "spectrum":
            visual_filter = (
                f"[1:a]volume={sensitivity:.3f},showspectrum=s={spectrum_width}x{spectrum_height}:"
                f"slide=scroll:mode=combined:color=intensity:scale=sqrt,format=rgba,"
                f"colorchannelmixer=aa={opacity:.3f}[viz]"
            )
        else:
            mode = "bar" if style_kind in {"bars", "circle"} else "line"
            render_height = max(1, spectrum_height // 2) if style == "Mirror Bar" else spectrum_height
            visual_filter = (
                f"[1:a]volume={sensitivity:.3f},showfreqs=s={bar_count}x{render_height}:"
                f"mode={mode}:ascale=sqrt:fscale=log:win_size=2048:colors={colors},format=rgba,"
                f"scale={spectrum_width}:{render_height}:flags=neighbor,"
                f"colorchannelmixer=aa={opacity:.3f}[bars]"
            )
            if style == "Mirror Bar":
                visual_filter += (
                    ";[bars]split[top][bottom];[bottom]vflip[flipped];"
                    f"[top][flipped]vstack,scale={spectrum_width}:{spectrum_height}[viz]"
                )
            elif style == "Rounded Bar":
                visual_filter += ";[bars]gblur=sigma=0.7[viz]"
            else:
                visual_filter += ";[bars]null[viz]"
        parts.append(visual_filter)

        overlay_x = self._overlay_x(width, spectrum_width, align, x_offset)
        overlay_y = self._overlay_y(height, spectrum_height, y_offset)
        parts.append(f"[bg][viz]overlay={overlay_x}:{overlay_y}:format=auto[baseviz]")
        current = "baseviz"

        if logo:
            rotate = max(-360.0, min(float(logo_rotation), 360.0))
            pulse_scale = "1+0.04*sin(t*4)" if logo_pulse else "1"
            logo_chain = (
                f"[2:v]scale={logo_size}:-1,format=rgba,"
                f"scale=iw*({pulse_scale}):ih*({pulse_scale}):eval=frame,"
                f"rotate={rotate:.3f}*PI/180:c=none:ow=rotw({rotate:.3f}*PI/180):oh=roth({rotate:.3f}*PI/180),"
                f"colorchannelmixer=aa={logo_opacity:.3f}[logo]"
            )
            parts.append(logo_chain)
            parts.append(f"[{current}][logo]overlay=(W-w)/2:(H-h)/2:format=auto[withlogo]")
            current = "withlogo"

        effect_name = (effect or "None").strip().lower()
        if effect_name == "snow":
            parts.append(f"[{current}]noise=alls=8:allf=t+u,format=yuv420p[v]")
        elif effect_name == "cinema glow":
            parts.append(f"[{current}]eq=contrast=1.08:saturation=1.12:brightness=0.015,format=yuv420p[v]")
        else:
            parts.append(f"[{current}]format=yuv420p[v]")

        return ";".join(parts), "[v]"

    def _run(self, cmd, output_path: Path, progress_callback: ProgressCallback) -> Optional[Path]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger.log("Starting audio visualizer render...")
        self.logger.log(f"FFmpeg command: {' '.join(cmd[:12])} ...")
        if progress_callback:
            progress_callback(0.35, "Rendering MP4 visualizer...")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_VIDEO_RENDER)
        except subprocess.TimeoutExpired:
            self.logger.log("Audio visualizer render timed out", "ERROR")
            return None

        if result.returncode != 0:
            self.logger.log_ffmpeg_error(result.returncode, result.stderr, "Audio visualizer")
            return None
        if not output_path.exists() or output_path.stat().st_size == 0:
            self.logger.log("Audio visualizer failed: output file was not created", "ERROR")
            return None

        if progress_callback:
            progress_callback(1.0, "Visualizer complete")
        self.logger.log(f"Audio visualizer created: {output_path}", "SUCCESS")
        return output_path

    def _default_output(self, stem: str, suffix: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return self.output_folder / f"{stem}_{timestamp}{suffix}"

    def _require_file(self, file_path, extensions: Iterable[str], label: str) -> Path:
        if not file_path:
            raise ValueError(f"{label.title()} file is required.")
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"{label.title()} file not found: {path}")
        if path.suffix.lower() not in extensions:
            raise ValueError(f"Unsupported {label} file extension: {path.suffix}")
        return path

    def _optional_file(self, file_path, extensions: Iterable[str], label: str) -> Optional[Path]:
        if not file_path:
            return None
        return self._require_file(file_path, extensions, label)

    def _get_ffprobe_path(self) -> str:
        ffmpeg = Path(self.ffmpeg_path)
        if ffmpeg.name.lower().startswith("ffmpeg"):
            ffprobe = ffmpeg.with_name("ffprobe.exe" if ffmpeg.suffix.lower() == ".exe" else "ffprobe")
            if ffprobe.exists():
                return str(ffprobe)
        return "ffprobe"

    def _parse_resolution(self, resolution: str) -> Tuple[int, int]:
        presets = {
            "16:9 (1920 x 1080)": "1920x1080",
            "9:16 (1080 x 1920)": "1080x1920",
            "1:1 (1080 x 1080)": "1080x1080",
        }
        value = presets.get(resolution, resolution)
        width, height = value.lower().replace(" ", "").split("x", 1)
        width, height = int(width), int(height)
        if width < 2 or height < 2 or width % 2 or height % 2:
            raise ValueError("Resolution must contain positive even dimensions for H.264.")
        return width, height

    def _format_colors(self, colors: Sequence[str]) -> str:
        cleaned = []
        for color in colors:
            value = str(color or "").strip()
            if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                cleaned.append("0x" + value[1:])
        return "|".join(cleaned[:4]) if cleaned else "0x28e6ae|0xff3434|0xf4ef2e"

    def _overlay_x(self, video_width: int, visual_width: int, align: str, offset: int) -> str:
        align = (align or "Center").lower()
        safe_offset = max(-video_width, min(int(offset), video_width))
        if align == "left":
            return str(max(0, safe_offset))
        if align == "right":
            return f"W-w-{max(0, safe_offset)}"
        return f"(W-w)/2+{safe_offset}"

    def _overlay_y(self, video_height: int, visual_height: int, offset: int) -> str:
        default_y = int(video_height * 0.62)
        safe_offset = max(-video_height, min(int(offset), video_height))
        return str(max(0, min(video_height - visual_height, default_y + safe_offset)))

    def _clamp_int(self, value, minimum: int, maximum: int) -> int:
        return min(maximum, max(minimum, int(float(value))))
