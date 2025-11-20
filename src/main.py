#!/usr/bin/env python3
"""
Autotube - Desktop tool for automating long-form YouTube content creation
Main entry point
"""

import sys
import os
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from ui.main_window import MainWindow
from utils.ffmpeg_checker import check_ffmpeg
from utils.config_manager import ConfigManager
from utils.file_logger import init_file_logger, close_file_logger
from utils.notifications import init_notifier
from __version__ import __version__, GITHUB_REPO
from utils.auto_updater import check_for_updates_simple


def main():
    """Main entry point for the application"""

    # Initialize configuration manager
    config = ConfigManager()

    # Initialize file logger
    general_settings = config.get_general_settings()
    file_logger = None

    if general_settings.get("log_to_file", True):
        file_logger = init_file_logger(
            max_size_mb=general_settings.get("max_log_file_size_mb", 10),
            max_files=general_settings.get("max_log_files", 5),
            log_level=general_settings.get("log_level", "INFO"),
        )
        file_logger.log_section("Autotube Application Started")
        file_logger.info("Configuration loaded successfully")

    # Initialize notification system
    notifier = init_notifier(enabled=general_settings.get("show_notifications", True))

    # Check if FFmpeg is installed
    if not check_ffmpeg():
        error_msg = "FFmpeg tidak ditemukan!"
        print(f"\n❌ ERROR: {error_msg}")
        print("Silakan install FFmpeg terlebih dahulu:")
        print("  - Windows: Download dari gyan.dev, extract, dan tambahkan ke PATH")
        print("  - Linux: sudo apt install ffmpeg")
        print("  - Mac: brew install ffmpeg\n")

        if file_logger:
            file_logger.error(error_msg)
            file_logger.error("FFmpeg installation required but not found")

        sys.exit(1)

    print("✅ FFmpeg terdeteksi!")
    print(f"📦 Autotube v{__version__}")

    if file_logger:
        file_logger.info("FFmpeg detected successfully")
        file_logger.info(f"Autotube version: {__version__}")
        file_logger.info(f"Config file: {config.get_config_file_path()}")
        file_logger.info(f"Log file: {file_logger.get_log_file_path()}")

    # Check for updates (if enabled in config)
    check_updates = general_settings.get("check_for_updates", True)
    if check_updates:
        print("🔍 Checking for updates...")
        if file_logger:
            file_logger.info("Checking for updates...")

        try:
            has_update, latest_version = check_for_updates_simple(__version__, GITHUB_REPO)
            if has_update:
                print(f"✨ New version available: v{latest_version} (current: v{__version__})")
                if file_logger:
                    file_logger.info(f"Update available: v{latest_version}")

                # Show notification
                if notifier:
                    try:
                        from utils.notifications import notify_success
                        notify_success(
                            "Update Available",
                            f"Autotube v{latest_version} is available!"
                        )
                    except:
                        pass
            else:
                print("✅ You're using the latest version")
                if file_logger:
                    file_logger.info("Application is up to date")
        except Exception as e:
            print(f"⚠️  Could not check for updates: {e}")
            if file_logger:
                file_logger.warning(f"Update check failed: {e}")

    print("🚀 Memulai Autotube...\n")

    try:
        # Create and run the main window (pass config and version to it)
        app = MainWindow(config=config, version=__version__)
        app.run()

    except KeyboardInterrupt:
        print("\n\n⏹️ Application interrupted by user")
        if file_logger:
            file_logger.info("Application interrupted by user (Ctrl+C)")

    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        if file_logger:
            file_logger.error(f"Unexpected error: {e}")
        raise

    finally:
        # Cleanup
        if file_logger:
            file_logger.log_section("Autotube Application Ended")
            close_file_logger()
        print("\n👋 Autotube closed")


if __name__ == "__main__":
    main()
