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
                video_path, crossfade_duration, use_gpu, progress_callback, cancel_event
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

                final_video = self.scale_video(looped_video, resolution, use_gpu, progress_callback, cancel_event)

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
                final_video, output_file, use_gpu, cpu_preset, cpu_crf, cpu_threads, progress_callback, cancel_event
            )

            # Cleanup temp files
            self._cleanup_temp_files()

            if success:
                self.log(f"✅ Loop created successfully: {output_file.name}", "SUCCESS")

                # Send desktop notification
                try:
                    from utils.notifications import notify_success
                    notify_success(
                        "Loop Created Successfully",
                        f"Video loop saved: {output_file.name}"
                    )
                except:
                    pass  # Ignore notification errors

                if progress_callback:
                    progress_callback(1.0, "Complete!")
                return True
            else:
                self.log("❌ Rendering failed!", "ERROR")

                # Send error notification
                try:
                    from utils.notifications import notify_error
                    notify_error("Loop Creation Failed", "Failed to render video loop")
                except:
                    pass

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

    def create_crossfade_clip(self, video_path, crossfade_duration, use_gpu=False, progress_callback=None, cancel_event=None):
        """
        Create a seamless looping video with crossfade transition

        This creates a seamless loop by:
        1. Taking the main video MINUS crossfade duration (to avoid overlap)
        2. Creating a crossfaded section that blends the end with the beginning
        3. Appending the crossfaded section to replace the removed end

        Example: 10 second video with 1 second crossfade
        - Main part: 0-9 seconds (9 seconds)
        - Crossfade: blend 9-10s (end) with 0-1s (start) = 1 second
        - Result: 9s + 1s = 10s seamless loop

        Args:
            video_path: Path to input video
            crossfade_duration: Duration of crossfade in seconds
            use_gpu: Whether to use GPU (not used for crossfade)
            progress_callback: Callback for progress updates
            cancel_event: Event for cancellation

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

            # Calculate trim point for seamless loop
            trim_point = duration - crossfade_duration

            # CORRECT crossfade approach for seamless looping:
            # 1. Main part: 0 to (duration - crossfade_duration)
            # 2. End part: (duration - crossfade_duration) to duration
            # 3. Start part: 0 to crossfade_duration
            # 4. Crossfade end with start
            # 5. Concatenate trimmed main with crossfaded section
            cmd = [
                "ffmpeg",
                "-i", str(video_path),
                "-i", str(video_path),
                "-filter_complex",
                # Trim main video to remove the end (which will be replaced by crossfade)
                f"[0:v]trim=0:{trim_point},setpts=PTS-STARTPTS[main];"
                # Get the end section for crossfade
                f"[1:v]trim={trim_point}:{duration},setpts=PTS-STARTPTS[end];"
                # Get the start section for crossfade
                f"[1:v]trim=0:{crossfade_duration},setpts=PTS-STARTPTS[start];"
                # Crossfade end with start - this creates the seamless transition
                f"[end][start]xfade=transition=fade:duration={crossfade_duration}:offset=0[faded];"
                # Concatenate: trimmed main + crossfaded section = same duration, seamless loop
                f"[main][faded]concat=n=2:v=1:a=0[outv]",
                "-map", "[outv]",
                "-map", "0:a?",
                "-c:a", "copy",
                "-y",
                str(temp_output)
            ]

            self.log(f"🔄 Creating seamless crossfade: {crossfade_duration:.1f}s transition at {trim_point:.1f}s")

            # Use progress parser for real-time progress
            from utils.ffmpeg_progress import run_ffmpeg_with_progress

            def progress_wrapper(percentage, message, eta):
                if progress_callback:
                    # Map to 0.3-0.4 range (crossfade is 10% of total work)
                    mapped_progress = 0.3 + (percentage * 0.1)
                    progress_callback(mapped_progress, f"Creating crossfade... {message}")

            success = run_ffmpeg_with_progress(
                cmd,
                total_duration=duration,
                progress_callback=progress_wrapper,
                cancel_event=cancel_event,
                log_callback=self.log
            )

            if not success:
                self.log(f"❌ Crossfade creation failed", "ERROR")
                return video_path

            return temp_output

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

    def scale_video(self, video_path, resolution, use_gpu=False, progress_callback=None, cancel_event=None):
        """
        Scale video to target resolution

        Args:
            video_path: Path to input video
            resolution: Target resolution (e.g., "1920x1080")
            use_gpu: Whether to use GPU acceleration
            progress_callback: Callback for progress updates
            cancel_event: Event for cancellation

        Returns:
            Path: Path to scaled video (temp file)
        """
        video_path = Path(video_path)

        if resolution == "Original":
            return video_path

        try:
            # Parse resolution
            width, height = map(int, resolution.split("x"))

            # Get video duration for progress tracking
            video_info = self.get_video_info(video_path)
            duration = video_info["duration"]

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

            # Use progress parser for real-time progress
            from utils.ffmpeg_progress import run_ffmpeg_with_progress

            def progress_wrapper(percentage, message, eta):
                if progress_callback:
                    # Map to 0.7-0.8 range (scaling is 10% of total work)
                    mapped_progress = 0.7 + (percentage * 0.1)
                    progress_callback(mapped_progress, f"Scaling video... {message}")

            success = run_ffmpeg_with_progress(
                cmd,
                total_duration=duration,
                progress_callback=progress_wrapper,
                cancel_event=cancel_event,
                log_callback=self.log
            )

            if not success:
                self.log(f"❌ Scaling failed", "ERROR")
                return video_path

            return temp_output

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
        self, input_path, output_path, use_gpu=False, cpu_preset="medium", cpu_crf=23, cpu_threads="auto", progress_callback=None, cancel_event=None
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
            progress_callback: Callback for progress updates
            cancel_event: Event for cancellation

        Returns:
            bool: True if successful
        """
        try:
            # Get video info
            video_info = self.get_video_info(input_path)
            duration = video_info["duration"]

            # Build FFmpeg command manually for progress tracking
            cmd = [
                "ffmpeg",
                "-i", str(input_path),
            ]

            # Video codec settings
            if use_gpu:
                # NVIDIA GPU acceleration
                cmd.extend([
                    "-c:v", "h264_nvenc",
                    "-preset", "medium",
                    "-b:v", "8M",
                ])
                self.log("⚡ Using GPU acceleration (NVIDIA)")
            else:
                # CPU encoding with user-defined settings
                cmd.extend([
                    "-c:v", "libx264",
                    "-preset", cpu_preset,
                    "-crf", str(cpu_crf),
                ])

                # Add threads if not auto
                if cpu_threads != "auto":
                    cmd.extend(["-threads", cpu_threads])

                self.log(f"💻 Using CPU encoding (preset={cpu_preset}, crf={cpu_crf}, threads={cpu_threads})")

            # Audio codec
            cmd.extend([
                "-c:a", "aac",
                "-b:a", "192k",
                "-y",
                str(output_path)
            ])

            # Use progress parser for real-time progress
            from utils.ffmpeg_progress import run_ffmpeg_with_progress

            def progress_wrapper(percentage, message, eta):
                if progress_callback:
                    # Map to 0.9-1.0 range (final render is last 10% of total work)
                    mapped_progress = 0.9 + (percentage * 0.1)
                    progress_callback(mapped_progress, f"Rendering final video... {message}")

            success = run_ffmpeg_with_progress(
                cmd,
                total_duration=duration,
                progress_callback=progress_wrapper,
                cancel_event=cancel_event,
                log_callback=self.log
            )

            if not success:
                return False

            return output_path.exists()

        except Exception as e:
            self.log(f"Render error: {str(e)}", "ERROR")
            return False
