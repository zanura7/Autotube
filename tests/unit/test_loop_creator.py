"""
Unit tests for loop creator backend
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import threading
from backend.loop_creator import LoopCreator


class TestLoopCreatorInit:
    """Test LoopCreator initialization"""

    def test_init_creates_output_folder(self, tmp_path):
        """Test that output folder is created on init"""
        output_folder = tmp_path / "output"
        creator = LoopCreator(output_folder)

        assert output_folder.exists()
        assert creator.output_folder == output_folder

    def test_init_with_existing_folder(self, tmp_path):
        """Test initialization with existing folder"""
        output_folder = tmp_path / "output"
        output_folder.mkdir()

        creator = LoopCreator(output_folder)
        assert creator.output_folder == output_folder

    def test_init_with_console_log(self, tmp_path):
        """Test initialization with console log"""
        mock_console = Mock()
        creator = LoopCreator(tmp_path, console_log=mock_console)

        assert creator.console_log is mock_console

    def test_init_creates_nested_folders(self, tmp_path):
        """Test that nested folders are created"""
        output_folder = tmp_path / "nested" / "folders" / "output"
        creator = LoopCreator(output_folder)

        assert output_folder.exists()


class TestLogging:
    """Test logging functionality"""

    def test_log_info_with_console(self, tmp_path):
        """Test logging info with console"""
        mock_console = Mock()
        creator = LoopCreator(tmp_path, console_log=mock_console)

        creator.log("Test message", "INFO")
        mock_console.log_info.assert_called_once_with("Test message")

    def test_log_error_with_console(self, tmp_path):
        """Test logging error with console"""
        mock_console = Mock()
        creator = LoopCreator(tmp_path, console_log=mock_console)

        creator.log("Error message", "ERROR")
        mock_console.log_error.assert_called_once_with("Error message")

    def test_log_warning_with_console(self, tmp_path):
        """Test logging warning with console"""
        mock_console = Mock()
        creator = LoopCreator(tmp_path, console_log=mock_console)

        creator.log("Warning message", "WARNING")
        mock_console.log_warning.assert_called_once_with("Warning message")

    def test_log_success_with_console(self, tmp_path):
        """Test logging success with console"""
        mock_console = Mock()
        creator = LoopCreator(tmp_path, console_log=mock_console)

        creator.log("Success message", "SUCCESS")
        mock_console.log_success.assert_called_once_with("Success message")

    def test_log_without_console(self, tmp_path, capsys):
        """Test logging without console (prints to stdout)"""
        creator = LoopCreator(tmp_path, console_log=None)

        creator.log("Test message", "INFO")
        captured = capsys.readouterr()
        assert "[INFO] Test message" in captured.out


class TestGetVideoInfo:
    """Test video info extraction"""

    def test_get_video_info_success(self, tmp_path):
        """Test successful video info extraction"""
        creator = LoopCreator(tmp_path)

        mock_probe_result = {
            "streams": [
                {
                    "codec_type": "video",
                    "duration": "10.5",
                    "r_frame_rate": "30/1",
                    "width": 1920,
                    "height": 1080
                }
            ],
            "format": {
                "duration": "10.5"
            }
        }

        with patch('ffmpeg.probe', return_value=mock_probe_result):
            info = creator.get_video_info(Path("/fake/video.mp4"))

            assert info["duration"] == 10.5
            assert info["fps"] == 30.0
            assert info["width"] == 1920
            assert info["height"] == 1080

    def test_get_video_info_with_fractional_fps(self, tmp_path):
        """Test video info with fractional FPS (e.g., 29.97)"""
        creator = LoopCreator(tmp_path)

        mock_probe_result = {
            "streams": [
                {
                    "codec_type": "video",
                    "duration": "10.0",
                    "r_frame_rate": "30000/1001",
                    "width": 1280,
                    "height": 720
                }
            ],
            "format": {"duration": "10.0"}
        }

        with patch('ffmpeg.probe', return_value=mock_probe_result):
            info = creator.get_video_info(Path("/fake/video.mp4"))

            assert abs(info["fps"] - 29.97) < 0.01

    def test_get_video_info_no_video_stream(self, tmp_path):
        """Test error when no video stream found"""
        creator = LoopCreator(tmp_path)

        mock_probe_result = {
            "streams": [
                {"codec_type": "audio"}
            ],
            "format": {"duration": "10.0"}
        }

        with patch('ffmpeg.probe', return_value=mock_probe_result):
            with pytest.raises(ValueError, match="No video stream found"):
                creator.get_video_info(Path("/fake/video.mp4"))

    def test_get_video_info_probe_fails(self, tmp_path):
        """Test error when probe fails"""
        creator = LoopCreator(tmp_path)

        with patch('ffmpeg.probe', side_effect=Exception("Probe failed")):
            with pytest.raises(ValueError, match="Failed to get video info"):
                creator.get_video_info(Path("/fake/video.mp4"))

    def test_get_video_info_duration_from_format(self, tmp_path):
        """Test getting duration from format when not in stream"""
        creator = LoopCreator(tmp_path)

        mock_probe_result = {
            "streams": [
                {
                    "codec_type": "video",
                    "r_frame_rate": "30/1",
                    "width": 1920,
                    "height": 1080
                }
            ],
            "format": {
                "duration": "15.5"
            }
        }

        with patch('ffmpeg.probe', return_value=mock_probe_result):
            info = creator.get_video_info(Path("/fake/video.mp4"))
            assert info["duration"] == 15.5


class TestGetAudioDuration:
    """Test audio duration extraction"""

    def test_get_audio_duration_success(self, tmp_path):
        """Test successful audio duration extraction"""
        creator = LoopCreator(tmp_path)

        mock_probe_result = {
            "format": {"duration": "120.5"}
        }

        with patch('ffmpeg.probe', return_value=mock_probe_result):
            duration = creator.get_audio_duration(Path("/fake/audio.mp3"))
            assert duration == 120.5

    def test_get_audio_duration_fails(self, tmp_path):
        """Test audio duration when probe fails"""
        creator = LoopCreator(tmp_path)

        with patch('ffmpeg.probe', side_effect=Exception("Probe failed")):
            duration = creator.get_audio_duration(Path("/fake/audio.mp3"))
            assert duration == 0


class TestCreateCrossfadeClip:
    """Test crossfade clip creation"""

    def test_create_crossfade_success(self, tmp_path, mocker):
        """Test successful crossfade creation"""
        creator = LoopCreator(tmp_path)

        # Mock get_video_info
        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 10.0, "fps": 30, "width": 1920, "height": 1080}
        )

        # Mock run_ffmpeg_with_progress
        mock_run_ffmpeg = mocker.patch(
            'backend.loop_creator.run_ffmpeg_with_progress',
            return_value=True
        )

        result = creator.create_crossfade_clip(
            Path("/fake/video.mp4"),
            crossfade_duration=1.0
        )

        # Should create temp file
        assert result.name.startswith("temp_crossfade_")
        assert mock_run_ffmpeg.called

    def test_create_crossfade_duration_too_long(self, tmp_path, mocker):
        """Test crossfade when duration > half video length"""
        mock_console = Mock()
        creator = LoopCreator(tmp_path, console_log=mock_console)

        # Video is 5 seconds, crossfade requested is 4 seconds (too long)
        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 5.0, "fps": 30, "width": 1920, "height": 1080}
        )

        mocker.patch(
            'backend.loop_creator.run_ffmpeg_with_progress',
            return_value=True
        )

        creator.create_crossfade_clip(
            Path("/fake/video.mp4"),
            crossfade_duration=4.0
        )

        # Should log warning about adjustment
        warning_logged = any(
            call[0][1] == "WARNING" for call in mock_console.log_warning.call_args_list
        )
        assert warning_logged or mock_console.log_warning.called

    def test_create_crossfade_with_progress_callback(self, tmp_path, mocker):
        """Test crossfade with progress callback"""
        creator = LoopCreator(tmp_path)

        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 10.0, "fps": 30, "width": 1920, "height": 1080}
        )

        mock_progress = Mock()

        def mock_ffmpeg_progress(cmd, total_duration, progress_callback, cancel_event, log_callback):
            # Simulate progress updates
            if progress_callback:
                progress_callback(0.5, "Processing", 10)
            return True

        mocker.patch(
            'backend.loop_creator.run_ffmpeg_with_progress',
            side_effect=mock_ffmpeg_progress
        )

        creator.create_crossfade_clip(
            Path("/fake/video.mp4"),
            crossfade_duration=1.0,
            progress_callback=mock_progress
        )

        # Progress callback should have been called
        assert mock_progress.called

    def test_create_crossfade_cancelled(self, tmp_path, mocker):
        """Test crossfade with cancellation"""
        creator = LoopCreator(tmp_path)

        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 10.0, "fps": 30, "width": 1920, "height": 1080}
        )

        # Mock cancellation
        mocker.patch(
            'backend.loop_creator.run_ffmpeg_with_progress',
            return_value=False
        )

        video_path = Path("/fake/video.mp4")
        result = creator.create_crossfade_clip(
            video_path,
            crossfade_duration=1.0
        )

        # Should return original video on failure
        assert result == video_path

    def test_create_crossfade_exception(self, tmp_path, mocker):
        """Test crossfade with exception"""
        mock_console = Mock()
        creator = LoopCreator(tmp_path, console_log=mock_console)

        mocker.patch.object(
            creator,
            'get_video_info',
            side_effect=Exception("Video info failed")
        )

        video_path = Path("/fake/video.mp4")
        result = creator.create_crossfade_clip(video_path, 1.0)

        # Should return original video on error
        assert result == video_path
        mock_console.log_error.assert_called()


class TestConcatenateLoops:
    """Test video concatenation/looping"""

    def test_concatenate_loops_success(self, tmp_path, mocker):
        """Test successful loop concatenation"""
        creator = LoopCreator(tmp_path)

        # Mock get_video_info
        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 10.0, "fps": 30, "width": 1920, "height": 1080}
        )

        # Mock subprocess.run
        mock_run = mocker.patch('subprocess.run')

        result = creator.concatenate_loops(
            Path("/fake/video.mp4"),
            loops=3,
            target_duration=30
        )

        # Should create temp file
        assert result.name.startswith("temp_looped_")

        # Should call FFmpeg concat
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "-f" in call_args
        assert "concat" in call_args

    def test_concatenate_loops_creates_concat_file(self, tmp_path, mocker):
        """Test that concat list file is created"""
        creator = LoopCreator(tmp_path)

        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 10.0, "fps": 30, "width": 1920, "height": 1080}
        )

        mocker.patch('subprocess.run')

        creator.concatenate_loops(
            Path("/fake/video.mp4"),
            loops=2,
            target_duration=20
        )

        # concat_list.txt should have been created and removed
        concat_file = tmp_path / "concat_list.txt"
        # File should be cleaned up, but we can check subprocess was called
        assert not concat_file.exists()  # Cleaned up

    def test_concatenate_loops_subprocess_error(self, tmp_path, mocker):
        """Test concatenation with subprocess error"""
        mock_console = Mock()
        creator = LoopCreator(tmp_path, console_log=mock_console)

        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 10.0, "fps": 30, "width": 1920, "height": 1080}
        )

        # Mock subprocess failure
        import subprocess
        mocker.patch(
            'subprocess.run',
            side_effect=subprocess.CalledProcessError(1, "ffmpeg", stderr="Error")
        )

        video_path = Path("/fake/video.mp4")
        result = creator.concatenate_loops(video_path, 3, 30)

        # Should return original video on error
        assert result == video_path
        mock_console.log_error.assert_called()

    def test_concatenate_loops_general_exception(self, tmp_path, mocker):
        """Test concatenation with general exception"""
        mock_console = Mock()
        creator = LoopCreator(tmp_path, console_log=mock_console)

        mocker.patch.object(
            creator,
            'get_video_info',
            side_effect=Exception("Info failed")
        )

        video_path = Path("/fake/video.mp4")
        result = creator.concatenate_loops(video_path, 3, 30)

        assert result == video_path
        mock_console.log_error.assert_called()


class TestScaleVideo:
    """Test video scaling"""

    def test_scale_video_original_returns_same(self, tmp_path):
        """Test that Original resolution returns same video"""
        creator = LoopCreator(tmp_path)

        video_path = Path("/fake/video.mp4")
        result = creator.scale_video(video_path, "Original")

        assert result == video_path

    def test_scale_video_success(self, tmp_path, mocker):
        """Test successful video scaling"""
        creator = LoopCreator(tmp_path)

        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 10.0, "fps": 30, "width": 1920, "height": 1080}
        )

        mocker.patch(
            'backend.loop_creator.run_ffmpeg_with_progress',
            return_value=True
        )

        result = creator.scale_video(
            Path("/fake/video.mp4"),
            resolution="1280x720"
        )

        # Should create temp file
        assert result.name.startswith("temp_scaled_")

    def test_scale_video_with_gpu(self, tmp_path, mocker):
        """Test video scaling with GPU"""
        creator = LoopCreator(tmp_path)

        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 10.0, "fps": 30, "width": 1920, "height": 1080}
        )

        mock_run_ffmpeg = mocker.patch(
            'backend.loop_creator.run_ffmpeg_with_progress',
            return_value=True
        )

        creator.scale_video(
            Path("/fake/video.mp4"),
            resolution="1280x720",
            use_gpu=True
        )

        # Should use scale_cuda filter
        call_args = mock_run_ffmpeg.call_args[0][0]
        assert any("scale_cuda" in str(arg) for arg in call_args)

    def test_scale_video_with_cpu(self, tmp_path, mocker):
        """Test video scaling with CPU"""
        creator = LoopCreator(tmp_path)

        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 10.0, "fps": 30, "width": 1920, "height": 1080}
        )

        mock_run_ffmpeg = mocker.patch(
            'backend.loop_creator.run_ffmpeg_with_progress',
            return_value=True
        )

        creator.scale_video(
            Path("/fake/video.mp4"),
            resolution="1280x720",
            use_gpu=False
        )

        # Should use regular scale filter with padding
        call_args = mock_run_ffmpeg.call_args[0][0]
        assert any("scale=1280:720" in str(arg) for arg in call_args)

    def test_scale_video_with_progress_callback(self, tmp_path, mocker):
        """Test scaling with progress callback"""
        creator = LoopCreator(tmp_path)

        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 10.0, "fps": 30, "width": 1920, "height": 1080}
        )

        mock_progress = Mock()

        def mock_ffmpeg_progress(cmd, total_duration, progress_callback, cancel_event, log_callback):
            if progress_callback:
                progress_callback(0.5, "Processing", 10)
            return True

        mocker.patch(
            'backend.loop_creator.run_ffmpeg_with_progress',
            side_effect=mock_ffmpeg_progress
        )

        creator.scale_video(
            Path("/fake/video.mp4"),
            resolution="1280x720",
            progress_callback=mock_progress
        )

        assert mock_progress.called

    def test_scale_video_fails(self, tmp_path, mocker):
        """Test scaling failure"""
        mock_console = Mock()
        creator = LoopCreator(tmp_path, console_log=mock_console)

        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 10.0, "fps": 30, "width": 1920, "height": 1080}
        )

        mocker.patch(
            'backend.loop_creator.run_ffmpeg_with_progress',
            return_value=False
        )

        video_path = Path("/fake/video.mp4")
        result = creator.scale_video(video_path, "1280x720")

        assert result == video_path
        mock_console.log_error.assert_called()


class TestAddAudio:
    """Test audio replacement"""

    def test_add_audio_success_with_short_audio(self, tmp_path, mocker):
        """Test adding audio that's shorter than video (needs looping)"""
        creator = LoopCreator(tmp_path)

        # Audio is 30s, video is 60s
        mocker.patch.object(creator, 'get_audio_duration', return_value=30.0)
        mock_run = mocker.patch('subprocess.run')

        result = creator.add_audio(
            Path("/fake/video.mp4"),
            Path("/fake/audio.mp3"),
            duration=60
        )

        # Should create temp file
        assert result.name.startswith("temp_audio_")

        # Should call FFmpeg with aloop filter
        call_args = mock_run.call_args[0][0]
        assert any("aloop" in str(arg) for arg in call_args)

    def test_add_audio_success_with_long_audio(self, tmp_path, mocker):
        """Test adding audio that's longer than video (needs trimming)"""
        creator = LoopCreator(tmp_path)

        # Audio is 120s, video is 60s
        mocker.patch.object(creator, 'get_audio_duration', return_value=120.0)
        mock_run = mocker.patch('subprocess.run')

        result = creator.add_audio(
            Path("/fake/video.mp4"),
            Path("/fake/audio.mp3"),
            duration=60
        )

        # Should create temp file
        assert result.name.startswith("temp_audio_")

        # Should call FFmpeg with atrim filter only
        call_args = mock_run.call_args[0][0]
        assert any("atrim" in str(arg) for arg in call_args)
        # Should not have aloop
        assert not any("aloop" in str(arg) for arg in call_args if "atrim" not in str(arg))

    def test_add_audio_subprocess_error(self, tmp_path, mocker):
        """Test audio addition with subprocess error"""
        mock_console = Mock()
        creator = LoopCreator(tmp_path, console_log=mock_console)

        mocker.patch.object(creator, 'get_audio_duration', return_value=60.0)

        import subprocess
        mocker.patch(
            'subprocess.run',
            side_effect=subprocess.CalledProcessError(1, "ffmpeg", stderr="Error")
        )

        video_path = Path("/fake/video.mp4")
        result = creator.add_audio(video_path, Path("/fake/audio.mp3"), 60)

        assert result == video_path
        mock_console.log_error.assert_called()

    def test_add_audio_general_exception(self, tmp_path, mocker):
        """Test audio addition with general exception"""
        mock_console = Mock()
        creator = LoopCreator(tmp_path, console_log=mock_console)

        mocker.patch.object(
            creator,
            'get_audio_duration',
            side_effect=Exception("Duration failed")
        )

        video_path = Path("/fake/video.mp4")
        result = creator.add_audio(video_path, Path("/fake/audio.mp3"), 60)

        assert result == video_path
        mock_console.log_error.assert_called()


