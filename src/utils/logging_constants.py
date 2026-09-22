"""
Logging Constants and Emoji Standardization
Provides consistent emoji usage and logging patterns across the application
"""

# Standard Emojis for Different Operations
class LogEmojis:
    """Standardized emojis for consistent logging"""
    
    # Status Indicators
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    
    # Process States
    START = "🚀"
    STOP = "🛑"
    PROCESS = "🔄"
    LOOP = "🔁"
    
    # Media Types
    VIDEO = "🎬"
    AUDIO = "🎵"
    IMAGE = "🖼️"
    
    # File Operations
    FOLDER = "📁"
    DOWNLOAD = "⬇️"
    NOTE = "📝"
    CHAPTER = "📖"
    
    # Technical
    GPU = "⚡"
    CPU = "💻"
    TIME = "⏱️"
    SIZE = "📐"
    ANALYZE = "📊"


class LogMessages:
    """Standardized log message templates"""
    
    @staticmethod
    def starting_operation(operation_name: str) -> str:
        """Standard message for starting an operation"""
        return f"{LogEmojis.START} Starting {operation_name}..."
    
    @staticmethod
    def completed_operation(operation_name: str) -> str:
        """Standard message for completed operation"""
        return f"{LogEmojis.SUCCESS} {operation_name} completed successfully"
    
    @staticmethod
    def failed_operation(operation_name: str, error: str = None) -> str:
        """Standard message for failed operation"""
        base_msg = f"{LogEmojis.ERROR} {operation_name} failed"
        return f"{base_msg}: {error}" if error else f"{base_msg}!"
    
    @staticmethod
    def warning_operation(operation_name: str, warning: str = None) -> str:
        """Standard message for operation with warnings"""
        base_msg = f"{LogEmojis.WARNING} {operation_name}"
        return f"{base_msg}: {warning}" if warning else base_msg
    
    @staticmethod
    def progress_update(current: int, total: int, operation: str = None) -> str:
        """Standard progress message"""
        base_msg = f"[{current}/{total}]"
        return f"{base_msg} {operation}" if operation else base_msg
    
    @staticmethod
    def file_operation(action: str, filename: str) -> str:
        """Standard file operation message"""
        return f"{LogEmojis.FOLDER} {action}: {filename}"
    
    @staticmethod
    def media_processing(media_type: str, action: str, details: str = None) -> str:
        """Standard media processing message"""
        emoji_map = {
            "video": LogEmojis.VIDEO,
            "audio": LogEmojis.AUDIO,
            "image": LogEmojis.IMAGE
        }
        emoji = emoji_map.get(media_type.lower(), LogEmojis.PROCESS)
        base_msg = f"{emoji} {action}"
        return f"{base_msg}: {details}" if details else base_msg


# Standard Log Levels
class LogLevels:
    """Standard log level constants"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"


# Common Log Patterns
class LogPatterns:
    """Common logging patterns used throughout the application"""
    
    @staticmethod
    def duration_info(duration: float, unit: str = "seconds") -> str:
        """Format duration information"""
        return f"{LogEmojis.TIME} Duration: {duration:.2f} {unit}"
    
    @staticmethod
    def size_info(size: float, unit: str = "MB") -> str:
        """Format size information"""
        return f"{LogEmojis.SIZE} Size: {size:.2f} {unit}"
    
    @staticmethod
    def gpu_acceleration() -> str:
        """GPU acceleration message"""
        return f"{LogEmojis.GPU} Using GPU acceleration (NVIDIA)"
    
    @staticmethod
    def cpu_processing(preset: str = None, crf: str = None, threads: str = None) -> str:
        """CPU processing message"""
        details = []
        if preset:
            details.append(f"preset={preset}")
        if crf:
            details.append(f"crf={crf}")
        if threads:
            details.append(f"threads={threads}")
        
        detail_str = f" ({', '.join(details)})" if details else ""
        return f"{LogEmojis.CPU} Using CPU encoding{detail_str}"
    
    @staticmethod
    def analyzing_media(media_type: str) -> str:
        """Analyzing media message"""
        return f"{LogEmojis.ANALYZE} Analyzing {media_type}..."