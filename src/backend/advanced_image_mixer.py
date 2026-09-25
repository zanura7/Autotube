"""
Advanced Image Mixer
Generate unique videos from multiple images with pan/zoom effects and audio playlist
"""

import subprocess
import random
from pathlib import Path
from typing import List, Optional, Callable
import json

from utils.constants import (
    MAX_MULTI_IMAGES, MAX_MULTI_AUDIO, IMAGES_PER_CHUNK,
    ROTATION_MODE_SEQUENTIAL, ROTATION_MODE_RANDOM, ROTATION_MODE_MIXED,
    EFFECT_TYPE_ZOOM, EFFECT_TYPE_PAN, EFFECT_TYPE_FADE, EFFECT_TYPE_NONE,
    EFFECT_WEIGHT_ZOOM, EFFECT_WEIGHT_PAN, EFFECT_WEIGHT_FADE,
    PAN_DIRECTION_LEFT_TO_RIGHT, PAN_DIRECTION_RIGHT_TO_LEFT,
    PAN_DIRECTION_TOP_TO_BOTTOM, PAN_DIRECTION_BOTTOM_TO_TOP, PAN_DIRECTION_DIAGONAL,
    TRANSITION_TYPE_CROSSFADE, TRANSITION_TYPE_FADE, TRANSITION_TYPE_NONE,
    DEFAULT_RESOLUTION, VIDEO_CRF_DEFAULT, VIDEO_PRESET_DEFAULT,
    DEFAULT_AUDIO_BITRATE, TIMEOUT_VIDEO_RENDER, TIMEOUT_AUDIO_CONCAT
)
from utils.enhanced_logger import create_enhanced_logger


