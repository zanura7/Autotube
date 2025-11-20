"""
Unit tests for configuration manager
"""

import pytest
import json
from pathlib import Path
from utils.config_manager import ConfigManager


class TestConfigManager:
    """Test configuration manager"""

    def test_default_config_creation(self, tmp_path):
        """Test that default config is created properly"""
        config_file = tmp_path / "config.json"
        config = ConfigManager(config_file=config_file)

        # Should have all required sections
        assert "mode_a" in config.config
        assert "mode_b" in config.config
        assert "mode_c" in config.config
        assert "general" in config.config

        # Should have specific settings
        assert "output_folder" in config.config["mode_a"]
        assert "max_concurrent" in config.config["mode_b"]
        assert "log_to_file" in config.config["general"]

    def test_load_existing_config(self, mock_config_file):
        """Test loading existing config from file"""
        config = ConfigManager(config_file=mock_config_file)

        assert config.config["mode_a"]["default_duration"] == 60
        assert config.config["mode_b"]["max_concurrent"] == 3
        assert config.config["general"]["log_to_file"] is True

    def test_save_config(self, tmp_path):
        """Test saving config to file"""
        config_file = tmp_path / "config.json"
        config = ConfigManager(config_file=config_file)

        # Modify a setting
        config.set("mode_a", "default_duration", 120)

        # Save
        assert config.save_config() is True

        # Verify file was written
        assert config_file.exists()

        # Load again and verify
        with open(config_file) as f:
            loaded_config = json.load(f)

        assert loaded_config["mode_a"]["default_duration"] == 120

    def test_get_setting(self, mock_config_file):
        """Test getting individual settings"""
        config = ConfigManager(config_file=mock_config_file)

        # Get existing setting
        assert config.get("mode_a", "default_duration") == 60

        # Get non-existent setting with default
        assert config.get("mode_a", "nonexistent", default=999) == 999

    def test_set_setting(self, tmp_path):
        """Test setting individual settings"""
        config_file = tmp_path / "config.json"
        config = ConfigManager(config_file=config_file)

        # Set a new value
        config.set("mode_a", "test_setting", "test_value")

        assert config.config["mode_a"]["test_setting"] == "test_value"

    def test_update_mode_settings(self, tmp_path):
        """Test updating entire mode settings"""
        config_file = tmp_path / "config.json"
        config = ConfigManager(config_file=config_file)

        new_settings = {
            "default_duration": 90,
            "use_gpu": True,
        }

        config.update_mode_a_settings(new_settings)

        assert config.config["mode_a"]["default_duration"] == 90
        assert config.config["mode_a"]["use_gpu"] is True

        # Should preserve other settings
        assert "output_folder" in config.config["mode_a"]

    def test_config_merge_with_defaults(self, tmp_path):
        """Test that incomplete config is merged with defaults"""
        config_file = tmp_path / "config.json"

        # Create incomplete config
        incomplete_config = {
            "mode_a": {
                "default_duration": 99,  # Only one setting
            }
        }

        with open(config_file, "w") as f:
            json.dump(incomplete_config, f)

        # Load config
        config = ConfigManager(config_file=config_file)

        # Should have the custom setting
        assert config.config["mode_a"]["default_duration"] == 99

        # Should also have default settings
        assert "output_folder" in config.config["mode_a"]
        assert "mode_b" in config.config
        assert "general" in config.config

    def test_reset_to_defaults(self, tmp_path):
        """Test resetting config to defaults"""
        config_file = tmp_path / "config.json"
        config = ConfigManager(config_file=config_file)

        # Modify settings
        config.set("mode_a", "default_duration", 999)
        config.save_config()

        # Reset to defaults
        config.reset_to_defaults()

        # Should have default values
        default_config = config.get_default_config()
        assert config.config["mode_a"]["default_duration"] == default_config["mode_a"]["default_duration"]

    def test_get_mode_settings(self, mock_config_file):
        """Test getting settings for specific modes"""
        config = ConfigManager(config_file=mock_config_file)

        mode_a_settings = config.get_mode_a_settings()
        assert mode_a_settings["default_duration"] == 60

        mode_b_settings = config.get_mode_b_settings()
        assert mode_b_settings["max_concurrent"] == 3

        general_settings = config.get_general_settings()
        assert general_settings["log_to_file"] is True

    def test_config_file_path(self, tmp_path):
        """Test getting config file path"""
        config_file = tmp_path / "config.json"
        config = ConfigManager(config_file=config_file)

        path = config.get_config_file_path()
        assert Path(path) == config_file

    def test_invalid_config_file(self, tmp_path):
        """Test handling of invalid/corrupted config file"""
        config_file = tmp_path / "corrupt.json"

        # Write invalid JSON
        with open(config_file, "w") as f:
            f.write("{ invalid json ]")

        # Should fall back to defaults
        config = ConfigManager(config_file=config_file)

        # Should have default config
        assert "mode_a" in config.config
        assert "mode_b" in config.config

    def test_config_persistence(self, tmp_path):
        """Test that config persists across instances"""
        config_file = tmp_path / "persist.json"

        # Create and modify config
        config1 = ConfigManager(config_file=config_file)
        config1.set("mode_a", "default_duration", 777)
        config1.save_config()

        # Load in new instance
        config2 = ConfigManager(config_file=config_file)

        # Should have persisted value
        assert config2.get("mode_a", "default_duration") == 777
