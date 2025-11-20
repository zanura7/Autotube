"""
Video Generator Backend
Combine audio playlist with visual (video/image) to create final YouTube video
"""

import ffmpeg
import subprocess
from pathlib import Path
from datetime import datetime
import json


class VideoGenerator:
    """Generate final YouTube video from audio playlist and visual"""

    def __init__(self, output_folder, console_log=None):
        """
        Initialize video generator

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

    def generate_video(
        self,
        playlist_path=None,
        audio_folder=None,
        visual_path=None,
        resolution="1920x1080",
        generate_chapters=True,
        apply_zoom=True,
        progress_callback=None,
    ):
        """
        Generate final video

        Args:
            playlist_path: Path to M3U playlist (optional)
            audio_folder: Path to audio folder (optional)
            visual_path: Path to visual (video or image)
            resolution: Output resolution
            generate_chapters: Whether to generate chapter metadata
            apply_zoom: Whether to apply zoom effect (for images)
            progress_callback: Callback for progress updates

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Step 1: Get audio files
            self.log("📋 Collecting audio files...")
            if progress_callback:
                progress_callback(0.1, "Collecting audio files...")

            audio_files = self.get_audio_files(playlist_path, audio_folder)

            if not audio_files:
                self.log("❌ No audio files found!", "ERROR")
                return False

            self.log(f"✅ Found {len(audio_files)} audio files")

            # Step 2: Calculate total duration and create chapter metadata
            self.log("⏱️  Calculating duration...")
            if progress_callback:
                progress_callback(0.2, "Calculating duration...")

            chapters = self.create_chapters(audio_files)
            total_duration = chapters[-1]["end_time"] if chapters else 0

            self.log(f"ℹ️  Total duration: {total_duration:.2f}s ({total_duration / 60:.2f} min)")

            # Step 3: Concatenate audio files
            self.log("🎵 Concatenating audio...")
            if progress_callback:
                progress_callback(0.4, "Concatenating audio...")

            temp_audio = self.concatenate_audio(audio_files)

            # Check if audio concatenation succeeded
            if not temp_audio or not temp_audio.exists():
                self.log("❌ Failed to concatenate audio files!", "ERROR")
                try:
                    from utils.notifications import notify_error
                    notify_error("Video Generation Failed", "Failed to concatenate audio files")
                except:
                    pass
                return False

            # Step 4: Prepare visual
            self.log("🖼️  Preparing visual...")
            if progress_callback:
                progress_callback(0.6, "Preparing visual...")

            visual_path = Path(visual_path)

            # Validate visual file exists
            if not visual_path.exists():
                self.log(f"❌ Visual file not found: {visual_path}", "ERROR")
                try:
                    from utils.notifications import notify_error
                    notify_error("Video Generation Failed", f"Visual file not found: {visual_path.name}")
                except:
                    pass
                return False

            is_image = visual_path.suffix.lower() in [".png", ".jpg", ".jpeg"]

            # Step 5: Generate output filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_folder / f"final_video_{timestamp}.mp4"

            # Step 6: Render final video
            self.log("🎬 Rendering final video...")
            if progress_callback:
                progress_callback(0.8, "Rendering final video...")

            success = self.render_video(
                audio_path=temp_audio,
                visual_path=visual_path,
                output_path=output_file,
                duration=total_duration,
                resolution=resolution,
                is_image=is_image,
                apply_zoom=apply_zoom and is_image,
            )

            if not success:
                self.log("❌ Rendering failed!", "ERROR")
                return False

            # Step 7: Generate chapter file if requested
            if generate_chapters and chapters:
                self.log("📖 Generating chapter file...")
                chapter_file = self.save_chapters(chapters, output_file)
                if chapter_file:
                    self.log(f"✅ Chapter file created: {chapter_file.name}", "SUCCESS")

            # Cleanup temp audio
            try:
                if temp_audio and temp_audio.exists():
                    temp_audio.unlink()
            except Exception as e:
                self.log(f"⚠️  Warning: Could not delete temp file: {e}", "WARNING")

            self.log(f"✅ Video created successfully: {output_file.name}", "SUCCESS")

            # Send desktop notification
            try:
                from utils.notifications import notify_success
                notify_success(
                    "Video Created Successfully",
                    f"Final video saved: {output_file.name}"
                )
            except:
                pass  # Ignore notification errors

            if progress_callback:
                progress_callback(1.0, "Complete!")

            return True

        except Exception as e:
            self.log(f"❌ Error generating video: {str(e)}", "ERROR")

            # Send error notification
            try:
                from utils.notifications import notify_error
                notify_error("Video Generation Failed", str(e))
            except:
                pass

            # Cleanup temp files on error
            try:
                if temp_audio and temp_audio.exists():
                    temp_audio.unlink()
                list_file = self.output_folder / "audio_list.txt"
                if list_file.exists():
                    list_file.unlink()
            except:
                pass

            return False

    def get_audio_files(self, playlist_path=None, audio_folder=None):
        """Get list of audio files from playlist or folder"""
        audio_files = []

        if playlist_path:
            # Read M3U playlist
            playlist_path = Path(playlist_path)
            playlist_dir = playlist_path.parent

            with open(playlist_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Handle relative paths
                        audio_path = playlist_dir / line
                        if audio_path.exists():
                            audio_files.append(audio_path)

        elif audio_folder:
            # Scan folder for audio files
            audio_folder = Path(audio_folder)
            audio_extensions = [".mp3", ".m4a", ".wav", ".aac"]

            for ext in audio_extensions:
                audio_files.extend(audio_folder.glob(f"*{ext}"))

            # Sort by name
            audio_files.sort()

        return audio_files

    def create_chapters(self, audio_files):
        """
        Create chapter metadata from audio files

        Args:
            audio_files: List of audio file paths

        Returns:
            list: List of chapter dicts with title, start_time, end_time
        """
        chapters = []
        current_time = 0.0

        for audio_file in audio_files:
            # Get duration
            duration = self.get_audio_duration(audio_file)

            if duration:
                chapter = {
                    "title": audio_file.stem,
                    "start_time": current_time,
                    "end_time": current_time + duration,
                }
                chapters.append(chapter)
                current_time += duration

        return chapters

    def get_audio_duration(self, audio_path):
        """Get audio duration in seconds"""
        try:
            probe = ffmpeg.probe(str(audio_path))
            duration = float(probe["format"]["duration"])
            return duration
        except Exception as e:
            self.log(f"⚠️  Warning: Could not get duration for {audio_path.name}", "WARNING")
            return None

    def concatenate_audio(self, audio_files):
        """
        Concatenate multiple audio files into one

        Args:
            audio_files: List of audio file paths

        Returns:
            Path: Path to concatenated audio file
        """
        # Use M4A format to avoid issues with MP3 + album art
        temp_audio = self.output_folder / "temp_audio.m4a"

        try:
            # Create file list for concat
            list_file = self.output_folder / "audio_list.txt"

            with open(list_file, "w", encoding="utf-8") as f:
                for audio_file in audio_files:
                    # Use absolute path with proper escaping for Windows
                    # Convert backslashes to forward slashes for FFmpeg compatibility
                    abs_path = str(audio_file.absolute()).replace('\\', '/')
                    # Escape single quotes in filename
                    abs_path = abs_path.replace("'", "'\\''")
                    f.write(f"file '{abs_path}'\n")

            self.log(f"📝 Created concat list: {list_file}")
            self.log(f"📋 Concatenating {len(audio_files)} audio files...")

            # Use FFmpeg concat demuxer with re-encoding for compatibility
            # IMPORTANT: Many MP3 files have embedded album art (video stream)
            # We must use -map 0:a to select ONLY audio stream, ignore video (album art)
            cmd = [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-map",  # Map only audio stream
                "0:a",   # Select audio from input 0, ignore video (album art)
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-ar",
                "48000",
                "-y",
                str(temp_audio),
            ]

            self.log("🔧 Using audio-only mapping to ignore album art...")
            self.log(f"⏳ This may take several minutes for {len(audio_files)} files...")
            self.log("💡 FFmpeg is re-encoding all audio to AAC format...")

            # Add timeout to prevent hanging forever
            # For 30 files at ~3 min each, allow up to 15 minutes
            timeout_seconds = max(600, len(audio_files) * 30)  # At least 10 min, or 30s per file

            self.log(f"⏱️  Timeout set to {timeout_seconds // 60} minutes")

            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )

            # Check if output file was created
            if not temp_audio.exists():
                self.log("❌ Audio concatenation failed: output file not created", "ERROR")
                self.log(f"FFmpeg output: {result.stderr}", "ERROR")
                return None

            # Cleanup list file after successful concat
            if list_file.exists():
                list_file.unlink()

            self.log(f"✅ Successfully concatenated {len(audio_files)} audio files")
            return temp_audio

        except subprocess.TimeoutExpired as e:
            timeout_min = e.timeout // 60 if e.timeout else 10
            self.log(f"❌ FFmpeg timeout after {timeout_min} minutes!", "ERROR")
            self.log(f"⚠️  Audio concatenation took too long - may need to reduce number of files", "WARNING")

            # Cleanup
            try:
                list_file = self.output_folder / "audio_list.txt"
                if list_file.exists():
                    self.log(f"📄 Audio list file saved for debugging: {list_file}", "WARNING")
            except:
                pass
            return None

        except subprocess.CalledProcessError as e:
            self.log(f"❌ FFmpeg error during audio concatenation!", "ERROR")

            # Show detailed error from FFmpeg
            if e.stderr:
                self.log(f"📋 FFmpeg stderr output:", "ERROR")
                # Show last 20 lines for context
                error_lines = e.stderr.strip().split('\n')
                for line in error_lines[-20:]:
                    if line.strip():
                        self.log(f"   {line}", "ERROR")

            # Show the command that failed
            self.log(f"💻 Command: {' '.join(e.cmd)}", "ERROR")

            # Cleanup list file on error
            try:
                list_file = self.output_folder / "audio_list.txt"
                if list_file.exists():
                    # Don't delete - keep for debugging
                    self.log(f"📄 Audio list file saved for debugging: {list_file}", "WARNING")
            except:
                pass
            return None
        except Exception as e:
            self.log(f"❌ Error concatenating audio: {str(e)}", "ERROR")
            # Cleanup list file on error
            try:
                list_file = self.output_folder / "audio_list.txt"
                if list_file.exists():
                    list_file.unlink()
            except:
                pass
            return None

    def render_video(
        self,
        audio_path,
        visual_path,
        output_path,
        duration,
        resolution,
        is_image=False,
        apply_zoom=False,
    ):
        """
        Render final video

        Args:
            audio_path: Path to audio file
            visual_path: Path to visual (video or image)
            output_path: Output video path
            duration: Target duration in seconds
            resolution: Output resolution (e.g., "1920x1080")
            is_image: Whether visual is an image
            apply_zoom: Whether to apply zoom effect (for images)

        Returns:
            bool: True if successful
        """
        try:
            # Validate inputs
            if not audio_path or not Path(audio_path).exists():
                self.log(f"❌ Audio file not found: {audio_path}", "ERROR")
                return False

            if not visual_path or not Path(visual_path).exists():
                self.log(f"❌ Visual file not found: {visual_path}", "ERROR")
                return False

            width, height = map(int, resolution.split("x"))

            if is_image:
                # Image input
                visual_input = ffmpeg.input(str(visual_path), loop=1, t=duration)

                # Apply zoom effect if requested
                if apply_zoom:
                    # Slow zoom in effect
                    visual_stream = visual_input.filter(
                        "zoompan",
                        z="min(zoom+0.0005,1.2)",
                        d=f"{int(duration * 25)}",
                        s=f"{width}x{height}",
                        fps=25,
                    )
                else:
                    # Just scale
                    visual_stream = visual_input.filter("scale", width, height)
            else:
                # Video input - loop if needed
                visual_input = ffmpeg.input(str(visual_path), stream_loop=-1)
                visual_stream = visual_input.filter("scale", width, height).filter(
                    "trim", duration=duration
                )

            # Audio input
            audio_input = ffmpeg.input(str(audio_path))

            # Combine
            output = ffmpeg.output(
                visual_stream,
                audio_input,
                str(output_path),
                vcodec="libx264",
                acodec="aac",
                preset="medium",
                crf=23,
                audio_bitrate="192k",
                shortest=None,
            )

            # Run FFmpeg
            self.log(f"🎬 Running FFmpeg to render final video...")
            ffmpeg.run(output, overwrite_output=True, capture_stdout=True, capture_stderr=True)

            # Verify output was created
            if not output_path.exists():
                self.log("❌ Rendering failed: output file not created", "ERROR")
                return False

            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            self.log(f"✅ Video rendered successfully ({file_size_mb:.2f} MB)")

            return True

        except ffmpeg.Error as e:
            error_message = e.stderr.decode() if e.stderr else str(e)
            self.log(f"❌ FFmpeg error during video rendering:", "ERROR")
            # Show last 10 lines of error for clarity
            error_lines = error_message.split('\n')
            for line in error_lines[-10:]:
                if line.strip():
                    self.log(f"   {line}", "ERROR")
            return False
        except Exception as e:
            self.log(f"❌ Render error: {str(e)}", "ERROR")
            import traceback
            self.log(f"   {traceback.format_exc()}", "ERROR")
            return False

    def save_chapters(self, chapters, video_file):
        """
        Save chapter metadata to a file

        Args:
            chapters: List of chapter dicts
            video_file: Path to video file

        Returns:
            Path: Path to chapter file
        """
        chapter_file = video_file.with_suffix(".chapters.txt")

        try:
            with open(chapter_file, "w", encoding="utf-8") as f:
                for chapter in chapters:
                    # YouTube chapter format: HH:MM:SS Title
                    start_time = self.format_timestamp(chapter["start_time"])
                    f.write(f"{start_time} {chapter['title']}\n")

            return chapter_file

        except Exception as e:
            self.log(f"⚠️  Warning: Could not save chapters: {str(e)}", "WARNING")
            return None

    def format_timestamp(self, seconds):
        """Format seconds to HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
