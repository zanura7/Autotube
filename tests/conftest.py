"""
Pytest configuration and fixtures
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def mock_console_log():
    """Create a mock console log for testing"""
    mock = Mock()
    mock.log = Mock()
    mock.log_info = Mock()
    mock.log_success = Mock()
    mock.log_warning = Mock()
    mock.log_error = Mock()
    return mock


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def sample_video_path(tmp_path):
    """Create a dummy video file for testing"""
    video_file = tmp_path / "sample.mp4"
    video_file.write_text("dummy video content")
    return video_file


@pytest.fixture
def sample_audio_path(tmp_path):
    """Create a dummy audio file for testing"""
    audio_file = tmp_path / "sample.mp3"
    audio_file.write_text("dummy audio content")
    return audio_file


@pytest.fixture
def sample_config_dict():
    """Sample configuration dictionary"""
    return {
        "mode_a": {
            "output_folder": "/tmp/output/loops",
            "default_duration": 60,
            "default_resolution": "1920x1080",
            "use_gpu": False,
        },
        "mode_b": {
            "output_folder": "/tmp/output/downloads",
            "max_concurrent": 3,
        },
        "general": {
            "log_to_file": True,
            "show_notifications": True,
        },
    }


@pytest.fixture
def mock_config_file(tmp_path, sample_config_dict):
    """Create a mock config file"""
    import json

    config_file = tmp_path / "config.json"
    with open(config_file, "w") as f:
        json.dump(sample_config_dict, f)
    return config_file
