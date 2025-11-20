"""
Unit tests for auto-updater system
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
from utils.auto_updater import AutoUpdater, check_for_updates_simple


class TestAutoUpdater:
    """Test AutoUpdater class"""

    def test_init(self):
        """Test AutoUpdater initialization"""
        updater = AutoUpdater("1.0.0", "user/repo")

        assert updater.current_version == "1.0.0"
        assert updater.github_repo == "user/repo"
        assert "api.github.com" in updater.api_url

    def test_check_for_updates_newer_available(self, mocker):
        """Test when newer version is available"""
        updater = AutoUpdater("1.0.0", "user/repo")

        # Mock response from GitHub API
        mock_response = Mock()
        mock_response.json.return_value = {
            "tag_name": "v1.1.0",
            "body": "New features",
        }
        mock_response.raise_for_status = Mock()

        mocker.patch("requests.get", return_value=mock_response)

        has_update, latest_version, release_data = updater.check_for_updates()

        assert has_update is True
        assert latest_version == "1.1.0"
        assert release_data is not None

    def test_check_for_updates_no_update(self, mocker):
        """Test when already on latest version"""
        updater = AutoUpdater("1.1.0", "user/repo")

        mock_response = Mock()
        mock_response.json.return_value = {
            "tag_name": "v1.1.0",
            "body": "Current version",
        }
        mock_response.raise_for_status = Mock()

        mocker.patch("requests.get", return_value=mock_response)

        has_update, latest_version, release_data = updater.check_for_updates()

        assert has_update is False
        assert latest_version == "1.1.0"

    def test_check_for_updates_network_error(self, mocker):
        """Test network error handling"""
        updater = AutoUpdater("1.0.0", "user/repo")

        mocker.patch("requests.get", side_effect=Exception("Network error"))

        has_update, latest_version, release_data = updater.check_for_updates()

        assert has_update is False
        assert latest_version is None
        assert release_data is None

    def test_get_download_asset_windows(self):
        """Test getting Windows asset"""
        updater = AutoUpdater("1.0.0", "user/repo")
        updater.platform = "Windows"

        release_data = {
            "assets": [
                {"name": "app-linux", "browser_download_url": "url1"},
                {"name": "app-windows.exe", "browser_download_url": "url2"},
                {"name": "app-macos", "browser_download_url": "url3"},
            ]
        }

        asset = updater.get_download_asset(release_data)

        assert asset is not None
        assert "windows" in asset["name"].lower()

    def test_get_download_asset_linux(self):
        """Test getting Linux asset"""
        updater = AutoUpdater("1.0.0", "user/repo")
        updater.platform = "Linux"

        release_data = {
            "assets": [
                {"name": "app-linux", "browser_download_url": "url1"},
                {"name": "app-windows.exe", "browser_download_url": "url2"},
            ]
        }

        asset = updater.get_download_asset(release_data)

        assert asset is not None
        assert "linux" in asset["name"].lower()

    def test_get_download_asset_not_found(self):
        """Test when no matching asset found"""
        updater = AutoUpdater("1.0.0", "user/repo")
        updater.platform = "UnknownOS"

        release_data = {"assets": []}

        asset = updater.get_download_asset(release_data)

        # Should return None or fallback to generic
        assert asset is None

    def test_download_update_success(self, mocker, tmp_path):
        """Test successful download"""
        updater = AutoUpdater("1.0.0", "user/repo")

        # Mock response
        mock_response = Mock()
        mock_response.headers = {"content-length": "1024"}
        mock_response.iter_content = Mock(
            return_value=[b"chunk1", b"chunk2", b"chunk3"]
        )
        mock_response.raise_for_status = Mock()

        mocker.patch("requests.get", return_value=mock_response)

        progress_calls = []

        def progress_callback(downloaded, total):
            progress_calls.append((downloaded, total))

        download_path = updater.download_update(
            "http://example.com/file.exe",
            "test.exe",
            progress_callback
        )

        assert download_path is not None
        assert download_path.exists()
        assert len(progress_calls) > 0

    def test_download_update_failure(self, mocker):
        """Test download failure"""
        updater = AutoUpdater("1.0.0", "user/repo")

        mocker.patch("requests.get", side_effect=Exception("Download failed"))

        download_path = updater.download_update(
            "http://example.com/file.exe",
            "test.exe"
        )

        assert download_path is None

    def test_verify_download_valid_file(self, tmp_path):
        """Test file verification with valid file"""
        updater = AutoUpdater("1.0.0", "user/repo")

        test_file = tmp_path / "test.exe"
        test_file.write_bytes(b"a" * 2048)  # 2KB file

        is_valid = updater.verify_download(test_file)

        assert is_valid is True

    def test_verify_download_too_small(self, tmp_path):
        """Test file verification with too small file"""
        updater = AutoUpdater("1.0.0", "user/repo")

        test_file = tmp_path / "test.exe"
        test_file.write_bytes(b"tiny")  # Less than 1KB

        is_valid = updater.verify_download(test_file)

        assert is_valid is False

    def test_verify_download_nonexistent(self):
        """Test file verification with non-existent file"""
        updater = AutoUpdater("1.0.0", "user/repo")

        is_valid = updater.verify_download(Path("/nonexistent/file.exe"))

        assert is_valid is False

    def test_verify_download_with_checksum_valid(self, tmp_path):
        """Test file verification with valid checksum"""
        updater = AutoUpdater("1.0.0", "user/repo")

        test_file = tmp_path / "test.exe"
        # Create content > 1000 bytes (minimum size requirement)
        content = b"test content for checksum validation " * 50  # > 1000 bytes
        test_file.write_bytes(content)

        # Calculate actual checksum
        import hashlib
        expected_checksum = hashlib.sha256(content).hexdigest()

        is_valid = updater.verify_download(test_file, expected_checksum)

        assert is_valid is True

    def test_verify_download_with_checksum_invalid(self, tmp_path):
        """Test file verification with invalid checksum"""
        updater = AutoUpdater("1.0.0", "user/repo")

        test_file = tmp_path / "test.exe"
        test_file.write_bytes(b"test content")

        wrong_checksum = "0" * 64  # Invalid checksum

        is_valid = updater.verify_download(test_file, wrong_checksum)

        assert is_valid is False

    def test_backup_current_version_not_frozen(self):
        """Test backup when not running as executable"""
        updater = AutoUpdater("1.0.0", "user/repo")
        updater.is_frozen = False

        backup_path = updater.backup_current_version()

        # Should return None when not frozen
        assert backup_path is None

    def test_backup_current_version_frozen(self, mocker, tmp_path):
        """Test backup when running as executable"""
        updater = AutoUpdater("1.0.0", "user/repo")
        updater.is_frozen = True

        # Mock sys.executable
        test_exe = tmp_path / "app.exe"
        test_exe.write_text("executable content")

        mocker.patch("sys.executable", str(test_exe))

        backup_path = updater.backup_current_version()

        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.suffix == ".backup"


class TestCheckForUpdatesSimple:
    """Test simple update check function"""

    def test_update_available(self, mocker):
        """Test simple check with update available"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "tag_name": "v2.0.0",
        }
        mock_response.raise_for_status = Mock()

        mocker.patch("requests.get", return_value=mock_response)

        has_update, latest_version = check_for_updates_simple("1.0.0", "user/repo")

        assert has_update is True
        assert latest_version == "2.0.0"

    def test_no_update_available(self, mocker):
        """Test simple check with no update"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "tag_name": "v1.0.0",
        }
        mock_response.raise_for_status = Mock()

        mocker.patch("requests.get", return_value=mock_response)

        has_update, latest_version = check_for_updates_simple("1.0.0", "user/repo")

        assert has_update is False

    def test_network_error(self, mocker):
        """Test simple check with network error"""
        mocker.patch("requests.get", side_effect=Exception("Network error"))

        has_update, latest_version = check_for_updates_simple("1.0.0", "user/repo")

        assert has_update is False
        assert latest_version is None


class TestVersionComparison:
    """Test version comparison logic"""

    def test_newer_version_detected(self, mocker):
        """Test that newer versions are detected correctly"""
        updater = AutoUpdater("1.0.0", "user/repo")

        test_cases = [
            ("1.0.1", True),   # Patch update
            ("1.1.0", True),   # Minor update
            ("2.0.0", True),   # Major update
            ("1.0.0", False),  # Same version
            ("0.9.0", False),  # Older version
        ]

        for new_version, should_update in test_cases:
            mock_response = Mock()
            mock_response.json.return_value = {
                "tag_name": f"v{new_version}",
            }
            mock_response.raise_for_status = Mock()

            mocker.patch("requests.get", return_value=mock_response)

            has_update, _, _ = updater.check_for_updates()

            assert has_update == should_update, f"Failed for version {new_version}"
