"""
Application Constants
Centralized configuration values to replace magic numbers throughout the codebase
"""

# =============================================================================
# TIMEOUT CONSTANTS (in seconds)
# =============================================================================

# FFmpeg operation timeouts
TIMEOUT_FFMPEG_VERSION_CHECK = 5       # FFmpeg version check
TIMEOUT_AUDIO_CONCAT = 300             # 5 minutes for audio concatenation
TIMEOUT_VIDEO_CONCAT = 600             # 10 minutes for video concatenation  
TIMEOUT_VIDEO_RENDER = 14400           # 4 hours for final video rendering
TIMEOUT_SLIDESHOW = 300                # 5 minutes for slideshow creation
TIMEOUT_SUBPROCESS_DEFAULT = 10        # Default subprocess timeout

# =============================================================================
# RESOURCE LIMITS
# =============================================================================

# File processing limits
MAX_AUDIO_FILES = 10                   # Maximum audio files to process at once
MAX_VIDEO_FILES = 10                   # Maximum video files to process at once
MAX_IMAGE_FILES = 20                   # Maximum images for slideshow
MAX_SIMPLE_FILES = 5                   # Maximum files for simple processing methods

# Multi-image mixer limits (Advanced Image Mixer feature)
MAX_MULTI_IMAGES = 100                 # Maximum images for advanced mixer
MAX_MULTI_AUDIO = 50                   # Maximum audio files for advanced mixer
IMAGES_PER_CHUNK = 15                  # Images per FFmpeg command chunk (to avoid command line length limits)

# =============================================================================
# MULTI-IMAGE EFFECT ROTATION MODES
# =============================================================================

# Effect rotation modes for multi-image mixer
ROTATION_MODE_SEQUENTIAL = "sequential"  # Cycle through effects in order
ROTATION_MODE_RANDOM = "random"         # Random effect selection
ROTATION_MODE_MIXED = "mixed"           # Weighted random selection

# Effect types for multi-image mixer
EFFECT_TYPE_ZOOM = "zoom"               # Zoom in effect
EFFECT_TYPE_PAN = "pan"                 # Pan movement effect
EFFECT_TYPE_FADE = "fade"               # Fade in/out effect
EFFECT_TYPE_NONE = "none"               # No effect

# Effect weights for mixed rotation mode
EFFECT_WEIGHT_ZOOM = 0.40               # 40% zoom
EFFECT_WEIGHT_PAN = 0.35                # 35% pan
EFFECT_WEIGHT_FADE = 0.25               # 25% fade

# Pan directions
PAN_DIRECTION_LEFT_TO_RIGHT = "left_to_right"
PAN_DIRECTION_RIGHT_TO_LEFT = "right_to_left"
PAN_DIRECTION_TOP_TO_BOTTOM = "top_to_bottom"
PAN_DIRECTION_BOTTOM_TO_TOP = "bottom_to_top"
PAN_DIRECTION_DIAGONAL = "diagonal"

# =============================================================================
# TRANSITION TYPES
# =============================================================================

TRANSITION_TYPE_CROSSFADE = "crossfade"  # Smooth crossfade transition
TRANSITION_TYPE_FADE = "fade"            # Simple fade transition
TRANSITION_TYPE_NONE = "none"            # No transition

# =============================================================================
# VIDEO QUALITY SETTINGS
# =============================================================================

# Resolution presets
RESOLUTION_4K = "3840x2160"            # 4K Ultra HD
RESOLUTION_FHD = "1920x1080"           # Full HD 1080p
RESOLUTION_HD = "1280x720"             # HD 720p
RESOLUTION_SD = "640x480"              # Standard Definition
RESOLUTION_TEST = "320x240"            # Test/Debug resolution

# Default resolutions
DEFAULT_RESOLUTION = RESOLUTION_FHD    # Default output resolution
DEFAULT_TEST_RESOLUTION = RESOLUTION_SD # Default test resolution

# Video encoding settings
VIDEO_CRF_DEFAULT = 23                 # Default CRF value for video quality
VIDEO_PRESET_DEFAULT = "medium"        # Default FFmpeg preset

# =============================================================================
# AUDIO QUALITY SETTINGS
# =============================================================================

# Audio bitrates
AUDIO_BITRATE_HIGH = "256k"            # High quality audio
AUDIO_BITRATE_STANDARD = "192k"        # Standard quality audio
AUDIO_BITRATE_LOW = "128k"             # Low quality audio

# Audio sample rates
AUDIO_SAMPLE_RATE_HIGH = "48000"       # Professional audio sample rate
AUDIO_SAMPLE_RATE_STANDARD = "44100"   # CD quality sample rate

# Audio channels
AUDIO_CHANNELS_STEREO = "2"            # Stereo audio
AUDIO_CHANNELS_MONO = "1"              # Mono audio

# Default audio settings
DEFAULT_AUDIO_BITRATE = AUDIO_BITRATE_STANDARD
DEFAULT_AUDIO_SAMPLE_RATE = AUDIO_SAMPLE_RATE_HIGH
DEFAULT_AUDIO_CHANNELS = AUDIO_CHANNELS_STEREO

# =============================================================================
# TEST CONSTANTS
# =============================================================================

# Test durations (in seconds)
TEST_DURATION_SHORT = 1                # Short test clips
TEST_DURATION_MEDIUM = 3               # Medium test clips
TEST_DURATION_LONG = 5                 # Long test clips

# Test frequencies (for sine wave generation)
TEST_FREQUENCY_BASE = 440              # Base frequency (A4 note)
TEST_FREQUENCY_STEP = 100              # Frequency step for multiple tones

# Test colors
TEST_COLORS = ["red", "blue", "green"] # Colors for test video generation

# =============================================================================
# UI CONSTANTS
# =============================================================================

# Progress display
PROGRESS_DECIMAL_PLACES = 1            # Decimal places for progress percentage

# Log message limits
LOG_RECENT_MESSAGES_COUNT = 5          # Number of recent log messages to check

# =============================================================================
# FILE SIZE CONSTANTS
# =============================================================================

# File size conversion
BYTES_PER_MB = 1024 * 1024            # Bytes in a megabyte
BYTES_PER_KB = 1024                   # Bytes in a kilobyte

# =============================================================================
# DEFAULT DURATIONS
# =============================================================================

# Default processing durations
DEFAULT_LOOP_DURATION_MINUTES = 60     # Default loop duration in minutes
DEFAULT_CROSSFADE_SECONDS = 1.0        # Default crossfade duration in seconds
DEFAULT_IMAGE_DURATION_SECONDS = 2.0   # Default image duration in slideshow

# =============================================================================
# VALIDATION CONSTANTS
# =============================================================================

# String formatting
SEPARATOR_LENGTH = 50                  # Length of separator lines in output

# =============================================================================
# AUDIO NORMALIZATION CONSTANTS
# =============================================================================

# Loudness normalization settings (EBU R128 standard)
LOUDNORM_INTEGRATED = -16              # Integrated loudness target (LUFS)
LOUDNORM_TRUE_PEAK = -1.5              # True peak target (dBTP)
LOUDNORM_LRA = 11                      # Loudness range target (LU)