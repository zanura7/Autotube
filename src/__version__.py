"""
Autotube Version Information
"""

__version__ = "1.0.0"
__version_info__ = (1, 0, 0)

# Release information
__author__ = "Autotube Contributors"
__license__ = "MIT"
__description__ = "Desktop tool for automating long-form YouTube content creation"

# GitHub repository for updates
GITHUB_REPO = "zanura7/Autotube"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"


def get_version() -> str:
    """Get current version string"""
    return __version__


def get_version_info() -> tuple:
    """Get version info as tuple"""
    return __version_info__


def version_string() -> str:
    """Get formatted version string"""
    return f"Autotube v{__version__}"
