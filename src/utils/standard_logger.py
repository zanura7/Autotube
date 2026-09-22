"""
Standardized Logger for Autotube
Provides consistent logging interface across all modules
"""

from typing import Optional
from .file_logger import get_file_logger
from .logging_constants import LogEmojis, LogMessages, LogLevels, LogPatterns


class StandardLogger:
    """Standardized logger that handles both console and file logging"""
    
    def __init__(self, console_log=None):
        """
        Initialize standard logger
        
        Args:
            console_log: Optional console log widget for UI display
        """
        self.console_log = console_log
        self.file_logger = get_file_logger()
    
    def log(self, message: str, level: str = "INFO"):
        """
        Log a message to both console and file
        
        Args:
            message: Message to log
            level: Log level (INFO, SUCCESS, WARNING, ERROR, DEBUG)
        """
        # Broadcast log via API WebSocket
        try:
            from api.logger import manager
            manager.sync_broadcast_log(message, level)
        except ImportError:
            # Fallback if running outside of FastAPI context
            import logging
            logging.info(f"[{level}] {message}")
        
        # Always log to file
        if self.file_logger:
            self.file_logger.log(message, level)
    
    def info(self, message: str):
        """Log info message"""
        self.log(message, "INFO")
    
    def success(self, message: str):
        """Log success message"""
        self.log(message, "SUCCESS")
    
    def warning(self, message: str):
        """Log warning message"""
        self.log(message, "WARNING")
    
    def error(self, message: str):
        """Log error message"""
        self.log(message, "ERROR")
    
    def debug(self, message: str):
        """Log debug message"""
        self.log(message, "DEBUG")
    
    # Convenience methods using standardized patterns
    def start_operation(self, operation_name: str):
        """Log start of operation using standard pattern"""
        self.info(LogMessages.starting_operation(operation_name))
    
    def complete_operation(self, operation_name: str):
        """Log completion of operation using standard pattern"""
        self.success(LogMessages.completed_operation(operation_name))
    
    def fail_operation(self, operation_name: str, error: str = None):
        """Log failure of operation using standard pattern"""
        self.error(LogMessages.failed_operation(operation_name, error))
    
    def warn_operation(self, operation_name: str, warning: str = None):
        """Log warning for operation using standard pattern"""
        self.warning(LogMessages.warning_operation(operation_name, warning))
    
    def progress(self, current: int, total: int, operation: str = None):
        """Log progress using standard pattern"""
        text = LogMessages.progress_update(current, total, operation)
        self.info(text)
        try:
            from api.logger import manager
            manager.sync_broadcast_progress(current, total, text)
        except ImportError:
            pass
    
    def file_op(self, action: str, filename: str):
        """Log file operation using standard pattern"""
        self.info(LogMessages.file_operation(action, filename))
    
    def media_process(self, media_type: str, action: str, details: str = None):
        """Log media processing using standard pattern"""
        self.info(LogMessages.media_processing(media_type, action, details))
    
    def duration(self, duration: float, unit: str = "seconds"):
        """Log duration information using standard pattern"""
        self.info(LogPatterns.duration_info(duration, unit))
    
    def size(self, size: float, unit: str = "MB"):
        """Log size information using standard pattern"""
        self.info(LogPatterns.size_info(size, unit))
    
    def gpu_accel(self):
        """Log GPU acceleration using standard pattern"""
        self.info(LogPatterns.gpu_acceleration())
    
    def cpu_process(self, preset: str = None, crf: str = None, threads: str = None):
        """Log CPU processing using standard pattern"""
        self.info(LogPatterns.cpu_processing(preset, crf, threads))
    
    def analyze_media(self, media_type: str):
        """Log media analysis using standard pattern"""
        self.info(LogPatterns.analyzing_media(media_type))


def create_logger(console_log=None) -> StandardLogger:
    """
    Create a standardized logger instance
    
    Args:
        console_log: Optional console log widget
        
    Returns:
        StandardLogger: Configured logger instance
    """
    return StandardLogger(console_log)