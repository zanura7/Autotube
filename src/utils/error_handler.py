"""
User-Friendly Error Handler for Autotube
Converts technical errors into user-friendly messages with actionable suggestions
"""

import re
from pathlib import Path
from typing import Tuple, Optional, Dict, List
from enum import Enum


class ErrorCategory(Enum):
    """Error categories for better user understanding"""
    FILE_PATH = "file_path"
    FORMAT = "format"
    SYSTEM = "system"
    RESOURCE = "resource"
    NETWORK = "network"
    MEDIA_PROCESSING = "media_processing"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Error severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class UserFriendlyError:
    """Container for user-friendly error information"""
    
    def __init__(
        self,
        user_message: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        suggestions: List[str] = None,
        technical_details: str = None,
        operation_context: str = None
    ):
        self.user_message = user_message
        self.category = category
        self.severity = severity
        self.suggestions = suggestions or []
        self.technical_details = technical_details
        self.operation_context = operation_context
    
    def get_display_message(self) -> str:
        """Get the main message to display to users"""
        context = f" while {self.operation_context}" if self.operation_context else ""
        return f"{self.user_message}{context}"
    
    def get_full_message(self) -> str:
        """Get complete message including suggestions"""
        message = self.get_display_message()
        
        if self.suggestions:
            suggestions_text = "\n".join([f"  • {suggestion}" for suggestion in self.suggestions])
            message += f"\n\nSuggestions:\n{suggestions_text}"
        
        return message
    
    def get_technical_details(self) -> str:
        """Get technical details for debugging"""
        details = []
        
        if self.operation_context:
            details.append(f"Operation: {self.operation_context}")
        
        details.append(f"Category: {self.category.value}")
        details.append(f"Severity: {self.severity.value}")
        
        if self.technical_details:
            details.append(f"Technical Error: {self.technical_details}")
        
        return "\n".join(details)
    
    def get_copy_friendly_format(self) -> str:
        """Get error in copy-friendly format for bug reports"""
        lines = [
            "=== Autotube Error Report ===",
            f"User Message: {self.get_display_message()}",
            f"Category: {self.category.value}",
            f"Severity: {self.severity.value}",
        ]
        
        if self.suggestions:
            lines.append("Suggestions:")
            for suggestion in self.suggestions:
                lines.append(f"  - {suggestion}")
        
        if self.technical_details:
            lines.append(f"Technical Details: {self.technical_details}")
        
        lines.append("=" * 30)
        
        return "\n".join(lines)


