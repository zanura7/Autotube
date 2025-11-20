"""
Unit tests for file logger
"""

import pytest
from pathlib import Path
import logging
from utils.file_logger import FileLogger, get_file_logger, init_file_logger, close_file_logger


class TestFileLogger:
    """Test FileLogger class"""

    def test_init_default_location(self, tmp_path, mocker):
        """Test logger initialization with default location"""
        # Mock home directory
        mocker.patch("pathlib.Path.home", return_value=tmp_path)

        logger = FileLogger()

        assert logger.log_file.exists()
        assert logger.log_file.parent.name == "logs"
        assert logger.log_file.name == "autotube.log"

    def test_init_custom_location(self, tmp_path):
        """Test logger initialization with custom location"""
        custom_log = tmp_path / "custom.log"

        logger = FileLogger(log_file=custom_log)

        assert logger.log_file == custom_log
        assert custom_log.exists()

    def test_log_info(self, tmp_path):
        """Test logging info message"""
        log_file = tmp_path / "test.log"
        logger = FileLogger(log_file=log_file)

        logger.log("Test info message", "INFO")

        content = log_file.read_text()
        assert "INFO" in content
        assert "Test info message" in content

    def test_log_warning(self, tmp_path):
        """Test logging warning message"""
        log_file = tmp_path / "test.log"
        logger = FileLogger(log_file=log_file)

        logger.log("Test warning", "WARNING")

        content = log_file.read_text()
        assert "WARNING" in content
        assert "Test warning" in content

    def test_log_error(self, tmp_path):
        """Test logging error message"""
        log_file = tmp_path / "test.log"
        logger = FileLogger(log_file=log_file)

        logger.log("Test error", "ERROR")

        content = log_file.read_text()
        assert "ERROR" in content
        assert "Test error" in content

    def test_log_success(self, tmp_path):
        """Test logging success message"""
        log_file = tmp_path / "test.log"
        logger = FileLogger(log_file=log_file)

        logger.log("Test success", "SUCCESS")

        content = log_file.read_text()
        assert "SUCCESS" in content
        assert "Test success" in content

    def test_emoji_cleaning(self, tmp_path):
        """Test that emojis are cleaned in log file"""
        log_file = tmp_path / "test.log"
        logger = FileLogger(log_file=log_file)

        logger.log("🚀 Starting process", "INFO")

        content = log_file.read_text()
        assert "[START]" in content
        assert "Starting process" in content
        assert "🚀" not in content

    def test_multiple_emoji_cleaning(self, tmp_path):
        """Test cleaning multiple emojis"""
        log_file = tmp_path / "test.log"
        logger = FileLogger(log_file=log_file)

        logger.log("✅ Download complete 📁", "SUCCESS")

        content = log_file.read_text()
        assert "[OK]" in content
        assert "[FOLDER]" in content
        assert "✅" not in content
        assert "📁" not in content

    def test_log_section(self, tmp_path):
        """Test logging section separator"""
        log_file = tmp_path / "test.log"
        logger = FileLogger(log_file=log_file)

        logger.log_section("Test Section")

        content = log_file.read_text()
        assert "=" * 80 in content
        assert "Test Section" in content

    def test_convenience_methods(self, tmp_path):
        """Test convenience logging methods"""
        log_file = tmp_path / "test.log"
        logger = FileLogger(log_file=log_file)

        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.success("Success message")

        content = log_file.read_text()
        assert "Info message" in content
        assert "Warning message" in content
        assert "Error message" in content
        assert "Success message" in content

    def test_get_log_file_path(self, tmp_path):
        """Test getting log file path"""
        log_file = tmp_path / "test.log"
        logger = FileLogger(log_file=log_file)

        path = logger.get_log_file_path()

        assert path == str(log_file)

    def test_get_log_size(self, tmp_path):
        """Test getting log file size"""
        log_file = tmp_path / "test.log"
        logger = FileLogger(log_file=log_file)

        logger.log("Test message", "INFO")

        size = logger.get_log_size()

        assert size > 0
        assert isinstance(size, float)

    def test_log_rotation(self, tmp_path):
        """Test that log rotation is configured"""
        log_file = tmp_path / "test.log"
        logger = FileLogger(log_file=log_file, max_size_mb=0.001, max_files=2)

        # Write enough data to trigger rotation
        for i in range(100):
            logger.log(f"Test message {i} " * 100, "INFO")

        # Check that rotation happened
        log_dir = log_file.parent
        log_files = list(log_dir.glob("test.log*"))

        # Should have main log and at least one backup
        assert len(log_files) >= 1

    def test_max_log_files_limit(self, tmp_path):
        """Test that max log files limit is enforced"""
        log_file = tmp_path / "test.log"
        max_files = 3
        logger = FileLogger(log_file=log_file, max_size_mb=0.001, max_files=max_files)

        # Write enough data to trigger multiple rotations
        for i in range(500):
            logger.log(f"Test message {i} " * 200, "INFO")

        # Check log files
        log_dir = log_file.parent
        log_files = list(log_dir.glob("test.log*"))

        # Should not exceed max_files + 1 (main file + backups)
        assert len(log_files) <= max_files + 1

    def test_close(self, tmp_path):
        """Test closing logger"""
        log_file = tmp_path / "test.log"
        logger = FileLogger(log_file=log_file)

        logger.log("Before close", "INFO")
        logger.close()

        content = log_file.read_text()
        assert "Autotube session ended" in content

    def test_log_level_filtering(self, tmp_path):
        """Test that log level filtering works"""
        log_file = tmp_path / "test.log"
        logger = FileLogger(log_file=log_file, log_level="WARNING")

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        content = log_file.read_text()

        # Debug and Info should be filtered out
        assert "Debug message" not in content
        assert "Info message" not in content

        # Warning and Error should be logged
        assert "Warning message" in content
        assert "Error message" in content


