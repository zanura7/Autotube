"""
Unit tests for downloader backend
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call, mock_open
from pathlib import Path
import subprocess
from concurrent.futures import Future
from backend.downloader import Downloader


class TestDownloaderInit:
    """Test Downloader initialization"""

    def test_init_creates_output_folder(self, tmp_path):
        """Test that output folder is created on init"""
        output_folder = tmp_path / "downloads"
        downloader = Downloader(output_folder)

        assert output_folder.exists()
        assert downloader.output_folder == output_folder
        assert downloader.downloaded_files == []

    def test_init_with_existing_folder(self, tmp_path):
        """Test initialization with existing folder"""
        output_folder = tmp_path / "downloads"
        output_folder.mkdir()

        downloader = Downloader(output_folder)
        assert downloader.output_folder == output_folder

    def test_init_with_console_log(self, tmp_path):
        """Test initialization with console log"""
        mock_console = Mock()
        downloader = Downloader(tmp_path, console_log=mock_console)

        assert downloader.console_log is mock_console

    def test_init_creates_nested_folders(self, tmp_path):
        """Test that nested folders are created"""
        output_folder = tmp_path / "nested" / "folders" / "downloads"
        downloader = Downloader(output_folder)

        assert output_folder.exists()


class TestLogging:
    """Test logging functionality"""

    def test_log_info_with_console(self, tmp_path):
        """Test logging info with console"""
        mock_console = Mock()
        downloader = Downloader(tmp_path, console_log=mock_console)

        downloader.log("Test message", "INFO")
        mock_console.log_info.assert_called_once_with("Test message")

    def test_log_error_with_console(self, tmp_path):
        """Test logging error with console"""
        mock_console = Mock()
        downloader = Downloader(tmp_path, console_log=mock_console)

        downloader.log("Error message", "ERROR")
        mock_console.log_error.assert_called_once_with("Error message")

    def test_log_warning_with_console(self, tmp_path):
        """Test logging warning with console"""
        mock_console = Mock()
        downloader = Downloader(tmp_path, console_log=mock_console)

        downloader.log("Warning message", "WARNING")
        mock_console.log_warning.assert_called_once_with("Warning message")

    def test_log_success_with_console(self, tmp_path):
        """Test logging success with console"""
        mock_console = Mock()
        downloader = Downloader(tmp_path, console_log=mock_console)

        downloader.log("Success message", "SUCCESS")
        mock_console.log_success.assert_called_once_with("Success message")

    def test_log_without_console(self, tmp_path, capsys):
        """Test logging without console (prints to stdout)"""
        downloader = Downloader(tmp_path, console_log=None)

        downloader.log("Test message", "INFO")
        captured = capsys.readouterr()
        assert "[INFO] Test message" in captured.out


class TestGetYdlOptions:
    """Test yt-dlp options generation"""

    def test_get_ydl_options_mp3_320(self, tmp_path):
        """Test MP3 320kbps options"""
        downloader = Downloader(tmp_path)
        opts = downloader._get_ydl_options("mp3_320")

        assert "format" in opts
        assert opts["format"] == "bestaudio/best"
        assert "postprocessors" in opts
        assert opts["postprocessors"][0]["key"] == "FFmpegExtractAudio"
        assert opts["postprocessors"][0]["preferredcodec"] == "mp3"
        assert opts["postprocessors"][0]["preferredquality"] == "320"

    def test_get_ydl_options_mp3_128(self, tmp_path):
        """Test MP3 128kbps options"""
        downloader = Downloader(tmp_path)
        opts = downloader._get_ydl_options("mp3_128")

        assert opts["format"] == "bestaudio/best"
        assert opts["postprocessors"][0]["preferredquality"] == "128"

    def test_get_ydl_options_video_best(self, tmp_path):
        """Test best video options"""
        downloader = Downloader(tmp_path)
        opts = downloader._get_ydl_options("video_best")

        assert opts["format"] == "bestvideo+bestaudio/best"
        assert opts["merge_output_format"] == "mp4"

    def test_get_ydl_options_has_outtmpl(self, tmp_path):
        """Test that all options have output template"""
        downloader = Downloader(tmp_path)

        for format_type in ["mp3_320", "mp3_128", "video_best"]:
            opts = downloader._get_ydl_options(format_type)
            assert "outtmpl" in opts
            assert str(tmp_path) in opts["outtmpl"]


class TestDownloadSingle:
    """Test single download functionality"""

    def test_download_single_mp3_success(self, tmp_path, mocker):
        """Test successful single MP3 download"""
        downloader = Downloader(tmp_path)

        mock_ydl_instance = Mock()
        mock_info = {"title": "Test Video", "ext": "webm"}
        mock_ydl_instance.extract_info.return_value = mock_info
        mock_ydl_instance.prepare_filename.return_value = str(tmp_path / "Test Video.webm")
        mock_ydl_instance.download.return_value = None

        mock_ydl = mocker.patch('yt_dlp.YoutubeDL')
        mock_ydl.return_value.__enter__.return_value = mock_ydl_instance

        result = downloader.download_single(
            "https://www.youtube.com/watch?v=test",
            format_type="mp3_320"
        )

        # Should return MP3 path
        assert result.suffix == ".mp3"
        assert result.stem == "Test Video"

        # Should call yt-dlp methods
        mock_ydl_instance.extract_info.assert_called_once()
        mock_ydl_instance.download.assert_called_once()

    def test_download_single_video_success(self, tmp_path, mocker):
        """Test successful single video download"""
        downloader = Downloader(tmp_path)

        mock_ydl_instance = Mock()
        mock_info = {"title": "Test Video", "ext": "mp4"}
        mock_ydl_instance.extract_info.return_value = mock_info
        mock_ydl_instance.prepare_filename.return_value = str(tmp_path / "Test Video.mp4")
        mock_ydl_instance.download.return_value = None

        mock_ydl = mocker.patch('yt_dlp.YoutubeDL')
        mock_ydl.return_value.__enter__.return_value = mock_ydl_instance

        result = downloader.download_single(
            "https://www.youtube.com/watch?v=test",
            format_type="video_best"
        )

        # Should return MP4 path (no suffix change for video)
        assert result.suffix == ".mp4"


class TestNormalizeAudio:
    """Test audio normalization"""

    def test_normalize_audio_success(self, tmp_path, mocker):
        """Test successful audio normalization"""
        downloader = Downloader(tmp_path)

        # Create fake audio file
        audio_file = tmp_path / "test.mp3"
        audio_file.touch()

        # Mock subprocess.run
        mock_run = mocker.patch('subprocess.run')

        # Create fake normalized file
        normalized_file = tmp_path / "test.normalized.mp3"

        def side_effect(*args, **kwargs):
            normalized_file.touch()

        mock_run.side_effect = side_effect

        result = downloader.normalize_audio(audio_file)

        assert result is True
        mock_run.assert_called_once()

        # Check FFmpeg command
        call_args = mock_run.call_args[0][0]
        assert "ffmpeg" in call_args
        assert "-af" in call_args
        assert any("loudnorm" in str(arg) for arg in call_args)

    def test_normalize_audio_subprocess_error(self, tmp_path, mocker):
        """Test normalization with subprocess error"""
        mock_console = Mock()
        downloader = Downloader(tmp_path, console_log=mock_console)

        audio_file = tmp_path / "test.mp3"
        audio_file.touch()

        mocker.patch(
            'subprocess.run',
            side_effect=subprocess.CalledProcessError(1, "ffmpeg", stderr="Error")
        )

        result = downloader.normalize_audio(audio_file)

        assert result is False
        mock_console.log_warning.assert_called()

    def test_normalize_audio_timeout(self, tmp_path, mocker):
        """Test normalization with timeout"""
        mock_console = Mock()
        downloader = Downloader(tmp_path, console_log=mock_console)

        audio_file = tmp_path / "test.mp3"
        audio_file.touch()

        mocker.patch(
            'subprocess.run',
            side_effect=subprocess.TimeoutExpired("ffmpeg", 300)
        )

        result = downloader.normalize_audio(audio_file)

        assert result is False
        mock_console.log_warning.assert_called()

    def test_normalize_audio_cleans_temp_on_error(self, tmp_path, mocker):
        """Test that temp file is cleaned up on error"""
        downloader = Downloader(tmp_path)

        audio_file = tmp_path / "test.mp3"
        audio_file.touch()

        # Create temp file that should be cleaned up
        temp_file = tmp_path / "test.normalized.mp3"

        def side_effect(*args, **kwargs):
            temp_file.touch()
            raise subprocess.CalledProcessError(1, "ffmpeg")

        mocker.patch('subprocess.run', side_effect=side_effect)

        result = downloader.normalize_audio(audio_file)

        assert result is False
        # Temp file should be cleaned up
        assert not temp_file.exists()

    def test_normalize_audio_replaces_original(self, tmp_path, mocker):
        """Test that normalized file replaces original"""
        downloader = Downloader(tmp_path)

        audio_file = tmp_path / "test.mp3"
        audio_file.write_text("original")

        normalized_file = tmp_path / "test.normalized.mp3"

        def side_effect(*args, **kwargs):
            normalized_file.write_text("normalized")

        mock_run = mocker.patch('subprocess.run', side_effect=side_effect)

        result = downloader.normalize_audio(audio_file)

        assert result is True
        # Original should now have normalized content
        assert audio_file.read_text() == "normalized"
        # Temp file should be gone
        assert not normalized_file.exists()


class TestGeneratePlaylist:
    """Test playlist generation"""

    def test_generate_playlist_success(self, tmp_path):
        """Test successful playlist generation"""
        downloader = Downloader(tmp_path)

        # Create fake downloaded files
        file1 = tmp_path / "song1.mp3"
        file2 = tmp_path / "song2.mp3"
        file3 = tmp_path / "song3.m4a"
        file1.touch()
        file2.touch()
        file3.touch()

        downloader.downloaded_files = [file1, file2, file3]

        playlist = downloader.generate_playlist()

        assert playlist is not None
        assert playlist.exists()
        assert playlist.suffix == ".m3u"

        # Check playlist content
        content = playlist.read_text(encoding="utf-8")
        assert "#EXTM3U" in content
        assert "song1.mp3" in content
        assert "song2.mp3" in content
        assert "song3.m4a" in content

    def test_generate_playlist_with_video_files(self, tmp_path):
        """Test playlist generation skips video files"""
        downloader = Downloader(tmp_path)

        # Mix of audio and video files
        audio1 = tmp_path / "song.mp3"
        video1 = tmp_path / "video.mp4"
        audio2 = tmp_path / "track.wav"

        audio1.touch()
        video1.touch()
        audio2.touch()

        downloader.downloaded_files = [audio1, video1, audio2]

        playlist = downloader.generate_playlist()

        assert playlist is not None

        # Should only include audio files
        content = playlist.read_text(encoding="utf-8")
        assert "song.mp3" in content
        assert "track.wav" in content
        assert "video.mp4" not in content

    def test_generate_playlist_no_files(self, tmp_path):
        """Test playlist generation with no files"""
        mock_console = Mock()
        downloader = Downloader(tmp_path, console_log=mock_console)

        downloader.downloaded_files = []

        playlist = downloader.generate_playlist()

        assert playlist is None
        mock_console.log_warning.assert_called()

    def test_generate_playlist_no_audio_files(self, tmp_path):
        """Test playlist generation with no audio files"""
        mock_console = Mock()
        downloader = Downloader(tmp_path, console_log=mock_console)

        # Only video files
        video1 = tmp_path / "video.mp4"
        video1.touch()

        downloader.downloaded_files = [video1]

        playlist = downloader.generate_playlist()

        assert playlist is None
        mock_console.log_warning.assert_called()

    def test_generate_playlist_includes_metadata(self, tmp_path):
        """Test playlist includes EXTINF metadata"""
        downloader = Downloader(tmp_path)

        audio = tmp_path / "My Song Title.mp3"
        audio.touch()

        downloader.downloaded_files = [audio]

        playlist = downloader.generate_playlist()

        content = playlist.read_text(encoding="utf-8")
        assert "#EXTINF:-1,My Song Title" in content

    def test_generate_playlist_uses_relative_paths(self, tmp_path):
        """Test playlist uses relative paths"""
        downloader = Downloader(tmp_path)

        audio = tmp_path / "song.mp3"
        audio.touch()

        downloader.downloaded_files = [audio]

        playlist = downloader.generate_playlist()

        content = playlist.read_text(encoding="utf-8")
        # Should use relative path, not absolute
        assert "song.mp3" in content
        assert str(tmp_path) not in content.split("#EXTM3U")[1]  # Not in file paths


class TestDownloadBatch:
    """Test batch download functionality"""

    def test_download_batch_validates_urls(self, tmp_path, mocker):
        """Test that batch download validates URLs"""
        mock_console = Mock()
        downloader = Downloader(tmp_path, console_log=mock_console)

        # Mock validate_youtube_url
        mock_validate = mocker.patch(
            'backend.downloader.validate_youtube_url',
            side_effect=[True, False, True]  # First valid, second invalid, third valid
        )

        # Mock download_single to avoid actual download
        mocker.patch.object(downloader, 'download_single', return_value=None)

        urls = [
            "https://www.youtube.com/watch?v=valid1",
            "https://invalid.com/video",
            "https://www.youtube.com/watch?v=valid2"
        ]

        downloader.download_batch(urls, max_concurrent=1)

        # Should validate all URLs
        assert mock_validate.call_count == 3

        # Should log warning for invalid URL
        warning_logged = any(
            "invalid" in str(call).lower()
            for call in mock_console.log_warning.call_args_list
        )
        assert warning_logged

    def test_download_batch_no_valid_urls(self, tmp_path, mocker):
        """Test batch download with no valid URLs"""
        mock_console = Mock()
        downloader = Downloader(tmp_path, console_log=mock_console)

        mocker.patch('backend.downloader.validate_youtube_url', return_value=False)

        urls = ["https://invalid.com/video1", "https://invalid.com/video2"]

        result = downloader.download_batch(urls)

        assert result is False
        mock_console.log_error.assert_called()

    def test_download_batch_limits_concurrency(self, tmp_path, mocker):
        """Test that batch download limits max concurrent downloads"""
        downloader = Downloader(tmp_path)

        mocker.patch('backend.downloader.validate_youtube_url', return_value=True)

        # Mock ThreadPoolExecutor to check max_workers
        mock_executor_class = mocker.patch('concurrent.futures.ThreadPoolExecutor')
        mock_executor = Mock()
        mock_executor.__enter__ = Mock(return_value=mock_executor)
        mock_executor.__exit__ = Mock(return_value=None)
        mock_executor.submit = Mock(return_value=Future())
        mock_executor_class.return_value = mock_executor

        # Mock as_completed to return empty
        mocker.patch('concurrent.futures.as_completed', return_value=[])

        urls = ["https://www.youtube.com/watch?v=test1"]

        # Test max limit (should cap at 5)
        downloader.download_batch(urls, max_concurrent=10)
        assert mock_executor_class.call_args[1]['max_workers'] == 5

        # Test min limit (should be at least 1)
        downloader.download_batch(urls, max_concurrent=0)
        assert mock_executor_class.call_args[1]['max_workers'] == 1

    def test_download_batch_concurrent_execution(self, tmp_path, mocker):
        """Test that batch download executes concurrently"""
        downloader = Downloader(tmp_path)

        mocker.patch('backend.downloader.validate_youtube_url', return_value=True)

        # Create mock files
        file1 = tmp_path / "video1.mp3"
        file2 = tmp_path / "video2.mp3"
        file1.touch()
        file2.touch()

        # Mock download_single to return files
        mocker.patch.object(
            downloader,
            'download_single',
            side_effect=[file1, file2]
        )

        # Mock normalize_audio
        mocker.patch.object(downloader, 'normalize_audio', return_value=True)

        urls = [
            "https://www.youtube.com/watch?v=test1",
            "https://www.youtube.com/watch?v=test2"
        ]

        result = downloader.download_batch(
            urls,
            format_type="mp3_320",
            normalize=False,
            max_concurrent=2
        )

        assert result is True
        assert len(downloader.downloaded_files) == 2

    def test_download_batch_with_normalization(self, tmp_path, mocker):
        """Test batch download with audio normalization"""
        downloader = Downloader(tmp_path)

        mocker.patch('backend.downloader.validate_youtube_url', return_value=True)

        # Create mock file
        audio_file = tmp_path / "audio.mp3"
        audio_file.touch()

        mocker.patch.object(downloader, 'download_single', return_value=audio_file)
        mock_normalize = mocker.patch.object(downloader, 'normalize_audio', return_value=True)

        urls = ["https://www.youtube.com/watch?v=test"]

        result = downloader.download_batch(
            urls,
            format_type="mp3_320",
            normalize=True,
            max_concurrent=1
        )

        assert result is True
        # Should call normalize_audio
        assert mock_normalize.called

    def test_download_batch_skips_normalization_for_video(self, tmp_path, mocker):
        """Test that normalization is skipped for video downloads"""
        downloader = Downloader(tmp_path)

        mocker.patch('backend.downloader.validate_youtube_url', return_value=True)

        video_file = tmp_path / "video.mp4"
        video_file.touch()

        mocker.patch.object(downloader, 'download_single', return_value=video_file)
        mock_normalize = mocker.patch.object(downloader, 'normalize_audio', return_value=True)

        urls = ["https://www.youtube.com/watch?v=test"]

        downloader.download_batch(
            urls,
            format_type="video_best",
            normalize=True,  # Requested but should be skipped
            max_concurrent=1
        )

        # Should NOT call normalize_audio for video
        assert not mock_normalize.called

    def test_download_batch_with_progress_callback(self, tmp_path, mocker):
        """Test batch download with progress callback"""
        downloader = Downloader(tmp_path)

        mocker.patch('backend.downloader.validate_youtube_url', return_value=True)

        file1 = tmp_path / "video1.mp3"
        file1.touch()

        mocker.patch.object(downloader, 'download_single', return_value=file1)
        mocker.patch.object(downloader, 'normalize_audio', return_value=True)

        mock_progress = Mock()

        urls = ["https://www.youtube.com/watch?v=test"]

        downloader.download_batch(
            urls,
            normalize=False,
            progress_callback=mock_progress,
            max_concurrent=1
        )

        # Progress callback should be called
        assert mock_progress.called

        # Should call with (completed, total, message)
        call_args = mock_progress.call_args_list
        assert len(call_args) > 0

    def test_download_batch_handles_download_failure(self, tmp_path, mocker):
        """Test batch download handles individual download failures"""
        mock_console = Mock()
        downloader = Downloader(tmp_path, console_log=mock_console)

        mocker.patch('backend.downloader.validate_youtube_url', return_value=True)

        # Mock download_single to fail
        mocker.patch.object(downloader, 'download_single', return_value=None)

        urls = ["https://www.youtube.com/watch?v=test"]

        result = downloader.download_batch(urls, max_concurrent=1)

        # Should log warning but not crash
        assert any(
            "failed" in str(call).lower() or "not found" in str(call).lower()
            for call in mock_console.log_warning.call_args_list
        )

    def test_download_batch_handles_exceptions(self, tmp_path, mocker):
        """Test batch download handles exceptions gracefully"""
        mock_console = Mock()
        downloader = Downloader(tmp_path, console_log=mock_console)

        mocker.patch('backend.downloader.validate_youtube_url', return_value=True)

        # Mock download_single to raise exception
        mocker.patch.object(
            downloader,
            'download_single',
            side_effect=Exception("Download error")
        )

        urls = ["https://www.youtube.com/watch?v=test"]

        result = downloader.download_batch(urls, max_concurrent=1)

        # Should handle error gracefully
        mock_console.log_error.assert_called()

    def test_download_batch_cleans_partial_downloads(self, tmp_path, mocker):
        """Test that partial downloads are cleaned up on error"""
        downloader = Downloader(tmp_path)

        mocker.patch('backend.downloader.validate_youtube_url', return_value=True)

        # Create fake partial file
        partial_file = tmp_path / "video.mp4.part"
        partial_file.touch()

        # Mock download_single to raise exception
        mocker.patch.object(
            downloader,
            'download_single',
            side_effect=Exception("Download error")
        )

        urls = ["https://www.youtube.com/watch?v=test"]

        downloader.download_batch(urls, max_concurrent=1)

        # Partial file should be cleaned up
        assert not partial_file.exists()

    def test_download_batch_thread_safe_counter(self, tmp_path, mocker):
        """Test that download counter is thread-safe"""
        downloader = Downloader(tmp_path)

        mocker.patch('backend.downloader.validate_youtube_url', return_value=True)

        # Create multiple mock files
        files = []
        for i in range(3):
            f = tmp_path / f"video{i}.mp3"
            f.touch()
            files.append(f)

        mocker.patch.object(
            downloader,
            'download_single',
            side_effect=files
        )

        mocker.patch.object(downloader, 'normalize_audio', return_value=True)

        urls = [
            "https://www.youtube.com/watch?v=test1",
            "https://www.youtube.com/watch?v=test2",
            "https://www.youtube.com/watch?v=test3"
        ]

        result = downloader.download_batch(
            urls,
            normalize=False,
            max_concurrent=3
        )

        assert result is True
        # All files should be tracked
        assert len(downloader.downloaded_files) == 3

    def test_download_batch_resets_downloaded_files(self, tmp_path, mocker):
        """Test that downloaded_files list is reset on each batch"""
        downloader = Downloader(tmp_path)

        mocker.patch('backend.downloader.validate_youtube_url', return_value=True)

        file1 = tmp_path / "video1.mp3"
        file1.touch()

        mocker.patch.object(downloader, 'download_single', return_value=file1)
        mocker.patch.object(downloader, 'normalize_audio', return_value=True)

        # First batch
        downloader.download_batch(
            ["https://www.youtube.com/watch?v=test1"],
            normalize=False,
            max_concurrent=1
        )

        assert len(downloader.downloaded_files) == 1

        # Second batch should reset
        downloader.download_batch(
            ["https://www.youtube.com/watch?v=test2"],
            normalize=False,
            max_concurrent=1
        )

        # Should still be 1 (not 2)
        assert len(downloader.downloaded_files) == 1

    def test_download_batch_logs_summary(self, tmp_path, mocker):
        """Test that batch download logs summary"""
        mock_console = Mock()
        downloader = Downloader(tmp_path, console_log=mock_console)

        mocker.patch('backend.downloader.validate_youtube_url', return_value=True)

        file1 = tmp_path / "video1.mp3"
        file2 = tmp_path / "video2.mp3"
        file1.touch()
        file2.touch()

        mocker.patch.object(
            downloader,
            'download_single',
            side_effect=[file1, file2]
        )

        mocker.patch.object(downloader, 'normalize_audio', return_value=True)

        urls = [
            "https://www.youtube.com/watch?v=test1",
            "https://www.youtube.com/watch?v=test2"
        ]

        downloader.download_batch(urls, normalize=False, max_concurrent=2)

        # Should log success summary
        success_logged = any(
            "complete" in str(call).lower() and "2" in str(call)
            for call in mock_console.log_success.call_args_list
        )
        assert success_logged


class TestDownloadBatchIntegration:
    """Integration tests for batch download"""

    def test_full_download_workflow(self, tmp_path, mocker):
        """Test complete download workflow from URLs to playlist"""
        downloader = Downloader(tmp_path)

        mocker.patch('backend.downloader.validate_youtube_url', return_value=True)

        # Create mock audio files
        audio1 = tmp_path / "Song 1.mp3"
        audio2 = tmp_path / "Song 2.mp3"
        audio1.touch()
        audio2.touch()

        mocker.patch.object(
            downloader,
            'download_single',
            side_effect=[audio1, audio2]
        )

        mocker.patch.object(downloader, 'normalize_audio', return_value=True)

        urls = [
            "https://www.youtube.com/watch?v=test1",
            "https://www.youtube.com/watch?v=test2"
        ]

        # Download batch
        result = downloader.download_batch(
            urls,
            format_type="mp3_320",
            normalize=True,
            max_concurrent=2
        )

        assert result is True
        assert len(downloader.downloaded_files) == 2

        # Generate playlist
        playlist = downloader.generate_playlist()

        assert playlist is not None
        assert playlist.exists()

        content = playlist.read_text(encoding="utf-8")
        assert "Song 1.mp3" in content
        assert "Song 2.mp3" in content
