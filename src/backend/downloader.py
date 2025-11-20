"""
Mass Downloader Backend using yt-dlp
Supports audio/video download with normalization
"""

import yt_dlp
import subprocess
from pathlib import Path
from datetime import datetime
import json


class Downloader:
    """Mass downloader for YouTube content"""

    def __init__(self, output_folder, console_log=None):
        """
        Initialize downloader

        Args:
            output_folder: Path to output folder
            console_log: Console log widget for logging
        """
        self.output_folder = Path(output_folder)
        self.console_log = console_log
        self.downloaded_files = []

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

    def download_batch(self, urls, format_type="mp3_320", normalize=True, progress_callback=None):
        """
        Download multiple URLs

        Args:
            urls: List of URLs to download
            format_type: Format type (mp3_320, mp3_128, video_best)
            normalize: Whether to normalize audio
            progress_callback: Callback function for progress updates

        Returns:
            bool: True if successful, False otherwise
        """
        self.downloaded_files = []
        total = len(urls)

        self.log(f"🚀 Memulai download {total} file...")

        for index, url in enumerate(urls, 1):
            try:
                if progress_callback:
                    progress_callback(index - 1, total, f"Downloading {index}/{total}")

                self.log(f"⬇️ [{index}/{total}] Downloading: {url}")

                # Download
                file_path = self.download_single(url, format_type)

                if file_path:
                    self.downloaded_files.append(file_path)
                    self.log(f"✅ Downloaded: {file_path.name}", "SUCCESS")

                    # Normalize if audio and requested
                    if normalize and format_type.startswith("mp3"):
                        self.log(f"🔊 Normalizing audio: {file_path.name}")
                        self.normalize_audio(file_path)
                        self.log(f"✅ Audio normalized", "SUCCESS")

            except Exception as e:
                self.log(f"❌ Error downloading {url}: {str(e)}", "ERROR")
                continue

        if progress_callback:
            progress_callback(total, total, "Complete")

        self.log(f"✅ Download selesai! {len(self.downloaded_files)}/{total} berhasil", "SUCCESS")

        return len(self.downloaded_files) > 0

    def download_single(self, url, format_type="mp3_320"):
        """
        Download a single URL

        Args:
            url: URL to download
            format_type: Format type

        Returns:
            Path: Path to downloaded file
        """
        # Configure yt-dlp options
        ydl_opts = self._get_ydl_options(format_type)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get info first
            info = ydl.extract_info(url, download=False)
            filename = ydl.prepare_filename(info)

            # Download
            ydl.download([url])

            # For MP3, the extension will be changed
            if format_type.startswith("mp3"):
                filename = Path(filename).with_suffix(".mp3")

            return Path(filename)

    def _get_ydl_options(self, format_type):
        """Get yt-dlp options based on format type"""

        base_opts = {
            "outtmpl": str(self.output_folder / "%(title)s.%(ext)s"),
            "quiet": False,
            "no_warnings": False,
        }

        if format_type == "mp3_320":
            base_opts.update(
                {
                    "format": "bestaudio/best",
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "320",
                        }
                    ],
                }
            )
        elif format_type == "mp3_128":
            base_opts.update(
                {
                    "format": "bestaudio/best",
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "128",
                        }
                    ],
                }
            )
        elif format_type == "video_best":
            base_opts.update(
                {
                    "format": "bestvideo+bestaudio/best",
                    "merge_output_format": "mp4",
                }
            )

        return base_opts

    def normalize_audio(self, audio_file):
        """
        Normalize audio volume using FFmpeg loudnorm filter

        Args:
            audio_file: Path to audio file
        """
        audio_file = Path(audio_file)
        temp_file = audio_file.with_suffix(".normalized.mp3")

        try:
            # Use FFmpeg loudnorm filter for audio normalization
            cmd = [
                "ffmpeg",
                "-i",
                str(audio_file),
                "-af",
                "loudnorm=I=-16:TP=-1.5:LRA=11",
                "-ar",
                "48000",
                "-y",
                str(temp_file),
            ]

            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )

            # Replace original with normalized
            temp_file.replace(audio_file)

        except subprocess.CalledProcessError as e:
            self.log(f"⚠️  Warning: Audio normalization failed: {e}", "WARNING")
            # Clean up temp file if exists
            if temp_file.exists():
                temp_file.unlink()

    def generate_playlist(self):
        """
        Generate M3U playlist from downloaded files

        Returns:
            Path: Path to playlist file
        """
        if not self.downloaded_files:
            self.log("⚠️  No files to create playlist", "WARNING")
            return None

        # Filter audio files only
        audio_files = [
            f for f in self.downloaded_files if f.suffix.lower() in [".mp3", ".m4a", ".wav"]
        ]

        if not audio_files:
            self.log("⚠️  No audio files found for playlist", "WARNING")
            return None

        # Create playlist filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        playlist_file = self.output_folder / f"playlist_{timestamp}.m3u"

        self.log(f"📝 Creating playlist: {playlist_file.name}")

        try:
            with open(playlist_file, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")

                for audio_file in audio_files:
                    # Write relative path
                    relative_path = audio_file.relative_to(self.output_folder)
                    f.write(f"#EXTINF:-1,{audio_file.stem}\n")
                    f.write(f"{relative_path}\n")

            self.log(f"✅ Playlist created with {len(audio_files)} tracks", "SUCCESS")
            return playlist_file

        except Exception as e:
            self.log(f"❌ Error creating playlist: {str(e)}", "ERROR")
            return None
