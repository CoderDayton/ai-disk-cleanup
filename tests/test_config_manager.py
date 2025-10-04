"""Tests for configuration manager."""

import json
import pytest
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from ai_disk_cleanup.core.config_manager import ConfigManager, get_config_manager, get_config, get_user_preferences
from ai_disk_cleanup.core.config_models import AppConfig, UserPreferences, ConfidenceLevel, CleanupScope


class TestConfigManager:
    """Test ConfigManager class."""

    def test_init_with_defaults(self, tmp_path):
        """Test initializing config manager with default paths."""
        config_file = tmp_path / "config.yaml"
        prefs_file = tmp_path / "prefs.yaml"

        manager = ConfigManager(
            config_file=config_file,
            user_prefs_file=prefs_file,
            auto_load=False
        )

        assert manager.config_file == config_file
        assert manager.user_prefs_file == prefs_file
        assert manager._config is None
        assert manager._user_prefs is None

    def test_load_config_creates_default(self, tmp_path):
        """Test loading config creates default when file doesn't exist."""
        config_file = tmp_path / "config.yaml"

        manager = ConfigManager(config_file=config_file, auto_load=False)
        config = manager.load_config()

        assert isinstance(config, AppConfig)
        assert config.app_name == "ai-disk-cleanup"
        assert config_file.exists()  # Should create default config file

    def test_load_config_from_existing_file(self, tmp_path):
        """Test loading config from existing file."""
        config_file = tmp_path / "config.yaml"
        test_config = {
            "app_name": "test-app",
            "version": "2.0.0",
            "ai_model": {
                "provider": "anthropic",
                "model_name": "claude-3"
            }
        }

        # Write test config
        with open(config_file, 'w') as f:
            yaml.dump(test_config, f)

        manager = ConfigManager(config_file=config_file, auto_load=False)
        config = manager.load_config()

        assert config.app_name == "test-app"
        assert config.version == "2.0.0"
        assert config.ai_model.provider == "anthropic"
        assert config.ai_model.model_name == "claude-3"

    def test_load_config_json_format(self, tmp_path):
        """Test loading config from JSON file."""
        config_file = tmp_path / "config.json"
        test_config = {
            "app_name": "json-app",
            "version": "1.0.0"
        }

        with open(config_file, 'w') as f:
            json.dump(test_config, f)

        manager = ConfigManager(config_file=config_file, auto_load=False)
        config = manager.load_config()

        assert config.app_name == "json-app"

    def test_save_config(self, tmp_path):
        """Test saving configuration to file."""
        config_file = tmp_path / "config.yaml"

        manager = ConfigManager(config_file=config_file, auto_load=False)
        manager._config = AppConfig(app_name="save-test")
        success = manager.save_config()

        assert success is True
        assert config_file.exists()

        # Verify saved content
        with open(config_file, 'r') as f:
            saved_data = yaml.safe_load(f)
            assert saved_data["app_name"] == "save-test"

    def test_load_user_preferences(self, tmp_path):
        """Test loading user preferences."""
        prefs_file = tmp_path / "prefs.yaml"

        manager = ConfigManager(user_prefs_file=prefs_file, auto_load=False)
        prefs = manager.load_user_preferences()

        assert isinstance(prefs, UserPreferences)
        assert prefs_file.exists()  # Should create default prefs file

    def test_load_user_preferences_from_existing(self, tmp_path):
        """Test loading user preferences from existing file."""
        prefs_file = tmp_path / "prefs.yaml"
        test_prefs = {
            "favorite_paths": ["/home/user/docs", "/home/user/downloads"],
            "recent_scans": ["/tmp", "/var/log"],
            "custom_rules": {"temp_files": {"age_days": 1}}
        }

        with open(prefs_file, 'w') as f:
            yaml.dump(test_prefs, f)

        manager = ConfigManager(user_prefs_file=prefs_file, auto_load=False)
        prefs = manager.load_user_preferences()

        assert len(prefs.favorite_paths) == 2
        assert "/home/user/docs" in prefs.favorite_paths
        assert len(prefs.recent_scans) == 2
        assert "/tmp" in prefs.recent_scans
        assert "temp_files" in prefs.custom_rules

    def test_save_user_preferences(self, tmp_path):
        """Test saving user preferences to file."""
        prefs_file = tmp_path / "prefs.yaml"

        manager = ConfigManager(user_prefs_file=prefs_file, auto_load=False)
        manager._user_prefs = UserPreferences(favorite_paths=["/test/path"])
        success = manager.save_user_preferences()

        assert success is True
        assert prefs_file.exists()

        # Verify saved content
        with open(prefs_file, 'r') as f:
            saved_data = yaml.safe_load(f)
            assert "/test/path" in saved_data["favorite_paths"]

    def test_config_property_lazy_load(self, tmp_path):
        """Test config property loads configuration when needed."""
        config_file = tmp_path / "config.yaml"

        manager = ConfigManager(config_file=config_file, auto_load=False)
        assert manager._config is None

        # Access property should trigger load
        config = manager.config
        assert isinstance(config, AppConfig)
        assert manager._config is not None

    def test_user_prefs_property_lazy_load(self, tmp_path):
        """Test user_prefs property loads preferences when needed."""
        prefs_file = tmp_path / "prefs.yaml"

        manager = ConfigManager(user_prefs_file=prefs_file, auto_load=False)
        assert manager._user_prefs is None

        # Access property should trigger load
        prefs = manager.user_prefs
        assert isinstance(prefs, UserPreferences)
        assert manager._user_prefs is not None

    def test_update_config(self, tmp_path):
        """Test updating configuration values."""
        config_file = tmp_path / "config.yaml"

        manager = ConfigManager(config_file=config_file, auto_load=True)
        success = manager.update_config(
            app_name="updated-app",
            version="2.0.0"
        )

        assert success is True
        assert manager.config.app_name == "updated-app"
        assert manager.config.version == "2.0.0"

    def test_update_user_preferences(self, tmp_path):
        """Test updating user preferences."""
        prefs_file = tmp_path / "prefs.yaml"

        manager = ConfigManager(user_prefs_file=prefs_file, auto_load=True)
        success = manager.update_user_preferences(
            favorite_paths=["/new/path1", "/new/path2"],
            last_scan_time="2024-01-01T12:00:00"
        )

        assert success is True
        assert len(manager.user_prefs.favorite_paths) == 2
        assert "/new/path1" in manager.user_prefs.favorite_paths
        assert manager.user_prefs.last_scan_time == "2024-01-01T12:00:00"

    @patch('ai_disk_cleanup.core.config_manager.CredentialStore')
    def test_get_api_key(self, mock_credential_store, tmp_path):
        """Test getting API key from credential store."""
        mock_store = Mock()
        mock_credential_store.return_value = mock_store
        mock_store.get_api_key.return_value = "test-api-key"

        manager = ConfigManager(auto_load=False)
        api_key = manager.get_api_key("openai")

        assert api_key == "test-api-key"
        mock_store.get_api_key.assert_called_once_with("openai")

    @patch('ai_disk_cleanup.core.config_manager.CredentialStore')
    def test_set_api_key(self, mock_credential_store, tmp_path):
        """Test setting API key in credential store."""
        mock_store = Mock()
        mock_credential_store.return_value = mock_store
        mock_store.set_api_key.return_value = True

        manager = ConfigManager(auto_load=False)
        success = manager.set_api_key("openai", "sk-test-key")

        assert success is True
        mock_store.set_api_key.assert_called_once_with("openai", "sk-test-key")

    def test_reset_to_defaults(self, tmp_path):
        """Test resetting configuration to defaults."""
        config_file = tmp_path / "config.yaml"
        prefs_file = tmp_path / "prefs.yaml"

        # Create custom config
        manager = ConfigManager(
            config_file=config_file,
            user_prefs_file=prefs_file,
            auto_load=True
        )
        manager.update_config(app_name="custom-app")
        manager.update_user_preferences(favorite_paths=["/custom"])

        # Reset to defaults
        success = manager.reset_to_defaults()

        assert success is True
        assert manager.config.app_name == "ai-disk-cleanup"  # Default value
        assert len(manager.user_prefs.favorite_paths) == 0  # Default empty list

    def test_export_config(self, tmp_path):
        """Test exporting configuration to file."""
        config_file = tmp_path / "config.yaml"
        export_file = tmp_path / "export.yaml"

        manager = ConfigManager(config_file=config_file, auto_load=True)
        manager.update_config(app_name="export-test")
        manager.update_user_preferences(favorite_paths=["/export/path"])

        success = manager.export_config(export_file)

        assert success is True
        assert export_file.exists()

        # Verify exported content
        with open(export_file, 'r') as f:
            exported_data = yaml.safe_load(f)
            assert "config" in exported_data
            assert "user_preferences" in exported_data
            assert exported_data["config"]["app_name"] == "export-test"
            assert "/export/path" in exported_data["user_preferences"]["favorite_paths"]

    def test_import_config(self, tmp_path):
        """Test importing configuration from file."""
        config_file = tmp_path / "config.yaml"
        import_file = tmp_path / "import.yaml"

        # Create import data
        import_data = {
            "config": {
                "app_name": "imported-app",
                "version": "3.0.0"
            },
            "user_preferences": {
                "favorite_paths": ["/imported/path"]
            }
        }

        with open(import_file, 'w') as f:
            yaml.dump(import_data, f)

        manager = ConfigManager(config_file=config_file, auto_load=False)
        success = manager.import_config(import_file)

        assert success is True
        assert manager.config.app_name == "imported-app"
        assert manager.config.version == "3.0.0"
        assert "/imported/path" in manager.user_prefs.favorite_paths

    def test_validate_config_valid(self, tmp_path):
        """Test configuration validation with valid config."""
        config_file = tmp_path / "config.yaml"

        manager = ConfigManager(config_file=config_file, auto_load=True)
        results = manager.validate_config()

        assert results['valid'] is True
        assert len(results['errors']) == 0

    def test_validate_config_with_issues(self, tmp_path):
        """Test configuration validation with issues."""
        config_file = tmp_path / "config.yaml"

        manager = ConfigManager(config_file=config_file, auto_load=True)

        # Simulate missing config
        manager._config = None
        results = manager.validate_config()

        assert results['valid'] is False
        assert "Configuration not loaded" in results['errors']

    @patch('ai_disk_cleanup.core.config_manager.CredentialStore')
    def test_validate_config_no_api_key(self, mock_credential_store, tmp_path):
        """Test configuration validation with missing API key."""
        mock_store = Mock()
        mock_credential_store.return_value = mock_store
        mock_store.get_api_key.return_value = None

        config_file = tmp_path / "config.yaml"

        manager = ConfigManager(config_file=config_file, auto_load=True)
        # Mock the credential store
        manager.credential_store = mock_store

        results = manager.validate_config()

        # Should still be valid but with warning about missing API key
        assert results['valid'] is True
        assert any("No API key configured" in warning for warning in results['warnings'])


class TestGlobalFunctions:
    """Test global convenience functions."""

    def test_get_config_manager_singleton(self):
        """Test that get_config_manager returns singleton instance."""
        with patch('ai_disk_cleanup.core.config_manager._config_manager', None):
            manager1 = get_config_manager()
            manager2 = get_config_manager()

            assert manager1 is manager2
            assert isinstance(manager1, ConfigManager)

    def test_get_config_function(self):
        """Test get_config convenience function."""
        with patch('ai_disk_cleanup.core.config_manager.get_config_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_config = Mock()
            mock_manager.config = mock_config
            mock_get_manager.return_value = mock_manager

            result = get_config()
            assert result is mock_config

    def test_get_user_preferences_function(self):
        """Test get_user_preferences convenience function."""
        with patch('ai_disk_cleanup.core.config_manager.get_config_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_prefs = Mock()
            mock_manager.user_prefs = mock_prefs
            mock_get_manager.return_value = mock_manager

            result = get_user_preferences()
            assert result is mock_prefs