"""
Auto-Update System
Check for updates, download, and install new versions
"""

import os
import sys
import platform
import requests
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Callable
from packaging import version
import json
import hashlib


class AutoUpdater:
    """Handle application auto-updates"""

    def __init__(self, current_version: str, github_repo: str):
        """
        Initialize auto-updater

        Args:
            current_version: Current application version (e.g., "1.0.0")
            github_repo: GitHub repository (e.g., "username/repo")
        """
        self.current_version = current_version
        self.github_repo = github_repo
        self.api_url = f"https://api.github.com/repos/{github_repo}/releases/latest"
        self.platform = platform.system()  # Windows, Linux, Darwin (macOS)
        self.is_frozen = getattr(sys, 'frozen', False)  # Running as executable

    def check_for_updates(self, timeout: int = 5) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        Check if a new version is available

        Args:
            timeout: Request timeout in seconds

        Returns:
            Tuple of (has_update, latest_version, release_info)
        """
        try:
            response = requests.get(self.api_url, timeout=timeout)
            response.raise_for_status()

            release_data = response.json()

            # Get latest version (remove 'v' prefix if present)
            latest_version = release_data["tag_name"].lstrip("v")

            # Compare versions
            if version.parse(latest_version) > version.parse(self.current_version):
                return True, latest_version, release_data

            return False, self.current_version, None

        except requests.RequestException as e:
            print(f"Error checking for updates: {e}")
            return False, None, None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False, None, None

    def get_download_asset(self, release_data: dict) -> Optional[dict]:
        """
        Get the appropriate download asset for current platform

        Args:
            release_data: GitHub release data

        Returns:
            Asset dict or None if not found
        """
        assets = release_data.get("assets", [])

        # Platform-specific asset names
        asset_patterns = {
            "Windows": ["windows", "win", ".exe"],
            "Linux": ["linux", "ubuntu", "debian"],
            "Darwin": ["macos", "darwin", "osx"],  # macOS
        }

        patterns = asset_patterns.get(self.platform, [])

        # Find matching asset
        for asset in assets:
            asset_name = asset["name"].lower()
            if any(pattern.lower() in asset_name for pattern in patterns):
                return asset

        # If no platform-specific asset, try generic
        for asset in assets:
            if "autotube" in asset["name"].lower():
                return asset

        return None

    def download_update(
        self,
        download_url: str,
        filename: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Optional[Path]:
        """
        Download update file

        Args:
            download_url: URL to download from
            filename: Filename for downloaded file
            progress_callback: Callback(downloaded_bytes, total_bytes)

        Returns:
            Path to downloaded file or None on failure
        """
        try:
            # Create temp directory
            temp_dir = Path(tempfile.gettempdir()) / "autotube_update"
            temp_dir.mkdir(parents=True, exist_ok=True)

            download_path = temp_dir / filename

            # Download with progress
            response = requests.get(download_url, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        if progress_callback:
                            progress_callback(downloaded_size, total_size)

            return download_path

        except Exception as e:
            print(f"Error downloading update: {e}")
            return None

    def verify_download(self, file_path: Path, expected_checksum: Optional[str] = None) -> bool:
        """
        Verify downloaded file integrity

        Args:
            file_path: Path to downloaded file
            expected_checksum: Expected SHA256 checksum (optional)

        Returns:
            True if verification passed
        """
        if not file_path.exists():
            return False

        # Basic file size check
        if file_path.stat().st_size < 1024:  # Less than 1KB is suspicious
            return False

        # If checksum provided, verify it
        if expected_checksum:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)

            actual_checksum = sha256_hash.hexdigest()
            return actual_checksum.lower() == expected_checksum.lower()

        return True

    def backup_current_version(self) -> Optional[Path]:
        """
        Create backup of current executable

        Returns:
            Path to backup file or None
        """
        try:
            if not self.is_frozen:
                # Not running as executable, skip backup
                return None

            current_exe = Path(sys.executable)
            backup_path = current_exe.with_suffix('.backup')

            shutil.copy2(current_exe, backup_path)
            return backup_path

        except Exception as e:
            print(f"Error creating backup: {e}")
            return None

    def install_update(self, update_file: Path) -> bool:
        """
        Install the downloaded update

        Args:
            update_file: Path to update file

        Returns:
            True if installation successful
        """
        try:
            if not self.is_frozen:
                print("Cannot auto-update when running from source")
                return False

            # Create backup
            backup_path = self.backup_current_version()

            current_exe = Path(sys.executable)

            # Platform-specific installation
            if self.platform == "Windows":
                return self._install_windows(update_file, current_exe, backup_path)
            else:
                return self._install_unix(update_file, current_exe, backup_path)

        except Exception as e:
            print(f"Error installing update: {e}")
            return False

    def _install_windows(self, update_file: Path, current_exe: Path, backup_path: Optional[Path]) -> bool:
        """Install update on Windows"""
        try:
            # Create batch script to replace executable after app exits
            batch_script = current_exe.parent / "update_autotube.bat"

            script_content = f"""@echo off
