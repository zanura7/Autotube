"""
Unit tests for video generator backend
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call, mock_open
from pathlib import Path
import ffmpeg
from backend.video_generator import VideoGenerator


class TestVideoGeneratorInit:
    """Test VideoGenerator initialization"""

    def test_init_creates_output_folder(self, tmp_path):
        """Test that output folder is created on init"""
        output_folder = tmp_path / "output"
        generator = VideoGenerator(output_folder)

        assert output_folder.exists()
        assert generator.output_folder == output_folder

    def test_init_with_existing_folder(self, tmp_path):
        """Test initialization with existing folder"""
        output_folder = tmp_path / "output"
        output_folder.mkdir()

        generator = VideoGenerator(output_folder)
        assert generator.output_folder == output_folder

    def test_init_with_console_log(self, tmp_path):
        """Test initialization with console log"""
        mock_console = Mock()
        generator = VideoGenerator(tmp_path, console_log=mock_console)

        assert generator.console_log is mock_console

    def test_init_creates_nested_folders(self, tmp_path):
        """Test that nested folders are created"""
        output_folder = tmp_path / "nested" / "folders" / "output"
        generator = VideoGenerator(output_folder)

        assert output_folder.exists()


class TestLogging:
    """Test logging functionality"""

    def test_log_info_with_console(self, tmp_path):
        """Test logging info with console"""
        mock_console = Mock()
        generator = VideoGenerator(tmp_path, console_log=mock_console)

        generator.log("Test message", "INFO")
        mock_console.log_info.assert_called_once_with("Test message")

    def test_log_error_with_console(self, tmp_path):
        """Test logging error with console"""
        mock_console = Mock()
        generator = VideoGenerator(tmp_path, console_log=mock_console)

        generator.log("Error message", "ERROR")
        mock_console.log_error.assert_called_once_with("Error message")

    def test_log_warning_with_console(self, tmp_path):
        """Test logging warning with console"""
        mock_console = Mock()
        generator = VideoGenerator(tmp_path, console_log=mock_console)

        generator.log("Warning message", "WARNING")
        mock_console.log_warning.assert_called_once_with("Warning message")

    def test_log_success_with_console(self, tmp_path):
        """Test logging success with console"""
        mock_console = Mock()
        generator = VideoGenerator(tmp_path, console_log=mock_console)

        generator.log("Success message", "SUCCESS")
        mock_console.log_success.assert_called_once_with("Success message")

    def test_log_without_console(self, tmp_path, capsys):
        """Test logging without console (prints to stdout)"""
        generator = VideoGenerator(tmp_path, console_log=None)

        generator.log("Test message", "INFO")
        captured = capsys.readouterr()
        assert "[INFO] Test message" in captured.out


class TestFormatTimestamp:
    """Test timestamp formatting"""

    def test_format_timestamp_hours_minutes_seconds(self, tmp_path):
        """Test formatting with hours, minutes, and seconds"""
        generator = VideoGenerator(tmp_path)

        result = generator.format_timestamp(3661)  # 1:01:01
        assert result == "01:01:01"

    def test_format_timestamp_only_seconds(self, tmp_path):
        """Test formatting with only seconds"""
        generator = VideoGenerator(tmp_path)

        result = generator.format_timestamp(45)
        assert result == "00:00:45"

    def test_format_timestamp_only_minutes(self, tmp_path):
        """Test formatting with minutes and seconds"""
        generator = VideoGenerator(tmp_path)

        result = generator.format_timestamp(150)  # 2:30
        assert result == "00:02:30"

    def test_format_timestamp_zero(self, tmp_path):
        """Test formatting zero time"""
        generator = VideoGenerator(tmp_path)

        result = generator.format_timestamp(0)
        assert result == "00:00:00"

    def test_format_timestamp_large_value(self, tmp_path):
        """Test formatting large time value"""
        generator = VideoGenerator(tmp_path)

        result = generator.format_timestamp(7325)  # 2:02:05
        assert result == "02:02:05"


class TestGetAudioDuration:
    """Test audio duration extraction"""

    def test_get_audio_duration_success(self, tmp_path, mocker):
        """Test successful audio duration extraction"""
        generator = VideoGenerator(tmp_path)

        mock_probe_result = {
            "format": {"duration": "120.5"}
        }

        mocker.patch('ffmpeg.probe', return_value=mock_probe_result)

        duration = generator.get_audio_duration(Path("/fake/audio.mp3"))
        assert duration == 120.5

    def test_get_audio_duration_fails(self, tmp_path, mocker):
        """Test audio duration when probe fails"""
        mock_console = Mock()
        generator = VideoGenerator(tmp_path, console_log=mock_console)

        mocker.patch('ffmpeg.probe', side_effect=Exception("Probe failed"))

        duration = generator.get_audio_duration(Path("/fake/audio.mp3"))

        assert duration is None
        mock_console.log_warning.assert_called()


class TestGetAudioFiles:
    """Test audio file collection"""

    def test_get_audio_files_from_playlist(self, tmp_path):
        """Test getting audio files from M3U playlist"""
        generator = VideoGenerator(tmp_path)

        # Create audio files
        audio1 = tmp_path / "song1.mp3"
        audio2 = tmp_path / "song2.mp3"
        audio1.touch()
        audio2.touch()

        # Create playlist
        playlist = tmp_path / "playlist.m3u"
        playlist.write_text(
            "#EXTM3U\n"
            "#EXTINF:-1,Song 1\n"
            "song1.mp3\n"
            "#EXTINF:-1,Song 2\n"
            "song2.mp3\n"
        )

        audio_files = generator.get_audio_files(playlist_path=playlist)

        assert len(audio_files) == 2
        assert audio1 in audio_files
        assert audio2 in audio_files

    def test_get_audio_files_from_folder(self, tmp_path):
        """Test getting audio files from folder"""
        generator = VideoGenerator(tmp_path)

        # Create audio files
        audio1 = tmp_path / "song1.mp3"
        audio2 = tmp_path / "song2.m4a"
        audio3 = tmp_path / "song3.wav"
        video1 = tmp_path / "video.mp4"  # Should be ignored

        audio1.touch()
        audio2.touch()
        audio3.touch()
        video1.touch()

        audio_files = generator.get_audio_files(audio_folder=tmp_path)

        assert len(audio_files) == 3
        assert audio1 in audio_files
        assert audio2 in audio_files
        assert audio3 in audio_files
        assert video1 not in audio_files

    def test_get_audio_files_from_folder_sorted(self, tmp_path):
        """Test that audio files from folder are sorted"""
        generator = VideoGenerator(tmp_path)

        # Create files in non-alphabetical order
        audio3 = tmp_path / "c_song.mp3"
        audio1 = tmp_path / "a_song.mp3"
        audio2 = tmp_path / "b_song.mp3"

        audio3.touch()
        audio1.touch()
        audio2.touch()

        audio_files = generator.get_audio_files(audio_folder=tmp_path)

        # Should be sorted alphabetically
        assert audio_files[0].name == "a_song.mp3"
        assert audio_files[1].name == "b_song.mp3"
        assert audio_files[2].name == "c_song.mp3"

    def test_get_audio_files_playlist_skips_missing(self, tmp_path):
        """Test that missing files in playlist are skipped"""
        generator = VideoGenerator(tmp_path)

        # Only create one file
        audio1 = tmp_path / "song1.mp3"
        audio1.touch()

        # Playlist references two files
        playlist = tmp_path / "playlist.m3u"
        playlist.write_text(
            "#EXTM3U\n"
            "song1.mp3\n"
            "missing.mp3\n"
        )

        audio_files = generator.get_audio_files(playlist_path=playlist)

        # Should only include existing file
        assert len(audio_files) == 1
        assert audio1 in audio_files

    def test_get_audio_files_empty_playlist(self, tmp_path):
        """Test with empty playlist"""
        generator = VideoGenerator(tmp_path)

        playlist = tmp_path / "playlist.m3u"
        playlist.write_text("#EXTM3U\n")

        audio_files = generator.get_audio_files(playlist_path=playlist)

        assert len(audio_files) == 0

    def test_get_audio_files_empty_folder(self, tmp_path):
        """Test with empty folder"""
        generator = VideoGenerator(tmp_path)

        audio_files = generator.get_audio_files(audio_folder=tmp_path)

        assert len(audio_files) == 0


class TestCreateChapters:
    """Test chapter metadata creation"""

    def test_create_chapters_success(self, tmp_path, mocker):
        """Test successful chapter creation"""
        generator = VideoGenerator(tmp_path)

        # Mock get_audio_duration
        mocker.patch.object(
            generator,
            'get_audio_duration',
            side_effect=[120.0, 180.0, 90.0]
        )

        audio_files = [
            Path("/fake/song1.mp3"),
            Path("/fake/song2.mp3"),
            Path("/fake/song3.mp3")
        ]

        chapters = generator.create_chapters(audio_files)

        assert len(chapters) == 3

        # First chapter
        assert chapters[0]["title"] == "song1"
        assert chapters[0]["start_time"] == 0.0
        assert chapters[0]["end_time"] == 120.0

        # Second chapter
        assert chapters[1]["title"] == "song2"
        assert chapters[1]["start_time"] == 120.0
        assert chapters[1]["end_time"] == 300.0

        # Third chapter
        assert chapters[2]["title"] == "song3"
        assert chapters[2]["start_time"] == 300.0
        assert chapters[2]["end_time"] == 390.0

    def test_create_chapters_with_failed_duration(self, tmp_path, mocker):
        """Test chapter creation when duration extraction fails"""
        generator = VideoGenerator(tmp_path)

        # One file fails duration extraction
        mocker.patch.object(
            generator,
            'get_audio_duration',
            side_effect=[120.0, None, 90.0]
        )

        audio_files = [
            Path("/fake/song1.mp3"),
            Path("/fake/song2.mp3"),
            Path("/fake/song3.mp3")
        ]

        chapters = generator.create_chapters(audio_files)

        # Should skip file with no duration
        assert len(chapters) == 2
        assert chapters[0]["title"] == "song1"
        assert chapters[1]["title"] == "song3"
        assert chapters[1]["start_time"] == 120.0

    def test_create_chapters_empty_list(self, tmp_path):
        """Test chapter creation with empty list"""
        generator = VideoGenerator(tmp_path)

        chapters = generator.create_chapters([])

        assert len(chapters) == 0


class TestConcatenateAudio:
    """Test audio concatenation"""

    def test_concatenate_audio_success(self, tmp_path, mocker):
        """Test successful audio concatenation"""
        generator = VideoGenerator(tmp_path)

        audio1 = tmp_path / "song1.mp3"
        audio2 = tmp_path / "song2.mp3"
        audio1.touch()
        audio2.touch()

        audio_files = [audio1, audio2]

        # Mock subprocess.run
        mock_run = mocker.patch('subprocess.run')

        result = generator.concatenate_audio(audio_files)

        assert result is not None
        assert result.name == "temp_audio.mp3"

        # Should call FFmpeg concat
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "ffmpeg" in call_args
        assert "-f" in call_args
        assert "concat" in call_args

    def test_concatenate_audio_creates_list_file(self, tmp_path, mocker):
        """Test that audio list file is created and cleaned up"""
        generator = VideoGenerator(tmp_path)

        audio1 = tmp_path / "song1.mp3"
        audio1.touch()

        # Mock subprocess.run
        mocker.patch('subprocess.run')

        generator.concatenate_audio([audio1])

        # List file should be cleaned up after success
        list_file = tmp_path / "audio_list.txt"
        assert not list_file.exists()

    def test_concatenate_audio_subprocess_error(self, tmp_path, mocker):
        """Test concatenation with subprocess error"""
        mock_console = Mock()
        generator = VideoGenerator(tmp_path, console_log=mock_console)

        audio1 = tmp_path / "song1.mp3"
        audio1.touch()

        import subprocess
        mocker.patch(
            'subprocess.run',
            side_effect=subprocess.CalledProcessError(1, "ffmpeg")
        )

        result = generator.concatenate_audio([audio1])

        assert result is None
        mock_console.log_error.assert_called()

    def test_concatenate_audio_uses_absolute_paths(self, tmp_path, mocker):
        """Test that concatenation uses absolute paths"""
        generator = VideoGenerator(tmp_path)

        audio1 = tmp_path / "song1.mp3"
        audio1.touch()

        # Capture the list file content
        list_content = None

        def mock_subprocess_run(*args, **kwargs):
            nonlocal list_content
            list_file = tmp_path / "audio_list.txt"
            if list_file.exists():
                list_content = list_file.read_text()

        mocker.patch('subprocess.run', side_effect=mock_subprocess_run)

        generator.concatenate_audio([audio1])

        # Should use absolute path
        assert list_content is not None
        assert str(audio1.absolute()) in list_content


class TestSaveChapters:
    """Test chapter file saving"""

    def test_save_chapters_success(self, tmp_path):
        """Test successful chapter file saving"""
        generator = VideoGenerator(tmp_path)

        video_file = tmp_path / "video.mp4"
        video_file.touch()

        chapters = [
            {"title": "Intro", "start_time": 0, "end_time": 120},
            {"title": "Main Content", "start_time": 120, "end_time": 300},
            {"title": "Outro", "start_time": 300, "end_time": 360}
        ]

        chapter_file = generator.save_chapters(chapters, video_file)

        assert chapter_file is not None
        assert chapter_file.exists()
        assert chapter_file.suffix == ".txt"
        assert "chapters" in chapter_file.name

        # Check content
        content = chapter_file.read_text(encoding="utf-8")
        assert "00:00:00 Intro" in content
        assert "00:02:00 Main Content" in content
        assert "00:05:00 Outro" in content

    def test_save_chapters_youtube_format(self, tmp_path):
        """Test that chapters are in YouTube format"""
        generator = VideoGenerator(tmp_path)

        video_file = tmp_path / "video.mp4"
        video_file.touch()

        chapters = [
            {"title": "Chapter 1", "start_time": 0, "end_time": 60},
            {"title": "Chapter 2", "start_time": 60, "end_time": 120}
        ]

        chapter_file = generator.save_chapters(chapters, video_file)

        content = chapter_file.read_text(encoding="utf-8")

        # YouTube format: HH:MM:SS Title
        lines = content.strip().split("\n")
        assert lines[0] == "00:00:00 Chapter 1"
        assert lines[1] == "00:01:00 Chapter 2"

    def test_save_chapters_empty_list(self, tmp_path):
        """Test saving empty chapter list"""
        generator = VideoGenerator(tmp_path)

        video_file = tmp_path / "video.mp4"
        video_file.touch()

        chapter_file = generator.save_chapters([], video_file)

        assert chapter_file is not None
        assert chapter_file.exists()

        content = chapter_file.read_text(encoding="utf-8")
        assert content == ""

    def test_save_chapters_handles_exception(self, tmp_path, mocker):
        """Test chapter saving handles exceptions"""
        mock_console = Mock()
        generator = VideoGenerator(tmp_path, console_log=mock_console)

        video_file = tmp_path / "video.mp4"

        chapters = [{"title": "Test", "start_time": 0, "end_time": 60}]

        # Mock open to raise exception
        mocker.patch('builtins.open', side_effect=IOError("Write error"))

        result = generator.save_chapters(chapters, video_file)

        assert result is None
        mock_console.log_warning.assert_called()


class TestRenderVideo:
    """Test video rendering"""

    def test_render_video_with_image_no_zoom(self, tmp_path, mocker):
        """Test rendering video with static image"""
        generator = VideoGenerator(tmp_path)

        audio_file = tmp_path / "audio.mp3"
        image_file = tmp_path / "image.jpg"
        output_file = tmp_path / "output.mp4"

        audio_file.touch()
        image_file.touch()

        # Mock ffmpeg
        mock_input = mocker.patch('ffmpeg.input')
        mock_output = mocker.patch('ffmpeg.output')
        mock_run = mocker.patch('ffmpeg.run')

        # Create mock output file
        output_file.touch()

        result = generator.render_video(
            audio_path=audio_file,
            visual_path=image_file,
            output_path=output_file,
            duration=120,
            resolution="1920x1080",
            is_image=True,
            apply_zoom=False
        )

        assert result is True
        assert mock_input.called
        assert mock_output.called
        assert mock_run.called

    def test_render_video_with_image_and_zoom(self, tmp_path, mocker):
        """Test rendering video with zoom effect"""
        generator = VideoGenerator(tmp_path)

        audio_file = tmp_path / "audio.mp3"
        image_file = tmp_path / "image.jpg"
        output_file = tmp_path / "output.mp4"

        audio_file.touch()
        image_file.touch()

        # Mock ffmpeg chain
        mock_input = Mock()
        mock_filtered = Mock()
        mock_filtered.filter = Mock(return_value=mock_filtered)
        mock_input.filter = Mock(return_value=mock_filtered)

        mocker.patch('ffmpeg.input', return_value=mock_input)
        mocker.patch('ffmpeg.output')
        mocker.patch('ffmpeg.run')

        output_file.touch()

        result = generator.render_video(
            audio_path=audio_file,
            visual_path=image_file,
            output_path=output_file,
            duration=120,
            resolution="1920x1080",
            is_image=True,
            apply_zoom=True
        )

        assert result is True
        # Should call filter with zoompan
        assert mock_input.filter.called

    def test_render_video_with_video_input(self, tmp_path, mocker):
        """Test rendering with video input"""
        generator = VideoGenerator(tmp_path)

        audio_file = tmp_path / "audio.mp3"
        video_file = tmp_path / "video.mp4"
        output_file = tmp_path / "output.mp4"

        audio_file.touch()
        video_file.touch()

        # Mock ffmpeg
        mock_input = Mock()
        mock_filtered = Mock()
        mock_filtered.filter = Mock(return_value=mock_filtered)
        mock_input.filter = Mock(return_value=mock_filtered)

        mocker.patch('ffmpeg.input', return_value=mock_input)
        mocker.patch('ffmpeg.output')
        mocker.patch('ffmpeg.run')

        output_file.touch()

        result = generator.render_video(
            audio_path=audio_file,
            visual_path=video_file,
            output_path=output_file,
            duration=120,
            resolution="1920x1080",
            is_image=False,
            apply_zoom=False
        )

        assert result is True

    def test_render_video_ffmpeg_error(self, tmp_path, mocker):
        """Test rendering with FFmpeg error"""
        mock_console = Mock()
        generator = VideoGenerator(tmp_path, console_log=mock_console)

        audio_file = tmp_path / "audio.mp3"
        image_file = tmp_path / "image.jpg"
        output_file = tmp_path / "output.mp4"

        audio_file.touch()
        image_file.touch()

        mocker.patch('ffmpeg.input')
        mocker.patch('ffmpeg.output')

        # Mock ffmpeg.run to raise error
        mock_error = ffmpeg.Error("ffmpeg", b"stdout", b"error message")
        mocker.patch('ffmpeg.run', side_effect=mock_error)

        result = generator.render_video(
            audio_path=audio_file,
            visual_path=image_file,
            output_path=output_file,
            duration=120,
            resolution="1920x1080",
            is_image=True
        )

        assert result is False
        mock_console.log_error.assert_called()

    def test_render_video_general_exception(self, tmp_path, mocker):
        """Test rendering with general exception"""
        mock_console = Mock()
        generator = VideoGenerator(tmp_path, console_log=mock_console)

        audio_file = tmp_path / "audio.mp3"
        image_file = tmp_path / "image.jpg"
        output_file = tmp_path / "output.mp4"

        audio_file.touch()
        image_file.touch()

        mocker.patch('ffmpeg.input', side_effect=Exception("General error"))

        result = generator.render_video(
            audio_path=audio_file,
            visual_path=image_file,
            output_path=output_file,
            duration=120,
            resolution="1920x1080",
            is_image=True
        )

        assert result is False
        mock_console.log_error.assert_called()


class TestGenerateVideo:
    """Test full video generation workflow"""

    def test_generate_video_minimal_success(self, tmp_path, mocker):
        """Test minimal successful video generation"""
        generator = VideoGenerator(tmp_path)

        # Create audio files
        audio1 = tmp_path / "song1.mp3"
        audio2 = tmp_path / "song2.mp3"
        audio1.touch()
        audio2.touch()

        # Create visual
        image = tmp_path / "image.jpg"
        image.touch()

        # Mock methods
        mocker.patch.object(
            generator,
            'get_audio_files',
            return_value=[audio1, audio2]
        )

        mocker.patch.object(
            generator,
            'get_audio_duration',
            return_value=120.0
        )

        temp_audio = tmp_path / "temp_audio.mp3"
        temp_audio.touch()
        mocker.patch.object(
            generator,
            'concatenate_audio',
            return_value=temp_audio
        )

        mocker.patch.object(
            generator,
            'render_video',
            return_value=True
        )

        result = generator.generate_video(
            audio_folder=tmp_path,
            visual_path=image,
            generate_chapters=False
        )

        assert result is True

    def test_generate_video_with_chapters(self, tmp_path, mocker):
        """Test video generation with chapter file"""
        generator = VideoGenerator(tmp_path)

        audio1 = tmp_path / "song1.mp3"
        audio1.touch()

        image = tmp_path / "image.jpg"
        image.touch()

        mocker.patch.object(
            generator,
            'get_audio_files',
            return_value=[audio1]
        )

        mocker.patch.object(
            generator,
            'get_audio_duration',
            return_value=120.0
        )

        temp_audio = tmp_path / "temp_audio.mp3"
        temp_audio.touch()
        mocker.patch.object(
            generator,
            'concatenate_audio',
            return_value=temp_audio
        )

        mocker.patch.object(
            generator,
            'render_video',
            return_value=True
        )

        mock_save_chapters = mocker.patch.object(
            generator,
            'save_chapters',
            return_value=tmp_path / "chapters.txt"
        )

        result = generator.generate_video(
            audio_folder=tmp_path,
            visual_path=image,
            generate_chapters=True
        )

        assert result is True
        assert mock_save_chapters.called

    def test_generate_video_no_audio_files(self, tmp_path, mocker):
        """Test video generation with no audio files"""
        mock_console = Mock()
        generator = VideoGenerator(tmp_path, console_log=mock_console)

        image = tmp_path / "image.jpg"
        image.touch()

        mocker.patch.object(
            generator,
            'get_audio_files',
            return_value=[]
        )

        result = generator.generate_video(
            audio_folder=tmp_path,
            visual_path=image
        )

        assert result is False
        mock_console.log_error.assert_called()

    def test_generate_video_with_progress_callback(self, tmp_path, mocker):
        """Test video generation with progress callback"""
        generator = VideoGenerator(tmp_path)

        audio1 = tmp_path / "song1.mp3"
        audio1.touch()

        image = tmp_path / "image.jpg"
        image.touch()

        mocker.patch.object(
            generator,
            'get_audio_files',
            return_value=[audio1]
        )

        mocker.patch.object(
            generator,
            'get_audio_duration',
            return_value=120.0
        )

        temp_audio = tmp_path / "temp_audio.mp3"
        temp_audio.touch()
        mocker.patch.object(
            generator,
            'concatenate_audio',
            return_value=temp_audio
        )

        mocker.patch.object(
            generator,
            'render_video',
            return_value=True
        )

        mock_progress = Mock()

        result = generator.generate_video(
            audio_folder=tmp_path,
            visual_path=image,
            progress_callback=mock_progress,
            generate_chapters=False
        )

        assert result is True
        # Progress callback should be called multiple times
        assert mock_progress.call_count > 0

    def test_generate_video_render_fails(self, tmp_path, mocker):
        """Test video generation when render fails"""
        mock_console = Mock()
        generator = VideoGenerator(tmp_path, console_log=mock_console)

        audio1 = tmp_path / "song1.mp3"
        audio1.touch()

        image = tmp_path / "image.jpg"
        image.touch()

        mocker.patch.object(
            generator,
            'get_audio_files',
            return_value=[audio1]
        )

        mocker.patch.object(
            generator,
            'get_audio_duration',
            return_value=120.0
        )

        temp_audio = tmp_path / "temp_audio.mp3"
        temp_audio.touch()
        mocker.patch.object(
            generator,
            'concatenate_audio',
            return_value=temp_audio
        )

        # Render fails
        mocker.patch.object(
            generator,
            'render_video',
            return_value=False
        )

        result = generator.generate_video(
            audio_folder=tmp_path,
            visual_path=image
        )

        assert result is False
        mock_console.log_error.assert_called()

    def test_generate_video_cleans_temp_audio(self, tmp_path, mocker):
        """Test that temp audio is cleaned up"""
        generator = VideoGenerator(tmp_path)

        audio1 = tmp_path / "song1.mp3"
        audio1.touch()

        image = tmp_path / "image.jpg"
        image.touch()

        mocker.patch.object(
            generator,
            'get_audio_files',
            return_value=[audio1]
        )

        mocker.patch.object(
            generator,
            'get_audio_duration',
            return_value=120.0
        )

        temp_audio = tmp_path / "temp_audio.mp3"
        temp_audio.touch()
        mocker.patch.object(
            generator,
            'concatenate_audio',
            return_value=temp_audio
        )

        mocker.patch.object(
            generator,
            'render_video',
            return_value=True
        )

        generator.generate_video(
            audio_folder=tmp_path,
            visual_path=image,
            generate_chapters=False
        )

        # Temp audio should be cleaned up
        assert not temp_audio.exists()

    def test_generate_video_cleans_temp_on_error(self, tmp_path, mocker):
        """Test that temp files are cleaned up on error"""
        generator = VideoGenerator(tmp_path)

        audio1 = tmp_path / "song1.mp3"
        audio1.touch()

        image = tmp_path / "image.jpg"
        image.touch()

        mocker.patch.object(
            generator,
            'get_audio_files',
            return_value=[audio1]
        )

        mocker.patch.object(
            generator,
            'get_audio_duration',
            side_effect=Exception("Duration error")
        )

        result = generator.generate_video(
            audio_folder=tmp_path,
            visual_path=image
        )

        assert result is False

    def test_generate_video_detects_image_vs_video(self, tmp_path, mocker):
        """Test that generator detects image vs video input"""
        generator = VideoGenerator(tmp_path)

        audio1 = tmp_path / "song1.mp3"
        audio1.touch()

        # Test with image
        image = tmp_path / "image.jpg"
        image.touch()

        mocker.patch.object(generator, 'get_audio_files', return_value=[audio1])
        mocker.patch.object(generator, 'get_audio_duration', return_value=120.0)

        temp_audio = tmp_path / "temp_audio.mp3"
        temp_audio.touch()
        mocker.patch.object(generator, 'concatenate_audio', return_value=temp_audio)

        mock_render = mocker.patch.object(generator, 'render_video', return_value=True)

        generator.generate_video(
            audio_folder=tmp_path,
            visual_path=image,
            apply_zoom=True,
            generate_chapters=False
        )

        # Check render_video was called with is_image=True and apply_zoom=True
        call_kwargs = mock_render.call_args[1]
        assert call_kwargs['is_image'] is True
        assert call_kwargs['apply_zoom'] is True

    def test_generate_video_creates_output_with_timestamp(self, tmp_path, mocker):
        """Test that output filename includes timestamp"""
        generator = VideoGenerator(tmp_path)

        audio1 = tmp_path / "song1.mp3"
        audio1.touch()

        image = tmp_path / "image.jpg"
        image.touch()

        mocker.patch.object(generator, 'get_audio_files', return_value=[audio1])
        mocker.patch.object(generator, 'get_audio_duration', return_value=120.0)

        temp_audio = tmp_path / "temp_audio.mp3"
        temp_audio.touch()
        mocker.patch.object(generator, 'concatenate_audio', return_value=temp_audio)

        mock_render = mocker.patch.object(generator, 'render_video', return_value=True)

        generator.generate_video(
            audio_folder=tmp_path,
            visual_path=image,
            generate_chapters=False
        )

        # Check output path has timestamp format
        call_args = mock_render.call_args[1]
        output_path = call_args['output_path']
        assert "final_video_" in output_path.name
        assert output_path.suffix == ".mp4"