class TestRenderFinal:
    """Test final video rendering"""

    def test_render_final_cpu_success(self, tmp_path, mocker):
        """Test successful CPU rendering"""
        creator = LoopCreator(tmp_path)

        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 60.0, "fps": 30, "width": 1920, "height": 1080}
        )

        mock_output = tmp_path / "output.mp4"
        mock_output.touch()

        mock_run_ffmpeg = mocker.patch(
            'backend.loop_creator.run_ffmpeg_with_progress',
            return_value=True
        )

        result = creator.render_final(
            Path("/fake/input.mp4"),
            mock_output,
            use_gpu=False,
            cpu_preset="fast",
            cpu_crf=22,
            cpu_threads="4"
        )

        assert result is True
        assert mock_run_ffmpeg.called

        # Check command includes CPU settings
        call_args = mock_run_ffmpeg.call_args[0][0]
        assert "-c:v" in call_args
        assert "libx264" in call_args
        assert "-preset" in call_args
        assert "fast" in call_args
        assert "-crf" in call_args
        assert "22" in call_args

    def test_render_final_gpu_success(self, tmp_path, mocker):
        """Test successful GPU rendering"""
        mock_console = Mock()
        creator = LoopCreator(tmp_path, console_log=mock_console)

        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 60.0, "fps": 30, "width": 1920, "height": 1080}
        )

        mock_output = tmp_path / "output.mp4"
        mock_output.touch()

        mock_run_ffmpeg = mocker.patch(
            'backend.loop_creator.run_ffmpeg_with_progress',
            return_value=True
        )

        result = creator.render_final(
            Path("/fake/input.mp4"),
            mock_output,
            use_gpu=True
        )

        assert result is True

        # Check command includes GPU settings
        call_args = mock_run_ffmpeg.call_args[0][0]
        assert "h264_nvenc" in call_args

        # Should log GPU usage
        any_gpu_log = any(
            "GPU" in str(call[0][0]) for call in mock_console.log_info.call_args_list
        )
        assert any_gpu_log

    def test_render_final_with_auto_threads(self, tmp_path, mocker):
        """Test rendering with auto threads"""
        creator = LoopCreator(tmp_path)

        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 60.0, "fps": 30, "width": 1920, "height": 1080}
        )

        mock_output = tmp_path / "output.mp4"
        mock_output.touch()

        mock_run_ffmpeg = mocker.patch(
            'backend.loop_creator.run_ffmpeg_with_progress',
            return_value=True
        )

        creator.render_final(
            Path("/fake/input.mp4"),
            mock_output,
            use_gpu=False,
            cpu_threads="auto"
        )

        # Should not include -threads in command
        call_args = mock_run_ffmpeg.call_args[0][0]
        assert "-threads" not in call_args

    def test_render_final_with_progress_callback(self, tmp_path, mocker):
        """Test rendering with progress callback"""
        creator = LoopCreator(tmp_path)

        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 60.0, "fps": 30, "width": 1920, "height": 1080}
        )

        mock_output = tmp_path / "output.mp4"
        mock_output.touch()

        mock_progress = Mock()

        def mock_ffmpeg_progress(cmd, total_duration, progress_callback, cancel_event, log_callback):
            if progress_callback:
                progress_callback(0.5, "Processing", 10)
            return True

        mocker.patch(
            'backend.loop_creator.run_ffmpeg_with_progress',
            side_effect=mock_ffmpeg_progress
        )

        creator.render_final(
            Path("/fake/input.mp4"),
            mock_output,
            progress_callback=mock_progress
        )

        assert mock_progress.called

    def test_render_final_fails(self, tmp_path, mocker):
        """Test rendering failure"""
        creator = LoopCreator(tmp_path)

        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 60.0, "fps": 30, "width": 1920, "height": 1080}
        )

        mocker.patch(
            'backend.loop_creator.run_ffmpeg_with_progress',
            return_value=False
        )

        result = creator.render_final(
            Path("/fake/input.mp4"),
            tmp_path / "output.mp4"
        )

        assert result is False

    def test_render_final_exception(self, tmp_path, mocker):
        """Test rendering with exception"""
        mock_console = Mock()
        creator = LoopCreator(tmp_path, console_log=mock_console)

        mocker.patch.object(
            creator,
            'get_video_info',
            side_effect=Exception("Info failed")
        )

        result = creator.render_final(
            Path("/fake/input.mp4"),
            tmp_path / "output.mp4"
        )

        assert result is False
        mock_console.log_error.assert_called()