echo Updating Autotube...
timeout /t 2 /nobreak >nul
move /y "{update_file}" "{current_exe}"
if exist "{backup_path}" del "{backup_path}"
start "" "{current_exe}"
del "%~f0"
"""

            with open(batch_script, 'w') as f:
                f.write(script_content)

            # Start batch script and exit current process
            subprocess.Popen(
                ['cmd', '/c', str(batch_script)],
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            return True

        except Exception as e:
            print(f"Windows installation error: {e}")
            return False

    def _install_unix(self, update_file: Path, current_exe: Path, backup_path: Optional[Path]) -> bool:
        """Install update on Linux/macOS"""
        try:
            # Make update file executable
            os.chmod(update_file, 0o755)

            # Create shell script to replace executable after app exits
            shell_script = current_exe.parent / "update_autotube.sh"

            script_content = f"""#!/bin/bash
sleep 2
mv -f "{update_file}" "{current_exe}"
chmod +x "{current_exe}"
rm -f "{backup_path}"
"{current_exe}" &
rm -f "$0"
"""

            with open(shell_script, 'w') as f:
                f.write(script_content)

            os.chmod(shell_script, 0o755)

            # Start shell script and exit
            subprocess.Popen([str(shell_script)])

            return True

        except Exception as e:
            print(f"Unix installation error: {e}")
            return False

    def rollback_update(self, backup_path: Path) -> bool:
        """
        Rollback to previous version from backup

        Args:
            backup_path: Path to backup file

        Returns:
            True if rollback successful
        """
        try:
            if not backup_path.exists():
                return False

            current_exe = Path(sys.executable)
            shutil.copy2(backup_path, current_exe)
            backup_path.unlink()

            return True

        except Exception as e:
            print(f"Error rolling back: {e}")
            return False

    def perform_update(
        self,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Tuple[bool, str]:
        """
        Perform complete update process

        Args:
            progress_callback: Callback(status_message, percentage)

        Returns:
            Tuple of (success, message)
        """
        try:
            # Step 1: Check for updates
            if progress_callback:
                progress_callback("Checking for updates...", 10)

            has_update, latest_version, release_data = self.check_for_updates()

            if not has_update:
                return False, "No updates available"

            # Step 2: Get download asset
            if progress_callback:
                progress_callback("Preparing download...", 20)

            asset = self.get_download_asset(release_data)
            if not asset:
                return False, "No compatible download found for your platform"

            # Step 3: Download update
            if progress_callback:
                progress_callback("Downloading update...", 30)

            def download_progress(downloaded, total):
                if progress_callback and total > 0:
                    percentage = 30 + int((downloaded / total) * 50)
                    progress_callback(f"Downloading... {downloaded}/{total} bytes", percentage)

            update_file = self.download_update(
                asset["browser_download_url"],
                asset["name"],
                download_progress
            )

            if not update_file:
                return False, "Download failed"

            # Step 4: Verify download
            if progress_callback:
                progress_callback("Verifying download...", 85)

            if not self.verify_download(update_file):
                return False, "Download verification failed"

            # Step 5: Install update
            if progress_callback:
                progress_callback("Installing update...", 90)

            if self.install_update(update_file):
                if progress_callback:
                    progress_callback("Update complete!", 100)
                return True, f"Successfully updated to version {latest_version}. Restarting..."
            else:
                return False, "Installation failed"

        except Exception as e:
            return False, f"Update error: {str(e)}"


def check_for_updates_simple(current_version: str, github_repo: str) -> Tuple[bool, Optional[str]]:
    """
    Simple update check without full updater

    Args:
        current_version: Current version string
        github_repo: GitHub repository

    Returns:
        Tuple of (has_update, latest_version)
    """
    updater = AutoUpdater(current_version, github_repo)
    has_update, latest_version, _ = updater.check_for_updates()
    return has_update, latest_version
