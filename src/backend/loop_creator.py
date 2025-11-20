"""
Loop Creator Backend with Crossfade
Create seamless video loops from short clips
"""

import ffmpeg
import subprocess
from pathlib import Path
from datetime import datetime
import math


class LoopCreator:
    """Create seamless video loops with crossfade transitions"""

    def __init__(self, output_folder, console_log=None):
        """
        Initialize loop creator

        Args:
            output_folder: Path to output folder
            console_log: Console log widget for logging
        """
        self.output_folder = Path(output_folder)
        self.console_log = console_log

        # Create output folder if it doesn't exist
        self.output_folder.mkdir(parents=True, exist_ok=True)

    def log(self, message, level="INFO"):
        """Log a message"""
        if self.console_log:
            if level == "ERROR":
                self.console_log.log_error(message)
            elif level == "WARNING":
                self.console_log.log_warning(message)
            elif level == "SUCCESS":
                self.console_log.log_success(message)
            else:
                self.console_log.log_info(message)
        else:
            print(f"[{level}] {message}")

    def create_loop(
        self,
        video_path,
        target_duration,
        crossfade_duration=1.0,
        resolution="Original",
        audio_path=None,
        use_gpu=False,
        cpu_preset="medium",
        cpu_crf=23,
        cpu_threads="auto",
        progress_callback=None,
        cancel_event=None,
    ):
        """
        Create a seamless loop from a video

        Args:
            video_path: Path to input video
            target_duration: Target duration in seconds
            crossfade_duration: Crossfade duration in seconds
            resolution: Output resolution (e.g., "1920x1080" or "Original")
            audio_path: Optional audio file to replace video audio
            use_gpu: Whether to use GPU acceleration
            cpu_preset: CPU encoding preset (ultrafast to slow)
            cpu_crf: CPU quality (18=best, 23=good, 28=faster)
            cpu_threads: Number of CPU threads to use
            progress_callback: Callback for progress updates

        Returns:
            bool: True if successful, False otherwise
        """
        video_path = Path(video_path)

        try:
            # Step 1: Get video info
            self.log("📊 Analyzing video...")
            if progress_callback:
                progress_callback(0.1, "Analyzing video...")

            video_info = self.get_video_info(video_path)
            source_duration = video_info["duration"]
            source_fps = video_info["fps"]

            self.log(f"ℹ️  Video duration: {source_duration:.2f}s, FPS: {source_fps}")

            # Step 2: Calculate number of loops needed
            loops_needed = math.ceil(target_duration / source_duration)
            self.log(f"🔄 Will create {loops_needed} loops to reach {target_duration}s")

            # Step 3: Create crossfade video
            if cancel_event and cancel_event.is_set():
                self.log("🛑 Render cancelled by user", "WARNING")
                return False

            self.log("🎬 Creating crossfade transition...")
            if progress_callback:
                progress_callback(0.3, "Creating crossfade...")

            crossfade_video = self.create_crossfade_clip(
                video_path, crossfade_duration, use_gpu
            )

            # Step 4: Create loop by concatenating
            if cancel_event and cancel_event.is_set():
                self.log("🛑 Render cancelled by user", "WARNING")
                self._cleanup_temp_files()
                return False

            self.log(f"🔁 Looping video {loops_needed} times...")
            if progress_callback:
                progress_callback(0.5, "Looping video...")

            looped_video = self.concatenate_loops(
                crossfade_video, loops_needed, target_duration, use_gpu
            )

            # Step 5: Scale if needed
            if cancel_event and cancel_event.is_set():
                self.log("🛑 Render cancelled by user", "WARNING")
                self._cleanup_temp_files()
                return False

            final_video = looped_video
            if resolution != "Original":
                self.log(f"📐 Scaling to {resolution}...")
                if progress_callback:
                    progress_callback(0.7, "Scaling video...")

                final_video = self.scale_video(looped_video, resolution, use_gpu)

            # Step 6: Add audio if provided
            if cancel_event and cancel_event.is_set():
                self.log("🛑 Render cancelled by user", "WARNING")
                self._cleanup_temp_files()
                return False

            if audio_path:
                self.log("🎵 Adding custom audio...")
                if progress_callback:
                    progress_callback(0.85, "Adding audio...")

                final_video = self.add_audio(final_video, audio_path, target_duration)

            # Step 7: Generate output filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = (
                self.output_folder
                / f"loop_{video_path.stem}_{target_duration}s_{timestamp}.mp4"
            )

            # Step 8: Render final video
            self.log("🎬 Rendering final video...")
            if progress_callback:
                progress_callback(0.9, "Rendering...")

            success = self.render_final(
                final_video, output_file, use_gpu, cpu_preset, cpu_crf, cpu_threads
            )

            # Cleanup temp files
            self._cleanup_temp_files()

            if success:
                self.log(f"✅ Loop created successfully: {output_file.name}", "SUCCESS")
                if progress_callback:
                    progress_callback(1.0, "Complete!")
                return True
            else:
                self.log("❌ Rendering failed!", "ERROR")
                return False

        except Exception as e:
            self.log(f"❌ Error creating loop: {str(e)}", "ERROR")
            # Cleanup temp files on error
            self._cleanup_temp_files()
            return False

    def get_video_info(self, video_path):
        """Get video information using ffprobe"""
        try:
            probe = ffmpeg.probe(str(video_path))

            video_stream = next(
                (s for s in probe["streams"] if s["codec_type"] == "video"), None
            )

            if not video_stream:
                raise ValueError("No video stream found")

            # Get duration
            duration = float(video_stream.get("duration", probe["format"]["duration"]))

            # Get FPS
            fps_str = video_stream.get("r_frame_rate", "30/1")
            fps_num, fps_den = map(int, fps_str.split("/"))
            fps = fps_num / fps_den if fps_den != 0 else 30

            # Get resolution
            width = int(video_stream["width"])
            height = int(video_stream["height"])

            return {
                "duration": duration,
                "fps": fps,
                "width": width,
                "height": height,
            }

        except Exception as e:
            raise ValueError(f"Failed to get video info: {str(e)}")

    def create_crossfade_clip(self, video_path, crossfade_duration, use_gpu=False):
        """
        Create a video clip with crossfade at the end

        This creates a seamless loop by:
        1. Taking the last N seconds of video
        2. Crossfading it with the first N seconds
        3. Appending this to the original video

        Args:
            video_path: Path to input video
            crossfade_duration: Duration of crossfade in seconds
            use_gpu: Whether to use GPU (not used for crossfade)

        Returns:
            Path: Path to crossfaded video (temp file)
        """
        video_path = Path(video_path)

        try:
            # Get video info
            video_info = self.get_video_info(video_path)
            duration = video_info["duration"]

            # Crossfade duration shouldn't be more than half the video
            if crossfade_duration > duration / 2:
                crossfade_duration = duration / 2
                self.log(f"⚠️  Crossfade duration adjusted to {crossfade_duration:.1f}s", "WARNING")

            # Create temp output path
            temp_output = self.output_folder / f"temp_crossfade_{video_path.name}"

            # Use FFmpeg to create crossfade
            # We'll use xfade filter to blend the end and beginning
            cmd = [
                "ffmpeg",
                "-i", str(video_path),
                "-i", str(video_path),
                "-filter_complex",
                f"[0:v]trim=0:{duration},setpts=PTS-STARTPTS[main];"
                f"[1:v]trim={duration - crossfade_duration}:{duration},setpts=PTS-STARTPTS[end];"
                f"[1:v]trim=0:{crossfade_duration},setpts=PTS-STARTPTS[start];"
                f"[end][start]xfade=transition=fade:duration={crossfade_duration}:offset=0[faded];"
                f"[main][faded]concat=n=2:v=1:a=0[outv]",
                "-map", "[outv]",
                "-map", "0:a?",
                "-c:a", "copy",
                "-y",
                str(temp_output)
            ]

            subprocess.run(cmd, check=True, capture_output=True, text=True)

            return temp_output

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            self.log(f"❌ Crossfade creation failed: {error_msg}", "ERROR")
            # Fall back to original video
            return video_path

        except Exception as e:
            self.log(f"❌ Error creating crossfade: {str(e)}", "ERROR")
            return video_path

    def concatenate_loops(self, video_path, loops, target_duration, use_gpu=False):
        """
        Concatenate video multiple times to reach target duration

        Args:
            video_path: Path to video to loop
            loops: Number of times to loop
            target_duration: Target duration in seconds
            use_gpu: Whether to use GPU (not applicable for concat)

        Returns:
            Path: Path to looped video (temp file)
        """
        video_path = Path(video_path)

        try:
            # Get video duration
            video_info = self.get_video_info(video_path)
            duration = video_info["duration"]

            # Create concat file list
            concat_list = self.output_folder / "concat_list.txt"

            with open(concat_list, "w") as f:
                for i in range(loops):
                    f.write(f"file '{video_path.absolute()}'\n")

            # Create temp output
            temp_output = self.output_folder / f"temp_looped_{video_path.name}"

            # Use FFmpeg concat demuxer
            cmd = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list),
                "-c", "copy",
                "-t", str(target_duration),  # Trim to exact target duration
                "-y",
                str(temp_output)
            ]

            subprocess.run(cmd, check=True, capture_output=True, text=True)

            # Cleanup concat list
            if concat_list.exists():
                concat_list.unlink()

            return temp_output

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            self.log(f"❌ Loop concatenation failed: {error_msg}", "ERROR")
            return video_path

        except Exception as e:
            self.log(f"❌ Error concatenating loops: {str(e)}", "ERROR")
            # Cleanup
            if concat_list and concat_list.exists():
                concat_list.unlink()
            return video_path

    def scale_video(self, video_path, resolution, use_gpu=False):
        """
        Scale video to target resolution

        Args:
            video_path: Path to input video
            resolution: Target resolution (e.g., "1920x1080")
            use_gpu: Whether to use GPU acceleration

        Returns:
            Path: Path to scaled video (temp file)
        """
        video_path = Path(video_path)

        if resolution == "Original":
            return video_path

        try:
            # Parse resolution
            width, height = map(int, resolution.split("x"))

            # Create temp output
            temp_output = self.output_folder / f"temp_scaled_{video_path.name}"

            # Build scale filter
            if use_gpu:
                # GPU scaling (CUDA)
                scale_filter = f"scale_cuda={width}:{height}"
            else:
                # CPU scaling with proper aspect ratio handling
                scale_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"

            # Use FFmpeg to scale
            cmd = [
                "ffmpeg",
                "-i", str(video_path),
                "-vf", scale_filter,
                "-c:a", "copy",
                "-y",
                str(temp_output)
            ]

            subprocess.run(cmd, check=True, capture_output=True, text=True)

            return temp_output

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            self.log(f"❌ Scaling failed: {error_msg}", "ERROR")
            return video_path

        except Exception as e:
            self.log(f"❌ Error scaling video: {str(e)}", "ERROR")
            return video_path

    def add_audio(self, video_path, audio_path, duration):
        """
        Add or replace audio track

        Args:
            video_path: Path to video file
            audio_path: Path to audio file to add
            duration: Target duration (trim/loop audio to match)

        Returns:
            Path: Path to video with new audio (temp file)
        """
        video_path = Path(video_path)
        audio_path = Path(audio_path)

        try:
            # Create temp output
            temp_output = self.output_folder / f"temp_audio_{video_path.name}"

            # Get audio duration
            audio_info = self.get_audio_duration(audio_path)

            # Build audio filter
            if audio_info < duration:
                # Loop audio if too short
                loops_needed = int(duration / audio_info) + 1
                audio_filter = f"aloop=loop={loops_needed}:size=2e+09,atrim=duration={duration}"
            else:
                # Trim audio if too long
                audio_filter = f"atrim=duration={duration}"

            # Use FFmpeg to replace audio
            cmd = [
                "ffmpeg",
                "-i", str(video_path),
                "-i", str(audio_path),
                "-filter_complex", f"[1:a]{audio_filter}[aout]",
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                "-y",
                str(temp_output)
            ]

            subprocess.run(cmd, check=True, capture_output=True, text=True)

            return temp_output

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            self.log(f"❌ Audio replacement failed: {error_msg}", "ERROR")
            return video_path

        except Exception as e:
            self.log(f"❌ Error adding audio: {str(e)}", "ERROR")
            return video_path

    def get_audio_duration(self, audio_path):
        """Get duration of audio file in seconds"""
        try:
            probe = ffmpeg.probe(str(audio_path))
            duration = float(probe["format"]["duration"])
            return duration
        except:
            return 0

    def _cleanup_temp_files(self):
        """Cleanup temporary files created during processing"""
        try:
            # List of temp file patterns
            temp_patterns = [
                "temp_crossfade_*",
                "temp_looped_*",
                "temp_scaled_*",
                "temp_audio_*",
                "concat_list.txt",
            ]

            for pattern in temp_patterns:
                for temp_file in self.output_folder.glob(pattern):
                    try:
                        temp_file.unlink()
                        self.log(f"🗑️  Cleaned up: {temp_file.name}", "INFO")
                    except Exception as e:
                        pass  # Ignore cleanup errors

        except Exception as e:
            pass  # Ignore all cleanup errors

    def render_final(
        self, input_path, output_path, use_gpu=False, cpu_preset="medium", cpu_crf=23, cpu_threads="auto"
    ):
        """
        Render final video

        Args:
            input_path: Input video path
            output_path: Output video path
            use_gpu: Whether to use GPU acceleration
            cpu_preset: CPU encoding preset (only used if GPU is disabled)
            cpu_crf: CPU quality setting (only used if GPU is disabled)
            cpu_threads: Number of CPU threads (only used if GPU is disabled)

        Returns:
            bool: True if successful
        """
        try:
            # Get video info
            video_info = self.get_video_info(input_path)

            # Build FFmpeg command
            input_stream = ffmpeg.input(str(input_path))

            # Video codec settings
            if use_gpu:
                # NVIDIA GPU acceleration
                video_codec = "h264_nvenc"
                codec_params = {
                    "preset": "medium",
                    "b:v": "8M",
                }
                self.log("⚡ Using GPU acceleration (NVIDIA)")
            else:
                # CPU encoding with user-defined settings
                video_codec = "libx264"
                codec_params = {
                    "preset": cpu_preset,
                    "crf": str(cpu_crf),
                }

                # Add threads if not auto
                if cpu_threads != "auto":
                    codec_params["threads"] = cpu_threads

                self.log(f"💻 Using CPU encoding (preset={cpu_preset}, crf={cpu_crf}, threads={cpu_threads})")

            # Output settings
            output_stream = ffmpeg.output(
                input_stream,
                str(output_path),
                vcodec=video_codec,
                acodec="aac",
                audio_bitrate="192k",
                **codec_params,
            )

            # Run FFmpeg
            ffmpeg.run(output_stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)

            return output_path.exists()

        except ffmpeg.Error as e:
            error_message = e.stderr.decode() if e.stderr else str(e)
            self.log(f"FFmpeg error: {error_message}", "ERROR")
            return False
        except Exception as e:
            self.log(f"Render error: {str(e)}", "ERROR")
            return False
