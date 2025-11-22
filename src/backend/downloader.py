"""
Mass Downloader Backend using yt-dlp
Supports audio/video download with normalization and concurrent downloads
"""

import yt_dlp
import subprocess
from pathlib import Path
from datetime import datetime
import json
import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.validators import validate_youtube_url


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

        # Thread-safe file locks for normalization
        self.file_locks = {}
        self.file_locks_lock = threading.Lock()

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

    def download_batch(self, urls, format_type="mp3_320", normalize=True, progress_callback=None, max_concurrent=3):
        """
        Download multiple URLs with concurrent downloads

        Args:
            urls: List of URLs to download
            format_type: Format type (mp3_320, mp3_128, video_best)
            normalize: Whether to normalize audio
            progress_callback: Callback function for progress updates
            max_concurrent: Maximum number of concurrent downloads (default: 3, max: 5)

        Returns:
            bool: True if successful, False otherwise
        """
        self.downloaded_files = []

        # Deduplicate URLs (remove duplicates while preserving order)
        seen = set()
        unique_urls = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        duplicates_removed = len(urls) - len(unique_urls)
        if duplicates_removed > 0:
            self.log(f"🔍 Removed {duplicates_removed} duplicate URL(s)", "INFO")

        # Validate and filter URLs
        valid_urls = []
        for url in unique_urls:
            if validate_youtube_url(url):
                valid_urls.append(url)
            else:
                self.log(f"⚠️  Skipping invalid URL: {url}", "WARNING")

        if not valid_urls:
            self.log("❌ No valid URLs to download!", "ERROR")
            return False

        total = len(valid_urls)

        # Limit concurrent downloads to max 5
        max_concurrent = min(max_concurrent, 5)
        max_concurrent = max(max_concurrent, 1)  # At least 1

        self.log(f"🚀 Starting download of {total} files ({max_concurrent} concurrent downloads)...")

        # Thread-safe counter for progress
        completed_count = 0
        count_lock = threading.Lock()

        def download_task(url, index):
            """Download a single URL (runs in thread)"""
            nonlocal completed_count

            try:
                self.log(f"⬇️ [{index}/{total}] Downloading: {url}")

                # Download with timeout
                file_path = self.download_single(url, format_type)

                if file_path and file_path.exists():
                    with count_lock:
                        self.downloaded_files.append(file_path)

                    self.log(f"✅ Downloaded: {file_path.name}", "SUCCESS")

                    # Normalize if audio and requested
                    if normalize and format_type.startswith("mp3"):
                        self.log(f"🔊 Normalizing audio: {file_path.name}")
                        if self.normalize_audio(file_path):
                            self.log(f"✅ Audio normalized", "SUCCESS")
                        else:
                            self.log(f"⚠️  Audio normalization skipped", "WARNING")

                    return True, file_path
                else:
                    self.log(f"⚠️  Download failed or file not found", "WARNING")
                    return False, None

            except Exception as e:
                self.log(f"❌ Error downloading {url}: {str(e)}", "ERROR")

                # Cleanup partial downloads
                try:
                    for partial in self.output_folder.glob("*.part"):
                        partial.unlink()
                except:
                    pass

                return False, None

        # Use ThreadPoolExecutor for concurrent downloads
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # Submit all download tasks
            future_to_url = {
                executor.submit(download_task, url, idx): (url, idx)
                for idx, url in enumerate(valid_urls, 1)
            }

            # Process completed downloads
            for future in as_completed(future_to_url):
                url, idx = future_to_url[future]

                try:
                    success, file_path = future.result()

                    with count_lock:
                        completed_count += 1

                    if progress_callback:
                        progress_callback(completed_count, total, f"Downloaded {completed_count}/{total}")

                except Exception as e:
                    self.log(f"❌ Unexpected error for {url}: {str(e)}", "ERROR")
                    with count_lock:
                        completed_count += 1

                    if progress_callback:
                        progress_callback(completed_count, total, f"Downloaded {completed_count}/{total}")

        if progress_callback:
            progress_callback(total, total, "Complete")

        self.log(f"✅ Download complete! {len(self.downloaded_files)}/{total} successful", "SUCCESS")

        return len(self.downloaded_files) > 0

    def download_single(self, url, format_type="mp3_320"):
        """
        Download a single URL
        Skips download if file already exists

        Args:
            url: URL to download
            format_type: Format type

        Returns:
            Path: Path to downloaded file, or None if already exists/failed
        """
        # Configure yt-dlp options
        ydl_opts = self._get_ydl_options(format_type)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get info first to determine filename
            info = ydl.extract_info(url, download=False)
            filename = ydl.prepare_filename(info)

            # For MP3, the extension will be changed
            if format_type.startswith("mp3"):
                filename = Path(filename).with_suffix(".mp3")
            else:
                filename = Path(filename)

            # Check if file already exists
            if filename.exists():
                self.log(f"⏭️ File already exists, skipping: {filename.name}", "INFO")
                return filename

            # Download
            ydl.download([url])

            return filename

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

    def _get_file_lock(self, file_path):
        """
        Get or create a thread lock for a specific file

        Args:
            file_path: Path to file

        Returns:
            threading.Lock: Lock for the file
        """
        file_key = str(file_path)

        with self.file_locks_lock:
            if file_key not in self.file_locks:
                self.file_locks[file_key] = threading.Lock()
            return self.file_locks[file_key]

    def normalize_audio(self, audio_file):
        """
        Normalize audio volume using FFmpeg loudnorm filter
        Thread-safe with file locking and retry logic

        Args:
            audio_file: Path to audio file

        Returns:
            bool: True if successful, False otherwise
        """
        audio_file = Path(audio_file)
        temp_file = audio_file.with_suffix(".normalized.mp3")

        # Get file-specific lock
        file_lock = self._get_file_lock(audio_file)

        # Try to acquire lock with timeout
        if not file_lock.acquire(timeout=10):
            self.log(f"⚠️  Normalization skipped: file locked by another thread", "WARNING")
            return False

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
                timeout=300,  # 5 minute timeout
            )

            # Replace original with normalized (with retry logic for Windows)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # On Windows, wait a moment for file handles to release
                    if sys.platform == "win32":
                        time.sleep(0.5)

                    temp_file.replace(audio_file)
                    return True

                except PermissionError as e:
                    if attempt < max_retries - 1:
                        # Wait with exponential backoff
                        wait_time = 2 ** attempt
                        self.log(f"⏳ File locked, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})", "INFO")
                        time.sleep(wait_time)
                    else:
                        self.log(f"⚠️  Warning: Could not replace file after {max_retries} attempts: {e}", "WARNING")
                        if temp_file.exists():
                            temp_file.unlink()
                        return False

        except subprocess.TimeoutExpired:
            self.log(f"⚠️  Warning: Audio normalization timeout", "WARNING")
            if temp_file.exists():
                temp_file.unlink()
            return False

        except subprocess.CalledProcessError as e:
            self.log(f"⚠️  Warning: Audio normalization failed: {e}", "WARNING")
            # Clean up temp file if exists
            if temp_file.exists():
                temp_file.unlink()
            return False

        except Exception as e:
            self.log(f"⚠️  Warning: Unexpected error in normalization: {e}", "WARNING")
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass
            return False

        finally:
            # Always release the lock
            file_lock.release()

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
