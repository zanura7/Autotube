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


def main():
    """Main entry point for the application"""

    # Check if FFmpeg is installed
    if not check_ffmpeg():
        print("\n❌ ERROR: FFmpeg tidak ditemukan!")
        print("Silakan install FFmpeg terlebih dahulu:")
        print("  - Windows: Download dari gyan.dev, extract, dan tambahkan ke PATH")
        print("  - Linux: sudo apt install ffmpeg")
        print("  - Mac: brew install ffmpeg\n")
        sys.exit(1)

    print("✅ FFmpeg terdeteksi!")
    print("🚀 Memulai Autotube...\n")

    # Create and run the main window
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