class AdvancedImageMixer:
    """Advanced multi-image + multi-audio video generator"""

    def __init__(self, output_folder, console_log=None):
        """
        Initialize advanced image mixer

        Args:
            output_folder: Path to output folder
            console_log: Console log widget for logging
        """
        self.output_folder = Path(output_folder)
        self.console_log = console_log
        self.logger = create_enhanced_logger(console_log)

        # Create output folder if it doesn't exist
        self.output_folder.mkdir(parents=True, exist_ok=True)

    def log(self, message, level="INFO"):
        """Log a message using enhanced logger"""
        self.logger.log(message, level)

    def generate_video(
        self,
        image_folder: Optional[str],
        audio_files: List[str],
        output_file: str,
        rotation_mode: str = ROTATION_MODE_SEQUENTIAL,
        effect_type: str = "mixed",
        transition_type: str = TRANSITION_TYPE_CROSSFADE,
        transition_duration: float = 1.0,
        resolution: str = DEFAULT_RESOLUTION,
        progress_callback: Optional[Callable] = None,
        image_files: Optional[List[str]] = None,
    ) -> bool:
        """
        Generate video from multiple images and audio files

        Args:
            image_folder: Folder with images
            audio_files: List of audio file paths
            output_file: Output video path
            rotation_mode: "sequential", "random", or "mixed"
            effect_type: "mixed", "zoom", "pan", "fade", or "none"
            transition_type: "crossfade", "fade", or "none"
            transition_duration: Transition duration in seconds
            resolution: Output resolution
            progress_callback: Callback for progress updates

        Returns:
            bool: True if successful, False otherwise
        """
        temp_audio = None
        temp_chunks = []

        try:
            # Step 1: Get image files
            self.log("📁 Collecting image files...")
            if progress_callback:
                progress_callback(0.1, "Collecting image files...")

            image_files = (
                [Path(path) for path in image_files]
                if image_files
                else self.get_image_files(image_folder)
            )

            if not image_files:
                self.log("❌ No image files found!", "ERROR")
                return False

            # Limit to MAX_MULTI_IMAGES
            if len(image_files) > MAX_MULTI_IMAGES:
                self.log(f"⚠️ Too many images ({len(image_files)}), using first {MAX_MULTI_IMAGES}", "WARNING")
                image_files = image_files[:MAX_MULTI_IMAGES]

            self.log(f"✅ Using {len(image_files)} images")

            # Step 2: Validate audio files
            self.log("🎵 Validating audio files...")
            if progress_callback:
                progress_callback(0.2, "Validating audio files...")

            if not audio_files:
                self.log("❌ No audio files provided!", "ERROR")
                return False

            # Limit to MAX_MULTI_AUDIO
            if len(audio_files) > MAX_MULTI_AUDIO:
                self.log(f"⚠️ Too many audio files ({len(audio_files)}), using first {MAX_MULTI_AUDIO}", "WARNING")
                audio_files = audio_files[:MAX_MULTI_AUDIO]

            self.log(f"✅ Using {len(audio_files)} audio files")

            # Step 3: Concatenate audio
            self.log("🎵 Concatenating audio...")
            if progress_callback:
                progress_callback(0.3, "Concatenating audio...")

            temp_audio = self.concatenate_audio(audio_files)
            if not temp_audio:
                self.log("❌ Audio concatenation failed!", "ERROR")
                return False

            # Step 4: Get total audio duration
            self.log("⏱️ Calculating total duration...")
            total_duration = self.get_audio_duration(temp_audio)
            self.log(f"ℹ️ Total audio duration: {total_duration/60:.1f} minutes")

            # Step 5: Calculate duration per image
            if len(image_files) == 0:
                self.log("❌ No image files found after validation!", "ERROR")
                return False

            duration_per_image = total_duration / len(image_files)
            self.log(f"ℹ️ Duration per image: {duration_per_image:.1f} seconds")

            # Step 6: Generate video
            self.log("🎬 Generating video with effects...")
            if progress_callback:
                progress_callback(0.5, "Generating video...")

            output_path = Path(output_file)

            # Use chunking strategy for large image counts
            if len(image_files) > IMAGES_PER_CHUNK:
                self.log(f"ℹ️ Using chunking strategy ({len(image_files)} images / {IMAGES_PER_CHUNK} per chunk)")
                success = self.generate_video_with_chunks(
                    image_files=image_files,
                    audio_file=temp_audio,
                    total_duration=total_duration,
                    duration_per_image=duration_per_image,
                    output_path=output_path,
                    rotation_mode=rotation_mode,
                    effect_type=effect_type,
                    transition_type=transition_type,
                    transition_duration=transition_duration,
                    resolution=resolution,
                    progress_callback=progress_callback,
                )
            else:
                success = self.generate_video_single_pass(
                    image_files=image_files,
                    audio_file=temp_audio,
                    total_duration=total_duration,
                    duration_per_image=duration_per_image,
                    output_path=output_path,
                    rotation_mode=rotation_mode,
                    effect_type=effect_type,
                    transition_type=transition_type,
                    transition_duration=transition_duration,
                    resolution=resolution,
                )

            if success:
                self.log("✅ Video generated successfully!", "SUCCESS")
                if progress_callback:
                    progress_callback(1.0, "Complete!")
            else:
                self.log("❌ Video generation failed!", "ERROR")

            return success

        except Exception as e:
            self.logger.log_user_friendly_error(e, "video generation")
            return False

        finally:
            # Cleanup temp files
            try:
                if temp_audio and temp_audio.exists():
                    temp_audio.unlink()
                    self.log("🗑️ Cleaned up temp audio file", "INFO")
            except Exception as e:
                self.log(f"⚠️ Could not delete temp audio: {e}", "WARNING")

            try:
                for chunk_file in temp_chunks:
                    if chunk_file.exists():
                        chunk_file.unlink()
                if temp_chunks:
                    self.log(f"🗑️ Cleaned up {len(temp_chunks)} chunk files", "INFO")
            except Exception as e:
                self.log(f"⚠️ Could not delete chunk files: {e}", "WARNING")

    def get_image_files(self, image_folder: str) -> List[Path]:
        """
        Get all image files from folder

        Args:
            image_folder: Path to image folder

        Returns:
            List of image file paths
        """
        folder = Path(image_folder)
        if not folder.exists():
            self.log(f"❌ Image folder not found: {image_folder}", "ERROR")
            return []

        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tiff"}
        return sorted((p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in image_extensions),
                      key=lambda p: p.name.lower())

    def concatenate_audio(self, audio_files: List[str]) -> Optional[Path]:
        output_file = self.output_folder / "concatenated_audio.m4a"
        try:
            if not audio_files:
                raise ValueError("At least one audio file is required.")
            cmd = ["ffmpeg"]
            filters = []
            for i, audio_file in enumerate(audio_files):
                cmd.extend(["-i", str(audio_file)])
                filters.append(f"[{i}:a:0]aresample=44100,"
                               f"aformat=sample_fmts=fltp:channel_layouts=stereo,"
                               f"asetpts=PTS-STARTPTS[a{i}]")
            inputs = "".join(f"[a{i}]" for i in range(len(audio_files)))
            filters.append(f"{inputs}concat=n={len(audio_files)}:v=0:a=1[audio]")
            cmd.extend(["-filter_complex", ";".join(filters), "-map", "[audio]",
                        "-c:a", "aac", "-b:a", DEFAULT_AUDIO_BITRATE, "-y", str(output_file)])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_AUDIO_CONCAT)
            if result.returncode:
                self.logger.log_ffmpeg_error(result.returncode, result.stderr, "mixer audio concatenation")
                return None
            return output_file if output_file.is_file() and output_file.stat().st_size else None
        except Exception as error:
            self.logger.log_user_friendly_error(error, "audio concatenation")
            return None

    def get_audio_duration(self, audio_file: Path) -> float:
        """
        Get duration of audio file in seconds

        Args:
            audio_file: Path to audio file

        Returns:
            Duration in seconds
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_file)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return duration
            else:
                self.log(f"⚠️ Could not get audio duration, using default", "WARNING")
                return 300.0  # 5 minutes default

        except Exception as e:
            self.log(f"⚠️ Error getting duration: {e}, using default", "WARNING")
            return 300.0

    def get_effect_for_image(
        self,
        index: int,
        effect_type: str,
        rotation_mode: str
    ) -> str:
        """
        Determine effect for specific image based on index and mode

        Args:
            index: Image index
            effect_type: Overall effect type setting
            rotation_mode: Rotation mode (sequential, random, mixed)

        Returns:
            Effect type for this image (zoom, pan, fade, none)
        """
        # If effect_type is specific, use that
        if effect_type in [EFFECT_TYPE_ZOOM, EFFECT_TYPE_PAN, EFFECT_TYPE_FADE, EFFECT_TYPE_NONE]:
            return effect_type

        # Otherwise, use rotation_mode to determine effect
        effects = [EFFECT_TYPE_ZOOM, EFFECT_TYPE_PAN, EFFECT_TYPE_FADE]

        if rotation_mode == ROTATION_MODE_SEQUENTIAL:
            # Cycle through effects in order
            return effects[index % len(effects)]

        elif rotation_mode == ROTATION_MODE_RANDOM:
            # Completely random
            return random.choice(effects)

        else:  # ROTATION_MODE_MIXED
            # Weighted random selection
            rand = random.random()
            if rand < EFFECT_WEIGHT_ZOOM:
                return EFFECT_TYPE_ZOOM
            elif rand < EFFECT_WEIGHT_ZOOM + EFFECT_WEIGHT_PAN:
                return EFFECT_TYPE_PAN
            else:
                return EFFECT_TYPE_FADE

    def get_pan_direction(self, index: int) -> str:
        """
        Get pan direction based on index (for sequential mode)

        Args:
            index: Image index

        Returns:
            Pan direction
        """
        directions = [
            PAN_DIRECTION_LEFT_TO_RIGHT,
            PAN_DIRECTION_RIGHT_TO_LEFT,
            PAN_DIRECTION_TOP_TO_BOTTOM,
            PAN_DIRECTION_BOTTOM_TO_TOP,
            PAN_DIRECTION_DIAGONAL
        ]
        return directions[index % len(directions)]

    def get_pan_expression(self, direction: str) -> str:
        """
        Get pan expression for FFmpeg zoompan filter

        Args:
            direction: Pan direction

        Returns:
            FFmpeg pan expression
        """
        expressions = {
            PAN_DIRECTION_LEFT_TO_RIGHT: "iw/zoom/2+(t/duration)*(iw/zoom)",
            PAN_DIRECTION_RIGHT_TO_LEFT: "iw-iw/zoom/2-(t/duration)*(iw/zoom)",
            PAN_DIRECTION_TOP_TO_BOTTOM: "ih/zoom/2+(t/duration)*(ih/zoom)",
            PAN_DIRECTION_BOTTOM_TO_TOP: "ih-ih/zoom/2-(t/duration)*(ih/zoom)",
            PAN_DIRECTION_DIAGONAL: "iw/zoom/2+(t/duration)*(iw/zoom)"
        }
        return expressions[direction]

    def generate_video_single_pass(
        self, image_files, audio_file, total_duration, duration_per_image,
        output_path, rotation_mode, effect_type, transition_type,
        transition_duration, resolution, audio_offset=0.0,
    ) -> bool:
        try:
            count = len(image_files)
            if not count or total_duration <= 0:
                raise ValueError("Images and a positive duration are required.")
            transition = (min(max(0.0, transition_duration), duration_per_image * 0.5)
                          if count > 1 and transition_type in
                          {TRANSITION_TYPE_CROSSFADE, TRANSITION_TYPE_FADE} else 0.0)
            # Overlap must be added back so transitions do not shorten the soundtrack.
            clip_duration = (total_duration + transition * (count - 1)) / count
            cmd = ["ffmpeg"]
            for image in image_files:
                cmd.extend(["-loop", "1", "-t", str(clip_duration), "-i", str(image)])
            cmd.extend(["-ss", str(audio_offset), "-i", str(audio_file)])
            filters = [
                self.apply_image_effect(i, self.get_effect_for_image(i, effect_type, rotation_mode),
                                        clip_duration, resolution)
                for i in range(count)
            ]
            if transition:
                current = "v0"
                transition_name = "smoothleft" if transition_type == TRANSITION_TYPE_CROSSFADE else "fade"
                for i in range(1, count):
                    next_label = "visual" if i == count - 1 else f"merged{i}"
                    offset = (clip_duration - transition) * i
                    filters.append(f"[{current}][v{i}]xfade=transition={transition_name}:"
                                   f"duration={transition}:offset={offset}[{next_label}]")
                    current = next_label
            else:
                inputs = "".join(f"[v{i}]" for i in range(count))
                filters.append(f"{inputs}concat=n={count}:v=1:a=0[visual]")
            filters.append(f"[{count}:a]atrim=duration={total_duration},asetpts=PTS-STARTPTS[audio]")
            cmd.extend([
                "-filter_complex", ";".join(filters),
                "-map", "[visual]", "-map", "[audio]", "-t", str(total_duration),
                "-c:v", "libx264", "-preset", VIDEO_PRESET_DEFAULT,
                "-crf", str(VIDEO_CRF_DEFAULT), "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", DEFAULT_AUDIO_BITRATE, "-shortest", "-y", str(output_path),
            ])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_VIDEO_RENDER)
            if result.returncode:
                self.logger.log_ffmpeg_error(result.returncode, result.stderr, "image mixer")
                return False
            return output_path.is_file() and output_path.stat().st_size > 0
        except Exception as error:
            self.logger.log_user_friendly_error(error, "single-pass video generation")
            return False

    def generate_video_with_chunks(
        self,
        image_files: List[Path],
        audio_file: Path,
        total_duration: float,
        duration_per_image: float,
        output_path: Path,
        rotation_mode: str,
        effect_type: str,
        transition_type: str,
        transition_duration: float,
        resolution: str,
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """
        Generate video using chunking strategy (for > IMAGES_PER_CHUNK)

        Args:
            image_files: List of image file paths
            audio_file: Concatenated audio file
            total_duration: Total audio duration
            duration_per_image: Duration per image
            output_path: Output video path
            rotation_mode: Rotation mode
            effect_type: Effect type
            transition_type: Transition type
            transition_duration: Transition duration
            resolution: Output resolution
            progress_callback: Progress callback

        Returns:
            bool: True if successful
        """
        temp_chunks = []

        try:
            # Split images into chunks
            chunks = []
            for i in range(0, len(image_files), IMAGES_PER_CHUNK):
                chunk = image_files[i:i + IMAGES_PER_CHUNK]
                chunks.append(chunk)

            self.log(f"ℹ️ Split into {len(chunks)} chunks")

            # Generate each chunk
            chunk_files = []
            for i, chunk in enumerate(chunks):
                self.log(f"🎬 Generating chunk {i+1}/{len(chunks)} ({len(chunk)} images)...")
                
                if progress_callback:
                    progress_callback(
                        0.5 + (0.4 * (i / len(chunks))),
                        f"Generating chunk {i+1}/{len(chunks)}..."
                    )

                chunk_duration = duration_per_image * len(chunk)
                
                # Generate chunk video
                chunk_file = self.output_folder / f"chunk_{i:03d}.mp4"
                
                success = self.generate_video_single_pass(
                    image_files=chunk,
                    audio_file=audio_file,
                    total_duration=chunk_duration,
                    audio_offset=i * IMAGES_PER_CHUNK * duration_per_image,
                    duration_per_image=duration_per_image,
                    output_path=chunk_file,
                    rotation_mode=rotation_mode,
                    effect_type=effect_type,
                    transition_type=transition_type,
                    transition_duration=transition_duration,
                    resolution=resolution,
                )

                if not success:
                    self.log(f"❌ Chunk {i+1} generation failed!", "ERROR")
                    return False

                chunk_files.append(chunk_file)
                temp_chunks.append(chunk_file)

            # Concatenate all chunks
            self.log(f"🎞️ Concatenating {len(chunk_files)} chunks...")
            if progress_callback:
                progress_callback(0.9, "Concatenating chunks...")

            success = self.concatenate_video_chunks(chunk_files, output_path, audio_file)

            if success:
                self.log("✅ Video generated successfully with chunking!", "SUCCESS")
            else:
                self.log("❌ Chunk concatenation failed!", "ERROR")

            return success

        except Exception as e:
            self.logger.log_user_friendly_error(e, "chunked video generation")
            return False

    def concatenate_video_chunks(
        self,
        chunk_files: List[Path],
        output_path: Path,
        audio_file: Optional[Path] = None,
    ) -> bool:
        """
        Concatenate video chunks into final output

        Args:
            chunk_files: List of chunk video files
            output_path: Final output path

        Returns:
            bool: True if successful
        """
        try:
            # Create concat list
            list_file = self.output_folder / "video_concat_list.txt"
            
            with open(list_file, 'w', encoding='utf-8') as f:
                for chunk_file in chunk_files:
                    chunk_path = chunk_file.resolve().as_posix()
                    escaped_path = chunk_path.replace("'", "'\\''").replace("\\", "\\\\")
                    f.write(f"file '{escaped_path}'\n")

            # Concatenate using ffmpeg
            cmd = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
                "-y",
                str(output_path)
            ]

            if audio_file is not None:
                cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(list_file),
                       "-i", str(audio_file), "-map", "0:v:0", "-map", "1:a:0",
                       "-c:v", "copy", "-c:a", "aac", "-b:a", DEFAULT_AUDIO_BITRATE,
                       "-shortest", "-y", str(output_path)]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_VIDEO_RENDER
            )

            if result.returncode != 0:
                self.log(f"❌ FFmpeg concat error: {result.stderr}", "ERROR")
                return False

            if not output_path.exists():
                self.log("❌ Final output not created!", "ERROR")
                return False

            return True

        except Exception as e:
            self.logger.log_user_friendly_error(e, "video concatenation")
            return False

    def apply_image_effect(self, index, effect, duration, resolution) -> str:
        width, height = resolution.split("x")
        chain = (
            f"[{index}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1"
        )
        if effect == EFFECT_TYPE_ZOOM:
            speed = 0.0005 + index * 0.00001
            maximum = 1.3 + (index % 5) * 0.05
            chain += f",zoompan=z='min(1+on*{speed},{maximum})':d=1:s={resolution}:fps=25"
        elif effect == EFFECT_TYPE_PAN:
            direction = self.get_pan_direction(index)
            progress = f"min(on/{max(1, round(duration * 25) - 1)},1)"
            x = "(iw-iw/zoom)/2"
            y = "(ih-ih/zoom)/2"
            if direction in {PAN_DIRECTION_LEFT_TO_RIGHT, PAN_DIRECTION_DIAGONAL}:
                x = f"{progress}*(iw-iw/zoom)"
            elif direction == PAN_DIRECTION_RIGHT_TO_LEFT:
                x = f"(1-{progress})*(iw-iw/zoom)"
            if direction in {PAN_DIRECTION_TOP_TO_BOTTOM, PAN_DIRECTION_DIAGONAL}:
                y = f"{progress}*(ih-ih/zoom)"
            elif direction == PAN_DIRECTION_BOTTOM_TO_TOP:
                y = f"(1-{progress})*(ih-ih/zoom)"
            chain += f",zoompan=z=1.15:x='{x}':y='{y}':d=1:s={resolution}:fps=25"
        elif effect == EFFECT_TYPE_FADE:
            fade = min(1.0, duration / 2)
            chain += f",fade=t=in:st=0:d={fade},fade=t=out:st={duration-fade}:d={fade}"
        return chain + f",fps=25,format=yuv420p,settb=AVTB,setpts=PTS-STARTPTS[v{index}]"
