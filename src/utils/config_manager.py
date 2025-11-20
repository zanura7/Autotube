"""
Configuration Manager
Save and load user preferences
"""

import json
from pathlib import Path
import os


class ConfigManager:
    """Manage application configuration"""

    def __init__(self, config_file=None):
        """
        Initialize config manager

        Args:
            config_file: Path to config file (default: ~/.autotube/config.json)
        """
        if config_file:
            self.config_file = Path(config_file)
        else:
            # Default location in user home directory
            config_dir = Path.home() / ".autotube"
            config_dir.mkdir(parents=True, exist_ok=True)
            self.config_file = config_dir / "config.json"

        self.config = self.load_config()

    def get_default_config(self):
        """Get default configuration"""
        return {
            # Mode A (Loop Creator) settings
            "mode_a": {
                "output_folder": os.path.abspath("./output/loops"),
                "default_duration": 60,  # minutes
                "default_resolution": "1920x1080",
                "default_crossfade": 1.0,  # seconds
                "use_gpu": False,
                "cpu_preset": "medium",
                "cpu_crf": 23,
                "cpu_threads": "auto",
            },
            # Mode B (Downloader) settings
            "mode_b": {
                "output_folder": os.path.abspath("./output/downloads"),
                "default_format": "mp3_320",
                "normalize_audio": True,
                "create_playlist": True,
                "max_concurrent": 3,  # concurrent downloads
            },
            # Mode C (Video Generator) settings
            "mode_c": {
                "output_folder": os.path.abspath("./output/final"),
                "default_resolution": "1920x1080",
                "generate_chapters": True,
                "apply_zoom": True,
            },
            # General settings
            "general": {
                "log_to_file": True,
                "log_level": "INFO",
                "show_notifications": True,
                "max_log_file_size_mb": 10,
                "max_log_files": 5,
                "check_for_updates": True,  # Auto-check for updates on startup
                "skipped_version": None,  # Version user chose to skip
            },
        }

    def load_config(self):
        """
        Load configuration from file

        Returns:
            dict: Configuration dictionary
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)

                # Merge with defaults (in case new settings were added)
                default_config = self.get_default_config()
                merged_config = self._merge_configs(default_config, config)

                return merged_config
            else:
                # Return default config
                return self.get_default_config()

        except Exception as e:
            print(f"Warning: Could not load config: {e}")
            return self.get_default_config()

    def save_config(self):
        """
        Save configuration to file

        Returns:
            bool: True if successful
        """
        try:
            # Create directory if it doesn't exist
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def _merge_configs(self, default, user):
        """
        Merge user config with default config

        Args:
            default: Default configuration
            user: User configuration

        Returns:
            dict: Merged configuration
        """
        merged = default.copy()

        for key, value in user.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                merged[key] = self._merge_configs(merged[key], value)
            else:
                # Override with user value
                merged[key] = value

        return merged

    # Convenience methods for getting/setting values

    def get(self, section, key, default=None):
        """
        Get a configuration value

        Args:
            section: Section name (e.g., "mode_a", "mode_b")
            key: Setting key
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        try:
            return self.config.get(section, {}).get(key, default)
        except:
            return default

    def set(self, section, key, value):
        """
        Set a configuration value

        Args:
            section: Section name
            key: Setting key
            value: Setting value
        """
        if section not in self.config:
            self.config[section] = {}

        self.config[section][key] = value

    def get_mode_a_settings(self):
        """Get Mode A settings"""
        return self.config.get("mode_a", {})

    def get_mode_b_settings(self):
        """Get Mode B settings"""
        return self.config.get("mode_b", {})

    def get_mode_c_settings(self):
        """Get Mode C settings"""
        return self.config.get("mode_c", {})

    def get_general_settings(self):
        """Get general settings"""
        return self.config.get("general", {})

    def update_mode_a_settings(self, settings):
        """Update Mode A settings"""
        if "mode_a" not in self.config:
            self.config["mode_a"] = {}
        self.config["mode_a"].update(settings)
        self.save_config()

    def update_mode_b_settings(self, settings):
        """Update Mode B settings"""
        if "mode_b" not in self.config:
            self.config["mode_b"] = {}
        self.config["mode_b"].update(settings)
        self.save_config()

    def update_mode_c_settings(self, settings):
        """Update Mode C settings"""
        if "mode_c" not in self.config:
            self.config["mode_c"] = {}
        self.config["mode_c"].update(settings)
        self.save_config()

    def update_general_settings(self, settings):
        """Update general settings"""
        if "general" not in self.config:
            self.config["general"] = {}
        self.config["general"].update(settings)
        self.save_config()

    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        self.config = self.get_default_config()
        self.save_config()

    def get_config_file_path(self):
        """Get the path to the config file"""
        return str(self.config_file)