class TestCleanupTempFiles:
    """Test temporary file cleanup"""

    def test_cleanup_removes_temp_files(self, tmp_path):
        """Test that temp files are removed"""
        creator = LoopCreator(tmp_path)

        # Create fake temp files
        (tmp_path / "temp_crossfade_video.mp4").touch()
        (tmp_path / "temp_looped_video.mp4").touch()
        (tmp_path / "temp_scaled_video.mp4").touch()
        (tmp_path / "temp_audio_video.mp4").touch()
        (tmp_path / "concat_list.txt").touch()

        # Keep a non-temp file
        (tmp_path / "output.mp4").touch()

        creator._cleanup_temp_files()

        # Temp files should be gone
        assert not (tmp_path / "temp_crossfade_video.mp4").exists()
        assert not (tmp_path / "temp_looped_video.mp4").exists()
        assert not (tmp_path / "temp_scaled_video.mp4").exists()
        assert not (tmp_path / "temp_audio_video.mp4").exists()
        assert not (tmp_path / "concat_list.txt").exists()

        # Non-temp file should remain
        assert (tmp_path / "output.mp4").exists()

    def test_cleanup_handles_missing_files(self, tmp_path):
        """Test cleanup doesn't fail if files don't exist"""
        creator = LoopCreator(tmp_path)

        # Should not raise exception
        creator._cleanup_temp_files()

    def test_cleanup_handles_permission_errors(self, tmp_path, mocker):
        """Test cleanup handles file permission errors gracefully"""
        creator = LoopCreator(tmp_path)

        # Create temp file
        temp_file = tmp_path / "temp_crossfade_video.mp4"
        temp_file.touch()

        # Mock unlink to raise permission error
        mocker.patch.object(
            Path,
            'unlink',
            side_effect=PermissionError("Permission denied")
        )

        # Should not raise exception
        creator._cleanup_temp_files()


