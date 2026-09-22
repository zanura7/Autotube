"""
FFmpeg checker utility to ensure FFmpeg is installed and accessible
"""

import subprocess
import shutil
import sys
from pathlib import Path


def check_ffmpeg(config=None):
    """
    Check if FFmpeg is installed and accessible

    Args:
        config: ConfigManager instance to check for custom FFmpeg path

    Returns:
        bool: True if FFmpeg is found, False otherwise
    """
    # Method 1: Check custom path from config
    if config:
        ffmpeg_settings = config.get_ffmpeg_settings()
        if ffmpeg_settings.get("use_custom_path", False):
            custom_path = ffmpeg_settings.get("custom_path", "")
            if custom_path and Path(custom_path).exists():
                return _test_ffmpeg_executable(custom_path)

    # Method 2: Use shutil.which (system PATH)
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return _test_ffmpeg_executable(ffmpeg_path)

    # Method 3: Check bundled FFmpeg in multiple possible locations
    # Try relative to executable (for frozen app)
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        bundled_path = exe_dir / "ffmpeg.exe"
        if bundled_path.exists():
            return _test_ffmpeg_executable(str(bundled_path))
    
    # Try in current working directory
    bundled_path = Path.cwd() / "ffmpeg" / "bin" / "ffmpeg.exe"
    if bundled_path.exists():
        return _test_ffmpeg_executable(str(bundled_path))

    return False


def get_ffmpeg_path(config=None):
    """
    Get the path to FFmpeg executable

    Args:
        config: ConfigManager instance to check for custom FFmpeg path

    Returns:
        str: Path to FFmpeg executable, or "ffmpeg" if using system PATH
    """
    # Method 1: Check custom path from config
    if config:
        ffmpeg_settings = config.get_ffmpeg_settings()
        if ffmpeg_settings.get("use_custom_path", False):
            custom_path = ffmpeg_settings.get("custom_path", "")
            if custom_path and Path(custom_path).exists():
                return custom_path

    # Method 2: Use system PATH
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path

    # Method 3: Check bundled FFmpeg in multiple possible locations
    # Try relative to executable (for frozen app)
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        bundled_path = exe_dir / "ffmpeg.exe"
        if bundled_path.exists():
            return str(bundled_path)
    
    # Try in current working directory
    bundled_path = Path.cwd() / "ffmpeg" / "bin" / "ffmpeg.exe"
    if bundled_path.exists():
        return str(bundled_path)

    return "ffmpeg"  # Fallback to system PATH


def _test_ffmpeg_executable(ffmpeg_path):
    """
    Test if FFmpeg executable works

    Args:
        ffmpeg_path: Path to FFmpeg executable

    Returns:
        bool: True if executable works, False otherwise
    """
    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
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