class ErrorHandler:
    """Handles conversion of technical errors to user-friendly messages"""
    
    def __init__(self):
        self.ffmpeg_patterns = self._init_ffmpeg_patterns()
        self.file_patterns = self._init_file_patterns()
        self.system_patterns = self._init_system_patterns()
    
    def _init_ffmpeg_patterns(self) -> Dict[str, Dict]:
        """Initialize FFmpeg error patterns and their user-friendly translations"""
        return {
            # Video/Audio format issues
            r"Invalid data found when processing input": {
                "message": "The media file appears to be corrupted or in an unsupported format",
                "category": ErrorCategory.FORMAT,
                "suggestions": [
                    "Try converting the file to MP4 or MP3 format",
                    "Check if the file downloaded completely",
                    "Try using a different source file"
                ]
            },
            r"No such file or directory": {
                "message": "Cannot find the specified file",
                "category": ErrorCategory.FILE_PATH,
                "suggestions": [
                    "Check that the file path is correct",
                    "Make sure the file hasn't been moved or deleted",
                    "Try browsing for the file again"
                ]
            },
            r"Permission denied": {
                "message": "Cannot access the file due to permission restrictions",
                "category": ErrorCategory.FILE_PATH,
                "suggestions": [
                    "Check file permissions",
                    "Try running as administrator",
                    "Make sure the file isn't open in another program"
                ]
            },
            r"height not divisible by 2|width not divisible by 2": {
                "message": "Video resolution is not compatible with the encoder",
                "category": ErrorCategory.FORMAT,
                "suggestions": [
                    "Try using standard resolutions like 1920x1080 or 1280x720",
                    "The resolution must have even numbers for width and height"
                ]
            },
            r"Conversion failed": {
                "message": "Media conversion process failed",
                "category": ErrorCategory.MEDIA_PROCESSING,
                "suggestions": [
                    "Try using a different output format",
                    "Check if there's enough disk space",
                    "Verify the source file is not corrupted"
                ]
            },
            r"No space left on device": {
                "message": "Not enough disk space to complete the operation",
                "category": ErrorCategory.RESOURCE,
                "suggestions": [
                    "Free up disk space on your drive",
                    "Choose a different output location with more space",
                    "Try processing fewer files at once"
                ]
            },
            r"Killed": {
                "message": "Process was terminated, possibly due to insufficient memory",
                "category": ErrorCategory.RESOURCE,
                "suggestions": [
                    "Try processing smaller files or fewer files at once",
                    "Close other applications to free up memory",
                    "Consider using lower quality settings"
                ]
            },
            r"Protocol not found|Server returned 404|Connection refused": {
                "message": "Cannot connect to the media source",
                "category": ErrorCategory.NETWORK,
                "suggestions": [
                    "Check your internet connection",
                    "Verify the URL is correct and accessible",
                    "Try again later as the server might be temporarily unavailable"
                ]
            }
        }
    
    def _init_file_patterns(self) -> Dict[str, Dict]:
        """Initialize file operation error patterns"""
        return {
            r"FileNotFoundError": {
                "message": "The specified file could not be found",
                "category": ErrorCategory.FILE_PATH,
                "suggestions": [
                    "Check that the file path is correct",
                    "Make sure the file exists in the specified location",
                    "Try browsing for the file using the file picker"
                ]
            },
            r"PermissionError": {
                "message": "Access to the file or folder is denied",
                "category": ErrorCategory.FILE_PATH,
                "suggestions": [
                    "Check file and folder permissions",
                    "Try running the application as administrator",
                    "Make sure the file isn't being used by another program"
                ]
            },
            r"OSError.*No space left": {
                "message": "Not enough disk space available",
                "category": ErrorCategory.RESOURCE,
                "suggestions": [
                    "Free up space on your hard drive",
                    "Choose a different output folder with more space",
                    "Delete temporary files to make room"
                ]
            },
            r"IsADirectoryError": {
                "message": "Expected a file but found a folder instead",
                "category": ErrorCategory.FILE_PATH,
                "suggestions": [
                    "Select a file, not a folder",
                    "Check that you're pointing to the correct location"
                ]
            },
            r"ValueError.*No audio source": {
                "message": "No audio source provided",
                "category": ErrorCategory.CONFIGURATION,
                "suggestions": [
                    "Select an audio playlist file or audio folder",
                    "Make sure you have audio files to process"
                ]
            },
            r"ValueError.*No visual source": {
                "message": "No visual source provided", 
                "category": ErrorCategory.CONFIGURATION,
                "suggestions": [
                    "Select a visual file (image or video)",
                    "Choose an image folder or video folder",
                    "Make sure you have visual content to combine with audio"
                ]
            }
        }
    
    def _init_system_patterns(self) -> Dict[str, Dict]:
        """Initialize system-level error patterns"""
        return {
            r"ffmpeg.*not found|'ffmpeg' is not recognized": {
                "message": "FFmpeg is not installed or not found in system PATH",
                "category": ErrorCategory.SYSTEM,
                "suggestions": [
                    "Install FFmpeg from https://ffmpeg.org/download.html",
                    "Add FFmpeg to your system PATH",
                    "Restart the application after installing FFmpeg"
                ]
            },
            r"TimeoutExpired": {
                "message": "Operation took too long and was cancelled",
                "category": ErrorCategory.RESOURCE,
                "suggestions": [
                    "Try processing smaller files",
                    "Reduce the number of files being processed",
                    "Check if your system is running other intensive tasks"
                ]
            },
            r"MemoryError": {
                "message": "Not enough memory available to complete the operation",
                "category": ErrorCategory.RESOURCE,
                "suggestions": [
                    "Close other applications to free up memory",
                    "Try processing fewer files at once",
                    "Restart the application and try again"
                ]
            }
        }
    
    def handle_error(
        self,
        error: Exception,
        operation_context: str = None,
        stderr_output: str = None
    ) -> UserFriendlyError:
        """
        Convert a technical error into a user-friendly error
        
        Args:
            error: The original exception or error
            operation_context: Description of what operation was being performed
            stderr_output: Raw stderr output from subprocess (e.g., FFmpeg)
            
        Returns:
            UserFriendlyError: User-friendly error information
        """
        error_text = str(error)
        technical_details = error_text
        
        # If we have stderr output, use that for pattern matching
        if stderr_output:
            error_text = stderr_output
            technical_details = f"Exception: {str(error)}\nStderr: {stderr_output}"
        
        # Try to match FFmpeg patterns first (most common)
        user_error = self._match_patterns(error_text, self.ffmpeg_patterns, technical_details, operation_context)
        if user_error:
            return user_error
        
        # Try file operation patterns
        user_error = self._match_patterns(error_text, self.file_patterns, technical_details, operation_context)
        if user_error:
            return user_error
        
        # Try system patterns
        user_error = self._match_patterns(error_text, self.system_patterns, technical_details, operation_context)
        if user_error:
            return user_error
        
        # Default fallback for unknown errors
        return self._create_fallback_error(error, technical_details, operation_context)
    
    def _match_patterns(
        self,
        error_text: str,
        patterns: Dict[str, Dict],
        technical_details: str,
        operation_context: str
    ) -> Optional[UserFriendlyError]:
        """Match error text against patterns and return user-friendly error"""
        for pattern, error_info in patterns.items():
            if re.search(pattern, error_text, re.IGNORECASE):
                return UserFriendlyError(
                    user_message=error_info["message"],
                    category=error_info["category"],
                    severity=ErrorSeverity.ERROR,
                    suggestions=error_info["suggestions"],
                    technical_details=technical_details,
                    operation_context=operation_context
                )
        return None
    
    def _create_fallback_error(
        self,
        error: Exception,
        technical_details: str,
        operation_context: str
    ) -> UserFriendlyError:
        """Create a fallback error for unknown error types"""
        error_type = type(error).__name__
        
        # Try to create a more friendly message based on exception type
        if "FileNotFound" in error_type:
            message = "A required file could not be found"
            category = ErrorCategory.FILE_PATH
            suggestions = ["Check that all required files are in place", "Try reselecting the files"]
        elif "Permission" in error_type:
            message = "Access was denied to a required file or folder"
            category = ErrorCategory.FILE_PATH
            suggestions = ["Check file permissions", "Try running as administrator"]
        elif "Timeout" in error_type:
            message = "The operation took too long and was cancelled"
            category = ErrorCategory.RESOURCE
            suggestions = ["Try with smaller files", "Check system performance"]
        elif "ValueError" in error_type:
            # Handle validation errors specifically
            error_message = str(error).lower()
            if "no audio source" in error_message:
                message = "No audio source provided"
                category = ErrorCategory.CONFIGURATION
                suggestions = [
                    "Select an audio playlist file or audio folder",
                    "Make sure you have audio files to process"
                ]
            elif "no visual source" in error_message:
                message = "No visual source provided"
                category = ErrorCategory.CONFIGURATION
                suggestions = [
                    "Select a visual file (image or video)",
                    "Choose an image folder or video folder",
                    "Make sure you have visual content to combine with audio"
                ]
            else:
                message = f"Invalid input: {str(error)}"
                category = ErrorCategory.CONFIGURATION
                suggestions = [
                    "Check your input settings",
                    "Make sure all required fields are filled",
                    "Verify your file selections are correct"
                ]
        else:
            message = "An unexpected error occurred"
            category = ErrorCategory.UNKNOWN
            suggestions = [
                "Try the operation again",
                "Check the application logs for more details",
                "Contact support if the problem persists"
            ]
        
        return UserFriendlyError(
            user_message=message,
            category=category,
            severity=ErrorSeverity.ERROR,
            suggestions=suggestions,
            technical_details=technical_details,
            operation_context=operation_context
        )
    
    def handle_subprocess_error(
        self,
        returncode: int,
        stderr: str,
        operation_context: str = None
    ) -> UserFriendlyError:
        """
        Handle subprocess errors (like FFmpeg failures)
        
        Args:
            returncode: Process return code
            stderr: Standard error output
            operation_context: What operation was being performed
            
        Returns:
            UserFriendlyError: User-friendly error information
        """
        # Create a generic subprocess error and let handle_error process it
        error = RuntimeError(f"Process failed with return code {returncode}")
        return self.handle_error(error, operation_context, stderr)


# Global error handler instance
_global_error_handler = None


def get_error_handler() -> ErrorHandler:
    """Get or create global error handler instance"""
    global _global_error_handler
    
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    
    return _global_error_handler


def handle_error(
    error: Exception,
    operation_context: str = None,
    stderr_output: str = None
) -> UserFriendlyError:
    """
    Convenience function to handle errors using global handler
    
    Args:
        error: The original exception
        operation_context: Description of what operation was being performed
        stderr_output: Raw stderr output from subprocess
        
    Returns:
        UserFriendlyError: User-friendly error information
    """
    handler = get_error_handler()
    return handler.handle_error(error, operation_context, stderr_output)


def handle_subprocess_error(
    returncode: int,
    stderr: str,
    operation_context: str = None
) -> UserFriendlyError:
    """
    Convenience function to handle subprocess errors
    
    Args:
        returncode: Process return code
        stderr: Standard error output
        operation_context: What operation was being performed
        
    Returns:
        UserFriendlyError: User-friendly error information
    """
    handler = get_error_handler()
    return handler.handle_subprocess_error(returncode, stderr, operation_context)