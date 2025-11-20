"""
File Logger with Rotation
Log messages to file with automatic rotation
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
import os


class FileLogger:
    """File logger with rotation support"""

    def __init__(
        self,
        log_file=None,
        max_size_mb=10,
        max_files=5,
        log_level="INFO",
    ):
        """
        Initialize file logger

        Args:
            log_file: Path to log file (default: ~/.autotube/logs/autotube.log)
            max_size_mb: Maximum size of log file in MB before rotation
            max_files: Maximum number of log files to keep
            log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        if log_file:
            self.log_file = Path(log_file)
        else:
            # Default location in user home directory
            log_dir = Path.home() / ".autotube" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            self.log_file = log_dir / "autotube.log"

        self.max_size_mb = max_size_mb
        self.max_files = max_files
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)

        # Create logger
        self.logger = logging.getLogger("Autotube")
        self.logger.setLevel(self.log_level)

        # Remove existing handlers
        self.logger.handlers.clear()

        # Create rotating file handler
        max_bytes = max_size_mb * 1024 * 1024  # Convert to bytes
        file_handler = RotatingFileHandler(
            str(self.log_file),
            maxBytes=max_bytes,
            backupCount=max_files,
            encoding="utf-8",
        )

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)

        # Add handler to logger
        self.logger.addHandler(file_handler)

        # Log initialization
        self.logger.info("=" * 80)
        self.logger.info(f"Autotube session started")
        self.logger.info(f"Log file: {self.log_file}")
        self.logger.info("=" * 80)

    def log(self, message, level="INFO"):
        """
        Log a message

        Args:
            message: Message to log
            level: Log level (INFO, WARNING, ERROR, SUCCESS, DEBUG)
        """
        # Clean ANSI codes and emojis for file logging
        clean_message = self._clean_message(message)

        level = level.upper()

        if level == "ERROR":
            self.logger.error(clean_message)
        elif level == "WARNING":
            self.logger.warning(clean_message)
        elif level == "SUCCESS":
            self.logger.info(f"SUCCESS: {clean_message}")
        elif level == "DEBUG":
            self.logger.debug(clean_message)
        else:
            self.logger.info(clean_message)

    def _clean_message(self, message):
        """
        Clean message for file logging (remove emojis and ANSI codes)

        Args:
            message: Raw message

        Returns:
            str: Cleaned message
        """
        # Remove common emojis used in app
        emoji_map = {
            "🚀": "[START]",
            "✅": "[OK]",
            "❌": "[ERROR]",
            "⚠️": "[WARN]",
            "📊": "[INFO]",
            "🎬": "[VIDEO]",
            "🎵": "[AUDIO]",
            "🔄": "[PROCESS]",
            "📁": "[FOLDER]",
            "⬇️": "[DOWNLOAD]",
            "📝": "[NOTE]",
            "🔊": "[AUDIO]",
            "🖼️": "[IMAGE]",
            "⏱️": "[TIME]",
            "📐": "[SIZE]",
            "⚡": "[GPU]",
            "💻": "[CPU]",
            "🛑": "[STOP]",
            "🔁": "[LOOP]",
            "📖": "[CHAPTER]",
            "ℹ️": "[INFO]",
        }

        clean_msg = message
        for emoji, replacement in emoji_map.items():
            clean_msg = clean_msg.replace(emoji, replacement)

        return clean_msg

    def info(self, message):
        """Log info message"""
        self.log(message, "INFO")

    def warning(self, message):
        """Log warning message"""
        self.log(message, "WARNING")

    def error(self, message):
        """Log error message"""
        self.log(message, "ERROR")

    def success(self, message):
        """Log success message"""
        self.log(message, "SUCCESS")

    def debug(self, message):
        """Log debug message"""
        self.log(message, "DEBUG")

    def log_section(self, title):
        """Log a section separator"""
        separator = "=" * 80
        self.logger.info(separator)
        self.logger.info(title)
        self.logger.info(separator)

    def get_log_file_path(self):
        """Get the path to the log file"""
        return str(self.log_file)

    def get_log_size(self):
        """Get current log file size in MB"""
        try:
            if self.log_file.exists():
                size_bytes = self.log_file.stat().st_size
                return size_bytes / (1024 * 1024)
            return 0
        except:
            return 0

    def close(self):
        """Close logger and handlers"""
        self.logger.info("=" * 80)
        self.logger.info("Autotube session ended")
        self.logger.info("=" * 80)

        for handler in self.logger.handlers:
            handler.close()
            self.logger.removeHandler(handler)


# Global file logger instance
_global_file_logger = None


def get_file_logger():
    """Get or create global file logger instance"""
    global _global_file_logger

    if _global_file_logger is None:
        _global_file_logger = FileLogger()

    return _global_file_logger


def init_file_logger(log_file=None, max_size_mb=10, max_files=5, log_level="INFO"):
    """
    Initialize global file logger

    Args:
        log_file: Path to log file
        max_size_mb: Maximum size of log file in MB
        max_files: Maximum number of log files
        log_level: Log level
    """
    global _global_file_logger

    _global_file_logger = FileLogger(
        log_file=log_file,
        max_size_mb=max_size_mb,
        max_files=max_files,
        log_level=log_level,
    )

    return _global_file_logger


def close_file_logger():
    """Close global file logger"""
    global _global_file_logger

    if _global_file_logger:
        _global_file_logger.close()
        _global_file_logger = None