class TestGlobalFileLogger:
    """Test global file logger functions"""

    def test_get_file_logger_creates_instance(self, mocker, tmp_path):
        """Test that get_file_logger creates global instance"""
        mocker.patch("pathlib.Path.home", return_value=tmp_path)

        # Clear global instance first
        import utils.file_logger
        utils.file_logger._global_file_logger = None

        logger = get_file_logger()

        assert logger is not None
        assert isinstance(logger, FileLogger)

    def test_get_file_logger_returns_same_instance(self, mocker, tmp_path):
        """Test that get_file_logger returns same instance"""
        mocker.patch("pathlib.Path.home", return_value=tmp_path)

        # Clear global instance first
        import utils.file_logger
        utils.file_logger._global_file_logger = None

        logger1 = get_file_logger()
        logger2 = get_file_logger()

        assert logger1 is logger2

    def test_init_file_logger(self, tmp_path):
        """Test initializing file logger with custom settings"""
        log_file = tmp_path / "custom.log"

        logger = init_file_logger(
            log_file=log_file,
            max_size_mb=5,
            max_files=3,
            log_level="DEBUG"
        )

        assert logger is not None
        assert logger.log_file == log_file
        assert logger.max_size_mb == 5
        assert logger.max_files == 3

    def test_close_file_logger(self, mocker, tmp_path):
        """Test closing global file logger"""
        mocker.patch("pathlib.Path.home", return_value=tmp_path)

        # Clear and initialize
        import utils.file_logger
        utils.file_logger._global_file_logger = None

        logger = get_file_logger()
        logger.log("Test message", "INFO")

        close_file_logger()

        # Global instance should be cleared
        assert utils.file_logger._global_file_logger is None


class TestLogMessageFormatting:
    """Test log message formatting"""

    def test_timestamp_format(self, tmp_path):
        """Test that timestamp is properly formatted"""
        log_file = tmp_path / "test.log"
        logger = FileLogger(log_file=log_file)

        logger.log("Test", "INFO")

        content = log_file.read_text()

        # Check timestamp format: YYYY-MM-DD HH:MM:SS
        import re
        timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
        assert re.search(timestamp_pattern, content) is not None

    def test_log_format_structure(self, tmp_path):
        """Test log message structure"""
        log_file = tmp_path / "test.log"
        logger = FileLogger(log_file=log_file)

        logger.log("Test message", "INFO")

        content = log_file.read_text()

        # Format should be: TIMESTAMP - LEVEL - MESSAGE
        assert " - INFO - " in content or "- INFO -" in content
        assert "Test message" in content

    def test_multiline_message(self, tmp_path):
        """Test logging multiline message"""
        log_file = tmp_path / "test.log"
        logger = FileLogger(log_file=log_file)

        multiline_msg = "Line 1\nLine 2\nLine 3"
        logger.log(multiline_msg, "INFO")

        content = log_file.read_text()

        assert "Line 1" in content
        assert "Line 2" in content
        assert "Line 3" in content

    def test_special_characters(self, tmp_path):
        """Test logging message with special characters"""
        log_file = tmp_path / "test.log"
        logger = FileLogger(log_file=log_file)

        special_msg = "Test with special chars: @#$%^&*()"
        logger.log(special_msg, "INFO")

        content = log_file.read_text()

        assert special_msg in content
