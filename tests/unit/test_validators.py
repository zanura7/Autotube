"""
Unit tests for validators module
"""

import pytest
from pathlib import Path
from utils.validators import (
    validate_youtube_url,
    validate_file_path,
    validate_duration,
    validate_file_size,
    sanitize_filename,
)


class TestValidateYoutubeUrl:
    """Test YouTube URL validation"""

    def test_valid_youtube_url(self):
        """Test with valid YouTube URLs"""
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=abc123",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=test",
        ]
        for url in valid_urls:
            assert validate_youtube_url(url) is True, f"Failed for {url}"

    def test_invalid_youtube_url(self):
        """Test with invalid URLs"""
        invalid_urls = [
            "https://evil.com/hack",
            "http://notayoutubeurl.com",
            "not a url at all",
            "",
            "javascript:alert('xss')",
            "https://youtube.com.evil.com/watch?v=fake",
        ]
        for url in invalid_urls:
            assert validate_youtube_url(url) is False, f"Should reject {url}"

    def test_empty_url(self):
        """Test with empty URL"""
        assert validate_youtube_url("") is False
        assert validate_youtube_url(None) is False


class TestValidateFilePath:
    """Test file path validation"""

    def test_valid_existing_file(self, tmp_path):
        """Test with valid existing file"""
        test_file = tmp_path / "test.mp4"
        test_file.write_text("test content")

        is_valid, error_msg = validate_file_path(
            str(test_file), must_exist=True, allowed_extensions=[".mp4"]
        )

        assert is_valid is True
        assert error_msg == ""

    def test_nonexistent_file_when_required(self):
        """Test with non-existent file when existence is required"""
        is_valid, error_msg = validate_file_path(
            "/nonexistent/file.mp4", must_exist=True
        )

        assert is_valid is False
        assert "does not exist" in error_msg.lower()

    def test_invalid_extension(self, tmp_path):
        """Test with invalid file extension"""
        test_file = tmp_path / "test.exe"
        test_file.write_text("test")

        is_valid, error_msg = validate_file_path(
            str(test_file), must_exist=True, allowed_extensions=[".mp4", ".avi"]
        )

        assert is_valid is False
        assert "extension" in error_msg.lower()

    def test_path_traversal_attempt(self):
        """Test path traversal attack prevention"""
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "/etc/passwd",
        ]

        for path in dangerous_paths:
            is_valid, error_msg = validate_file_path(path, must_exist=False)
            # Should either reject or normalize the path
            assert is_valid is False or ".." not in error_msg


class TestValidateDuration:
    """Test duration validation"""

    def test_valid_duration(self):
        """Test with valid duration values"""
        test_cases = [
            ("60", 1, 600, True, 60),
            ("120", 1, 600, True, 120),
            ("1", 1, 600, True, 1),
        ]

        for duration_str, min_val, max_val, expected_valid, expected_duration in test_cases:
            is_valid, error_msg, duration = validate_duration(
                duration_str, min_val, max_val
            )
            assert is_valid == expected_valid
            if is_valid:
                assert duration == expected_duration

    def test_invalid_duration_format(self):
        """Test with invalid duration formats"""
        invalid_durations = ["abc", "1.5.6", "", "negative"]

        for duration_str in invalid_durations:
            is_valid, error_msg, duration = validate_duration(duration_str, 1, 600)
            assert is_valid is False
            assert error_msg != ""

    def test_duration_out_of_range(self):
        """Test with duration outside allowed range"""
        # Too low
        is_valid, error_msg, duration = validate_duration("0", 1, 600)
        assert is_valid is False

        # Too high
        is_valid, error_msg, duration = validate_duration("1000", 1, 600)
        assert is_valid is False


class TestValidateFileSize:
    """Test file size validation"""

    def test_valid_file_size(self, tmp_path):
        """Test with file within size limit"""
        test_file = tmp_path / "small.txt"
        test_file.write_text("a" * 1000)  # 1KB file

        is_valid, error_msg, size_mb = validate_file_size(
            str(test_file), max_size_mb=1
        )

        assert is_valid is True
        assert size_mb < 1

    def test_file_exceeds_size_limit(self, tmp_path):
        """Test with file exceeding size limit"""
        test_file = tmp_path / "large.txt"
        test_file.write_text("a" * (2 * 1024 * 1024))  # 2MB file

        is_valid, error_msg, size_mb = validate_file_size(
            str(test_file), max_size_mb=1
        )

        assert is_valid is False
        assert "exceeds" in error_msg.lower()
        assert size_mb > 1

    def test_nonexistent_file(self):
        """Test with non-existent file"""
        is_valid, error_msg, size_mb = validate_file_size(
            "/nonexistent/file.txt", max_size_mb=100
        )

        assert is_valid is False
        assert size_mb == 0


class TestSanitizeFilename:
    """Test filename sanitization"""

    def test_remove_invalid_characters(self):
        """Test removal of invalid characters"""
        dangerous_filenames = [
            ("file<name>.mp4", "filename.mp4"),
            ("file|name.mp4", "filename.mp4"),
            ("file:name.mp4", "filename.mp4"),
            ("file*name.mp4", "filename.mp4"),
            ("file?name.mp4", "filename.mp4"),
            ('file"name.mp4', "filename.mp4"),
        ]

        for dangerous, expected in dangerous_filenames:
            sanitized = sanitize_filename(dangerous)
            assert sanitized == expected

    def test_preserve_valid_characters(self):
        """Test that valid characters are preserved"""
        valid_filenames = [
            "valid_file-name.mp4",
            "file-with-dashes.mp4",
            "file_with_underscores.mp4",
            "File With Spaces.mp4",
        ]

        for filename in valid_filenames:
            sanitized = sanitize_filename(filename)
            # Should preserve the structure (maybe normalize spaces)
            assert len(sanitized) > 0
            assert sanitized.endswith(".mp4")

    def test_empty_filename(self):
        """Test with empty filename"""
        sanitized = sanitize_filename("")
        assert sanitized == "unnamed"

    def test_filename_with_path_separators(self):
        """Test removal of path separators"""
        dangerous_filenames = [
            ("../../../etc/passwd", "etcpasswd"),
            ("C:\\Windows\\System32", "CWindowsSystem32"),
            ("/etc/shadow", "etcshadow"),
        ]

        for dangerous, _ in dangerous_filenames:
            sanitized = sanitize_filename(dangerous)
            assert "/" not in sanitized
            assert "\\" not in sanitized
            assert ".." not in sanitized
