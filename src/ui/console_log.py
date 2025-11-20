"""
Console Log widget for displaying process status and messages
"""

import customtkinter as ctk
from datetime import datetime


class ConsoleLog(ctk.CTkTextbox):
    """Custom console log widget with auto-scroll and file logging"""

    def __init__(self, master, **kwargs):
        # Set default height if not provided
        if "height" not in kwargs:
            kwargs["height"] = 150

        super().__init__(master, **kwargs)

        # Make it read-only
        self.configure(state="disabled")

    def log(self, message, level="INFO"):
        """
        Add a log message to the console

        Args:
            message: The message to log
            level: Log level (INFO, SUCCESS, WARNING, ERROR)
        """
        # Enable editing temporarily
        self.configure(state="normal")

        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Color coding based on level
        color_map = {
            "INFO": "#FFFFFF",
            "SUCCESS": "#4CAF50",
            "WARNING": "#FFC107",
            "ERROR": "#F44336",
        }

        color = color_map.get(level.upper(), "#FFFFFF")

        # Format and insert message
        formatted_message = f"[{timestamp}] {message}\n"
        self.insert("end", formatted_message)

        # Auto-scroll to bottom
        self.see("end")

        # Make it read-only again
        self.configure(state="disabled")

        # Also log to file if file logger is available
        try:
            from utils.file_logger import get_file_logger
            file_logger = get_file_logger()
            if file_logger:
                file_logger.log(message, level)
        except:
            pass  # Silently fail if file logger not available

    def clear(self):
        """Clear all log messages"""
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")

    def log_info(self, message):
        """Log an info message"""
        self.log(message, "INFO")

    def log_success(self, message):
        """Log a success message"""
        self.log(message, "SUCCESS")

    def log_warning(self, message):
        """Log a warning message"""
        self.log(message, "WARNING")

    def log_error(self, message):
        """Log an error message"""
        self.log(message, "ERROR")
