"""
Enhanced Logger with User-Friendly Error Display
Extends the standard logger to show user-friendly errors with progressive detail options
"""

from typing import Optional
from .standard_logger import StandardLogger
from .error_handler import UserFriendlyError, ErrorCategory, ErrorSeverity, handle_error, handle_subprocess_error


class EnhancedLogger(StandardLogger):
    """Enhanced logger that displays user-friendly errors with progressive details"""
    
    def __init__(self, console_log=None):
        """
        Initialize enhanced logger
        
        Args:
            console_log: Optional console log widget for UI display
        """
        super().__init__(console_log)
        self.show_technical_details = False  # Can be toggled by user
    
    def log_user_friendly_error(
        self,
        error: Exception,
        operation_context: str = None,
        stderr_output: str = None
    ):
        """
        Log an error using user-friendly formatting
        
        Args:
            error: The original exception
            operation_context: Description of what operation was being performed
            stderr_output: Raw stderr output from subprocess
        """
        user_error = handle_error(error, operation_context, stderr_output)
        self._display_user_error(user_error)
    
    def log_subprocess_error(
        self,
        returncode: int,
        stderr: str,
        operation_context: str = None
    ):
        """
        Log a subprocess error using user-friendly formatting
        
        Args:
            returncode: Process return code
            stderr: Standard error output
            operation_context: What operation was being performed
        """
        user_error = handle_subprocess_error(returncode, stderr, operation_context)
        self._display_user_error(user_error)
    
    def _display_user_error(self, user_error: UserFriendlyError):
        """Display a user-friendly error with appropriate formatting"""
        # Get the appropriate emoji for the category
        category_emoji = self._get_category_emoji(user_error.category)
        
        # Display main error message
        main_message = f"{category_emoji} {user_error.get_display_message()}"
        self.error(main_message)
        
        # Display suggestions if available
        if user_error.suggestions:
            self.info("💡 Suggestions:")
            for suggestion in user_error.suggestions:
                self.info(f"   • {suggestion}")
        
        # Show technical details if enabled
        if self.show_technical_details and user_error.technical_details:
            self.debug("🔧 Technical Details:")
            for line in user_error.technical_details.split('\n'):
                if line.strip():
                    self.debug(f"   {line}")
        else:
            # Offer option to view technical details
            self.info("ℹ️  Use 'Show Technical Details' for debugging information")
        
        # Always log full technical details to file
        if self.file_logger and user_error.technical_details:
            self.file_logger.debug("=== Technical Error Details ===")
            self.file_logger.debug(user_error.get_copy_friendly_format())
            self.file_logger.debug("=" * 35)
    
    def _get_category_emoji(self, category: ErrorCategory) -> str:
        """Get appropriate emoji for error category"""
        category_emojis = {
            ErrorCategory.FILE_PATH: "📁",
            ErrorCategory.FORMAT: "🎬",
            ErrorCategory.SYSTEM: "⚙️",
            ErrorCategory.RESOURCE: "💾",
            ErrorCategory.NETWORK: "🌐",
            ErrorCategory.MEDIA_PROCESSING: "🎵",
            ErrorCategory.CONFIGURATION: "⚙️",
            ErrorCategory.UNKNOWN: "❓"
        }
        return category_emojis.get(category, "❌")
    
    def toggle_technical_details(self):
        """Toggle display of technical details"""
        self.show_technical_details = not self.show_technical_details
        status = "enabled" if self.show_technical_details else "disabled"
        self.info(f"🔧 Technical details display {status}")
    
    def get_error_report(self, user_error: UserFriendlyError) -> str:
        """Get a copy-friendly error report"""
        return user_error.get_copy_friendly_format()
    
    # Convenience methods for common error scenarios
    def log_ffmpeg_error(
        self,
        returncode: int,
        stderr: str,
        operation: str = "media processing"
    ):
        """Log FFmpeg-specific errors with context"""
        self.log_subprocess_error(returncode, stderr, f"FFmpeg {operation}")
    
    def log_file_error(
        self,
        error: Exception,
        file_path: str,
        operation: str = "file operation"
    ):
        """Log file-related errors with context"""
        context = f"{operation} on '{file_path}'"
        self.log_user_friendly_error(error, context)
    
    def log_network_error(
        self,
        error: Exception,
        url: str = None,
        operation: str = "network operation"
    ):
        """Log network-related errors with context"""
        context = f"{operation}"
        if url:
            context += f" for '{url}'"
        self.log_user_friendly_error(error, context)
    
    def log_resource_error(
        self,
        error: Exception,
        resource_type: str = "system resource",
        operation: str = "resource operation"
    ):
        """Log resource-related errors with context"""
        context = f"{operation} using {resource_type}"
        self.log_user_friendly_error(error, context)


def create_enhanced_logger(console_log=None) -> EnhancedLogger:
    """
    Create an enhanced logger instance
    
    Args:
        console_log: Optional console log widget
        
    Returns:
        EnhancedLogger: Configured enhanced logger instance
    """
    return EnhancedLogger(console_log)


# Global enhanced logger instance
_global_enhanced_logger = None


def get_global_enhanced_logger() -> Optional[EnhancedLogger]:
    """Get the global enhanced logger instance if it exists"""
    return _global_enhanced_logger


def set_global_enhanced_logger(logger: EnhancedLogger):
    """Set the global enhanced logger instance"""
    global _global_enhanced_logger
    _global_enhanced_logger = logger