class TestCreateLoopIntegration:
    """Test full create_loop workflow"""

    def test_create_loop_minimal_success(self, tmp_path, mocker):
        """Test minimal successful loop creation"""
        creator = LoopCreator(tmp_path)

        # Mock all dependencies
        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 5.0, "fps": 30, "width": 1920, "height": 1080}
        )

        mock_crossfade = tmp_path / "temp_crossfade.mp4"
        mock_crossfade.touch()
        mocker.patch.object(creator, 'create_crossfade_clip', return_value=mock_crossfade)

        mock_looped = tmp_path / "temp_looped.mp4"
        mock_looped.touch()
        mocker.patch.object(creator, 'concatenate_loops', return_value=mock_looped)

        mocker.patch.object(creator, 'render_final', return_value=True)
        mocker.patch.object(creator, '_cleanup_temp_files')

        result = creator.create_loop(
            video_path="/fake/video.mp4",
            target_duration=20
        )

        assert result is True

    def test_create_loop_with_all_options(self, tmp_path, mocker):
        """Test loop creation with all options"""
        creator = LoopCreator(tmp_path)

        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 5.0, "fps": 30, "width": 1920, "height": 1080}
        )

        mock_crossfade = tmp_path / "temp_crossfade.mp4"
        mock_crossfade.touch()
        mocker.patch.object(creator, 'create_crossfade_clip', return_value=mock_crossfade)

        mock_looped = tmp_path / "temp_looped.mp4"
        mock_looped.touch()
        mocker.patch.object(creator, 'concatenate_loops', return_value=mock_looped)

        mock_scaled = tmp_path / "temp_scaled.mp4"
        mock_scaled.touch()
        mocker.patch.object(creator, 'scale_video', return_value=mock_scaled)

        mock_audio = tmp_path / "temp_audio.mp4"
        mock_audio.touch()
        mocker.patch.object(creator, 'add_audio', return_value=mock_audio)

        mocker.patch.object(creator, 'render_final', return_value=True)
        mocker.patch.object(creator, '_cleanup_temp_files')

        mock_progress = Mock()

        result = creator.create_loop(
            video_path="/fake/video.mp4",
            target_duration=20,
            crossfade_duration=1.5,
            resolution="1280x720",
            audio_path="/fake/audio.mp3",
            use_gpu=True,
            cpu_preset="fast",
            cpu_crf=22,
            cpu_threads="4",
            progress_callback=mock_progress
        )

        assert result is True
        assert mock_progress.called

        # All methods should be called
        assert creator.create_crossfade_clip.called
        assert creator.concatenate_loops.called
        assert creator.scale_video.called
        assert creator.add_audio.called
        assert creator.render_final.called

    def test_create_loop_with_cancellation(self, tmp_path, mocker):
        """Test loop creation with user cancellation"""
        creator = LoopCreator(tmp_path)

        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 5.0, "fps": 30, "width": 1920, "height": 1080}
        )

        # Create cancel event and set it
        cancel_event = threading.Event()
        cancel_event.set()

        result = creator.create_loop(
            video_path="/fake/video.mp4",
            target_duration=20,
            cancel_event=cancel_event
        )

        assert result is False

    def test_create_loop_render_fails(self, tmp_path, mocker):
        """Test loop creation when final render fails"""
        creator = LoopCreator(tmp_path)

        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 5.0, "fps": 30, "width": 1920, "height": 1080}
        )

        mock_crossfade = tmp_path / "temp_crossfade.mp4"
        mock_crossfade.touch()
        mocker.patch.object(creator, 'create_crossfade_clip', return_value=mock_crossfade)

        mock_looped = tmp_path / "temp_looped.mp4"
        mock_looped.touch()
        mocker.patch.object(creator, 'concatenate_loops', return_value=mock_looped)

        # Render fails
        mocker.patch.object(creator, 'render_final', return_value=False)
        mocker.patch.object(creator, '_cleanup_temp_files')

        result = creator.create_loop(
            video_path="/fake/video.mp4",
            target_duration=20
        )

        assert result is False
        # Cleanup should still be called
        assert creator._cleanup_temp_files.called

    def test_create_loop_exception_cleanup(self, tmp_path, mocker):
        """Test that cleanup is called even on exception"""
        creator = LoopCreator(tmp_path)

        # get_video_info raises exception
        mocker.patch.object(
            creator,
            'get_video_info',
            side_effect=Exception("Video error")
        )

        mocker.patch.object(creator, '_cleanup_temp_files')

        result = creator.create_loop(
            video_path="/fake/video.mp4",
            target_duration=20
        )

        assert result is False
        # Cleanup should be called
        assert creator._cleanup_temp_files.called

    def test_create_loop_calculates_correct_loops(self, tmp_path, mocker):
        """Test that correct number of loops is calculated"""
        mock_console = Mock()
        creator = LoopCreator(tmp_path, console_log=mock_console)

        # 7 second video, target 20 seconds = need 3 loops (7*3=21 > 20)
        mocker.patch.object(
            creator,
            'get_video_info',
            return_value={"duration": 7.0, "fps": 30, "width": 1920, "height": 1080}
        )

        mock_crossfade = tmp_path / "temp_crossfade.mp4"
        mock_crossfade.touch()
        mocker.patch.object(creator, 'create_crossfade_clip', return_value=mock_crossfade)

        mock_concat = mocker.patch.object(
            creator,
            'concatenate_loops',
            return_value=tmp_path / "temp_looped.mp4"
        )

        mocker.patch.object(creator, 'render_final', return_value=True)
        mocker.patch.object(creator, '_cleanup_temp_files')

        creator.create_loop(
            video_path="/fake/video.mp4",
            target_duration=20
        )

        # Should call concatenate with 3 loops
        assert mock_concat.called
        call_loops = mock_concat.call_args[0][1]
        assert call_loops == 3
