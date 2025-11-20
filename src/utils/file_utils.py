"""
File utility functions
"""

import os
import platform
import subprocess
from pathlib import Path


def open_folder(folder_path):
    """
    Open folder in file manager

    Args:
        folder_path: Path to folder to open
    """
    folder_path = Path(folder_path)

    # Create folder if it doesn't exist
    folder_path.mkdir(parents=True, exist_ok=True)

    # Open based on OS
    system = platform.system()

    try:
        if system == "Windows":
            os.startfile(folder_path)
        elif system == "Darwin":  # macOS
            subprocess.run(["open", str(folder_path)])
        else:  # Linux
            subprocess.run(["xdg-open", str(folder_path)])

        return True
    except Exception as e:
        print(f"Error opening folder: {e}")
        return False
