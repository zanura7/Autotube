"""
Input validation utilities
"""

import re
from pathlib import Path
from urllib.parse import urlparse


def validate_youtube_url(url):
    """
    Validate YouTube URL

    Args:
        url: URL string to validate

    Returns:
        bool: True if valid YouTube URL
    """
    if not url or not isinstance(url, str):
        return False

    # Parse URL
    try:
        parsed = urlparse(url)
    except:
        return False

    # Check scheme
    if parsed.scheme not in ["http", "https"]:
        return False

    # Check domain
    valid_domains = [
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "www.youtu.be",
    ]

    if not any(parsed.netloc.endswith(domain) for domain in valid_domains):
        return False

    return True


def validate_file_path(file_path, must_exist=True, allowed_extensions=None):
    """
    Validate file path

    Args:
        file_path: Path string to validate
        must_exist: Whether file must exist
        allowed_extensions: List of allowed extensions (e.g., ['.mp4', '.avi'])

    Returns:
        tuple: (is_valid, error_message)
    """
    if not file_path:
        return False, "Path is empty"

    try:
        path = Path(file_path)
    except Exception as e:
        return False, f"Invalid path: {str(e)}"

    # Check for path traversal
    try:
        path.resolve()
    except Exception as e:
        return False, f"Path resolution failed: {str(e)}"

    # Check if exists
    if must_exist and not path.exists():
        return False, "File does not exist"

    # Check extension
    if allowed_extensions and path.suffix.lower() not in allowed_extensions:
        return False, f"Invalid file extension. Allowed: {', '.join(allowed_extensions)}"

    return True, ""


def validate_duration(duration_minutes, min_val=1, max_val=600):
    """
    Validate duration in minutes

    Args:
        duration_minutes: Duration value
        min_val: Minimum allowed (default: 1 minute)
        max_val: Maximum allowed (default: 600 minutes = 10 hours)

    Returns:
        tuple: (is_valid, error_message, value)
    """
    try:
        value = int(duration_minutes)
    except ValueError:
        return False, "Duration must be a number", None

    if value < min_val:
        return False, f"Duration must be at least {min_val} minute(s)", None

    if value > max_val:
        return False, f"Duration cannot exceed {max_val} minutes ({max_val // 60} hours)", None

    return True, "", value


def validate_file_size(file_path, max_size_mb=1000):
    """
    Validate file size

    Args:
        file_path: Path to file
        max_size_mb: Maximum size in MB

    Returns:
        tuple: (is_valid, error_message, size_mb)
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return False, "File does not exist", 0

        size_bytes = path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)

        if size_mb > max_size_mb:
            return False, f"File too large ({size_mb:.1f} MB). Max: {max_size_mb} MB", size_mb

        return True, "", size_mb

    except Exception as e:
        return False, f"Error checking file size: {str(e)}", 0


def sanitize_filename(filename):
    """
    Sanitize filename to remove invalid characters

    Args:
        filename: Original filename

    Returns:
        str: Sanitized filename
    """
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)

    # Replace spaces with underscores
    filename = filename.replace(' ', '_')

    # Limit length
    if len(filename) > 200:
        filename = filename[:200]

    return filename


def validate_output_directory(dir_path):
    """
    Validate and create output directory if needed

    Args:
        dir_path: Directory path

    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        path = Path(dir_path)

        # Check for path traversal
        path.resolve()

        # Create if doesn't exist
        path.mkdir(parents=True, exist_ok=True)

        # Check if writable
        test_file = path / ".test_write"
        try:
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            return False, f"Directory not writable: {str(e)}"

        return True, ""

    except Exception as e:
        return False, f"Invalid directory: {str(e)}"
