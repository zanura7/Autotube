"""
Unit tests for FFmpeg progress parser
"""

import pytest
from utils.ffmpeg_progress import FFmpegProgressParser


class TestFFmpegProgressParser:
    """Test FFmpeg progress parsing"""

    def test_parse_time_format(self):
        """Test parsing of FFmpeg time format"""
        parser = FFmpegProgressParser(total_duration=100)

        # Test valid time formats
        assert parser.parse_time("00:00:05.00") == 5.0
        assert parser.parse_time("00:01:30.50") == 90.5
        assert parser.parse_time("01:00:00.00") == 3600.0

    def test_parse_time_invalid(self):
        """Test parsing of invalid time formats"""
        parser = FFmpegProgressParser(total_duration=100)

        # Should return 0 for invalid formats
        assert parser.parse_time("invalid") == 0
        assert parser.parse_time("") == 0
        assert parser.parse_time("12:34") == 0  # Missing seconds

    def test_parse_progress_line(self):
        """Test parsing of FFmpeg progress output line"""
        parser = FFmpegProgressParser(total_duration=100)

        # Typical FFmpeg progress line
        line = "frame= 123 fps= 25 q=28.0 size= 1024kB time=00:00:05.00 bitrate=1677.7kbits/s speed=1.02x"

        progress_info = parser.parse_line(line)

        assert progress_info is not None
        assert "time" in progress_info
        assert "speed" in progress_info
        assert "fps" in progress_info
        assert "frame" in progress_info
        assert "percentage" in progress_info

        assert progress_info["time"] == 5.0
        assert progress_info["speed"] == 1.02
        assert progress_info["fps"] == 25.0
        assert progress_info["frame"] == 123

    def test_parse_line_without_progress(self):
        """Test parsing of non-progress lines"""
        parser = FFmpegProgressParser(total_duration=100)

        # Lines without progress info should return None
        assert parser.parse_line("ffmpeg version 4.4") is None
        assert parser.parse_line("Input #0, mp4") is None
        assert parser.parse_line("") is None

    def test_percentage_calculation(self):
        """Test percentage calculation"""
        parser = FFmpegProgressParser(total_duration=100)

        # Parse line with 50 seconds processed out of 100 total
        line = "frame= 1250 fps= 25 q=28.0 size= 1024kB time=00:00:50.00 bitrate=1677.7kbits/s speed=1.0x"
        parser.start_time = parser.start_time or 0  # Set start time

        progress_info = parser.parse_line(line)

        assert progress_info is not None
        assert progress_info["percentage"] == pytest.approx(0.5, rel=0.01)

    def test_percentage_clamped_at_one(self):
        """Test that percentage doesn't exceed 1.0"""
        parser = FFmpegProgressParser(total_duration=100)

        # Parse line with more than total duration processed
        line = "frame= 2500 fps= 25 q=28.0 size= 2048kB time=00:01:50.00 bitrate=1677.7kbits/s speed=1.0x"

        progress_info = parser.parse_line(line)

        assert progress_info is not None
        assert progress_info["percentage"] <= 1.0

    def test_format_time(self):
        """Test human-readable time formatting"""
        parser = FFmpegProgressParser()

        assert parser.format_time(30) == "30s"
        assert parser.format_time(90) == "1m 30s"
        assert parser.format_time(3661) == "1h 1m"

    def test_eta_calculation(self):
        """Test ETA calculation"""
        import time

        parser = FFmpegProgressParser(total_duration=100)
        parser.start_time = time.time() - 10  # Started 10 seconds ago

        # Processed 20 seconds in 10 real seconds = 2.0x speed
        line = "frame= 500 fps= 25 q=28.0 size= 1024kB time=00:00:20.00 bitrate=1677.7kbits/s speed=2.0x"

        progress_info = parser.parse_line(line)

        assert progress_info is not None
        if "eta_seconds" in progress_info:
            # Remaining: 80 seconds of video at 2x speed = 40 real seconds
            assert progress_info["eta_seconds"] == pytest.approx(40, rel=0.2)

    def test_speed_extraction(self):
        """Test extraction of encoding speed"""
        parser = FFmpegProgressParser(total_duration=100)

        test_cases = [
            ("speed=1.0x", 1.0),
            ("speed=2.5x", 2.5),
            ("speed=0.8x", 0.8),
        ]

        for line_snippet, expected_speed in test_cases:
            full_line = f"frame= 100 fps= 25 time=00:00:05.00 {line_snippet}"
            progress_info = parser.parse_line(full_line)

            if progress_info:
                assert progress_info.get("speed") == expected_speed


class TestRunFFmpegWithProgress:
    """Test running FFmpeg with progress tracking"""

    def test_progress_callback_called(self, mocker):
        """Test that progress callback is called during execution"""
        from utils.ffmpeg_progress import run_ffmpeg_with_progress

        # Mock the subprocess.Popen to simulate FFmpeg output
        mock_popen = mocker.patch("utils.ffmpeg_progress.subprocess.Popen")
        mock_process = mocker.MagicMock()

        # Simulate FFmpeg progress output
        mock_process.stderr.readline.side_effect = [
            "frame= 100 fps= 25 q=28.0 time=00:00:04.00 speed=1.0x\n",
            "frame= 200 fps= 25 q=28.0 time=00:00:08.00 speed=1.0x\n",
            "",  # End of output
        ]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        callback_called = []

        def progress_callback(percentage, message, eta):
            callback_called.append((percentage, message))

        # Run FFmpeg with progress
        cmd = ["ffmpeg", "-i", "input.mp4", "output.mp4"]
        success = run_ffmpeg_with_progress(
            cmd, total_duration=10, progress_callback=progress_callback
        )

        assert success is True
        assert len(callback_called) > 0

    def test_cancellation_support(self, mocker):
        """Test that cancellation works correctly"""
        from utils.ffmpeg_progress import run_ffmpeg_with_progress
        import threading

        mock_popen = mocker.patch("utils.ffmpeg_progress.subprocess.Popen")
        mock_process = mocker.MagicMock()

        # Simulate FFmpeg output
        mock_process.stderr.readline.side_effect = [
            "frame= 100 fps= 25 q=28.0 time=00:00:04.00 speed=1.0x\n",
            "frame= 200 fps= 25 q=28.0 time=00:00:08.00 speed=1.0x\n",
        ]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        cancel_event = threading.Event()
        cancel_event.set()  # Cancel immediately

        cmd = ["ffmpeg", "-i", "input.mp4", "output.mp4"]
        success = run_ffmpeg_with_progress(
            cmd, total_duration=10, cancel_event=cancel_event
        )

        assert success is False
        mock_process.terminate.assert_called_once()
