"""
FFmpeg checker utility to ensure FFmpeg is installed and accessible
"""

import subprocess
import shutil


def check_ffmpeg():
    """
    Check if FFmpeg is installed and accessible in PATH

    Returns:
        bool: True if FFmpeg is found, False otherwise
    """
    # Method 1: Use shutil.which (most reliable)
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return True

    # Method 2: Try to run ffmpeg -version
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_ffmpeg_version():
    """
    Get FFmpeg version information

    Returns:
        str: FFmpeg version string, or None if not found
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            # Extract first line which contains version
            first_line = result.stdout.split("\n")[0]
            return first_line

        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def check_ffprobe():
    """
    Check if FFprobe is installed (comes with FFmpeg)

    Returns:
        bool: True if FFprobe is found, False otherwise
    """
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path:
        return True

    try:
        result = subprocess.run(
            ["ffprobe", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
