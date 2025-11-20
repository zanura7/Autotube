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

            # Step 4: Prepare visual
            self.log("🖼️  Preparing visual...")
            if progress_callback:
                progress_callback(0.6, "Preparing visual...")

            visual_path = Path(visual_path)
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
            if temp_audio and temp_audio.exists():
                temp_audio.unlink()

            self.log(f"✅ Video created successfully: {output_file.name}", "SUCCESS")
            if progress_callback:
                progress_callback(1.0, "Complete!")

            return True

        except Exception as e:
            self.log(f"❌ Error generating video: {str(e)}", "ERROR")
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
        temp_audio = self.output_folder / "temp_audio.mp3"

        try:
            # Create file list for concat
            list_file = self.output_folder / "audio_list.txt"

            with open(list_file, "w", encoding="utf-8") as f:
                for audio_file in audio_files:
                    # Use absolute path
                    f.write(f"file '{audio_file.absolute()}'\n")

            # Use FFmpeg concat demuxer
            cmd = [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                "-y",
                str(temp_audio),
            ]

            subprocess.run(cmd, check=True, capture_output=True, text=True)

            # Clean up list file
            list_file.unlink()

            return temp_audio

        except Exception as e:
            self.log(f"❌ Error concatenating audio: {str(e)}", "ERROR")
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
            ffmpeg.run(output, overwrite_output=True, capture_stdout=True, capture_stderr=True)

            return output_path.exists()

        except ffmpeg.Error as e:
            error_message = e.stderr.decode() if e.stderr else str(e)
            self.log(f"FFmpeg error: {error_message}", "ERROR")
            return False
        except Exception as e:
            self.log(f"Render error: {str(e)}", "ERROR")
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
