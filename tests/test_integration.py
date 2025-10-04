"""Integration tests for configuration and credential management."""

import json
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, Mock

from ai_disk_cleanup.core.config_manager import ConfigManager
from ai_disk_cleanup.core.config_models import AppConfig, UserPreferences, ConfidenceLevel, CleanupScope
from ai_disk_cleanup.security.credential_store import CredentialStore


class TestConfigurationIntegration:
    """Integration tests for the complete configuration system."""

    def test_full_configuration_workflow(self):
        """Test complete configuration workflow from creation to usage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_file = temp_path / "config.yaml"
            prefs_file = temp_path / "prefs.yaml"

            # Initialize configuration manager
            manager = ConfigManager(
                config_file=config_file,
                user_prefs_file=prefs_file,
                auto_load=True
            )

            # Verify default configuration
            assert manager.config.app_name == "ai-disk-cleanup"
            assert manager.config.ai_model.provider == "openai"
            assert manager.config.security.min_confidence_threshold == ConfidenceLevel.HIGH
            assert manager.config.cleanup.default_scope == CleanupScope.HOME_DIRECTORY

            # Customize configuration
            manager.update_config(
                app_name="test-app",
                ai_model__provider="anthropic",
                ai_model__model_name="claude-3",
                security__min_confidence_threshold=ConfidenceLevel.VERY_HIGH,
                security__require_confirmation=False,
                cleanup__file_age_threshold_days=7
            )

            # Customize user preferences
            manager.update_user_preferences(
                favorite_paths=["/home/user/docs", "/home/user/downloads"],
                recent_scans=["/tmp"],
                custom_rules={"temp_files": {"delete": True, "age_days": 1}}
            )

            # Verify configuration files were created
            assert config_file.exists()
            assert prefs_file.exists()

            # Load configuration in new manager instance
            manager2 = ConfigManager(
                config_file=config_file,
                user_prefs_file=prefs_file,
                auto_load=True
            )

            # Verify settings persisted
            assert manager2.config.app_name == "test-app"
            assert manager2.config.ai_model.provider == "anthropic"
            assert manager2.config.ai_model.model_name == "claude-3"
            assert manager2.config.security.min_confidence_threshold == ConfidenceLevel.VERY_HIGH
            assert manager2.config.security.require_confirmation is False
            assert manager2.config.cleanup.file_age_threshold_days == 7

            assert len(manager2.user_prefs.favorite_paths) == 2
            assert "/home/user/docs" in manager2.user_prefs.favorite_paths
            assert "/tmp" in manager2.user_prefs.recent_scans
            assert "temp_files" in manager2.user_prefs.custom_rules

    @patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', True)
    @patch('ai_disk_cleanup.security.credential_store.keyring')
    def test_credential_integration(self, mock_keyring):
        """Test credential storage integration with configuration."""
        # Mock keyring operations
        mock_keyring.get_keyring.return_value = Mock()
        mock_keyring.get_password.return_value = None

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_file = temp_path / "config.yaml"

            # Initialize configuration manager
            manager = ConfigManager(config_file=config_file, auto_load=True)

            # Store API keys
            openai_key = "sk-openai-test-key-1234567890abcdef"
            anthropic_key = "sk-ant-anthropic-test-key-1234567890abcdef"

            success1 = manager.set_api_key("openai", openai_key)
            success2 = manager.set_api_key("anthropic", anthropic_key)

            assert success1 is True
            assert success2 is True

            # Mock the stored encrypted keys for retrieval
            mock_keyring.get_password.side_effect = lambda service, username: {
                "api_key_openai": manager.credential_store._encrypt_data(openai_key),
                "api_key_anthropic": manager.credential_store._encrypt_data(anthropic_key),
                "ai-disk-cleanup_encryption": "dummy"  # For encryption key
            }.get(username)

            # Retrieve API keys
            retrieved_openai = manager.get_api_key("openai")
            retrieved_anthropic = manager.get_api_key("anthropic")

            assert retrieved_openai == openai_key
            assert retrieved_anthropic == anthropic_key

            # List providers
            providers = manager.credential_store.list_providers()
            assert "openai" in providers
            assert "anthropic" in providers

            # Test API keys
            openai_result = manager.test_api_key("openai")
            anthropic_result = manager.test_api_key("anthropic")

            assert openai_result['valid'] is True
            assert anthropic_result['valid'] is True

            # Delete API keys
            delete_success1 = manager.delete_api_key("openai")
            delete_success2 = manager.delete_api_key("anthropic")

            assert delete_success1 is True
            assert delete_success2 is True

    def test_configuration_validation_integration(self):
        """Test configuration validation in integrated environment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_file = temp_path / "config.yaml"

            manager = ConfigManager(config_file=config_file, auto_load=True)

            # Validate default configuration
            results = manager.validate_config()
            assert results['valid'] is True
            assert len(results['errors']) == 0

            # Test validation with missing directories (should create warnings)
            # Force invalid data directory
            manager._config.data_dir = Path("/nonexistent/path")
            results = manager.validate_config()

            assert len(results['warnings']) > 0
            assert any("does not exist" in warning for warning in results['warnings'])

    def test_configuration_export_import_integration(self):
        """Test configuration export and import functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_file = temp_path / "config.yaml"
            export_file = temp_path / "export.yaml"
            import_file = temp_path / "import.yaml"

            # Create and customize configuration
            manager1 = ConfigManager(config_file=config_file, auto_load=True)
            manager1.update_config(
                app_name="export-test",
                ai_model__provider="anthropic"
            )
            manager1.update_user_preferences(
                favorite_paths=["/export/test"]
            )

            # Export configuration
            export_success = manager1.export_config(export_file)
            assert export_success is True
            assert export_file.exists()

            # Create new manager and import configuration
            config_file2 = temp_path / "config2.yaml"
            manager2 = ConfigManager(config_file=config_file2, auto_load=False)
            import_success = manager2.import_config(export_file)
            assert import_success is True

            # Verify imported configuration
            assert manager2.config.app_name == "export-test"
            assert manager2.config.ai_model.provider == "anthropic"
            assert "/export/test" in manager2.user_prefs.favorite_paths

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-env-test-key'})
    def test_environment_variable_fallback(self):
        """Test environment variable fallback for API keys."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_file = temp_path / "config.yaml"

            # Initialize manager with keyring unavailable
            with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False):
                manager = ConfigManager(config_file=config_file, auto_load=True)

                # Should get API key from environment
                api_key = manager.get_api_key("openai")
                assert api_key == "sk-env-test-key"

                # Test API key validation
                result = manager.test_api_key("openai")
                assert result['valid'] is True

    def test_platform_specific_paths(self):
        """Test platform-specific data directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create config with custom data directory
            config = AppConfig(data_dir=temp_path / "custom_data")

            # Test data directory creation
            data_dir = config.get_data_dir()
            assert data_dir.exists()
            assert data_dir == temp_path / "custom_data"

            # Test cache directory creation
            cache_dir = config.get_cache_dir()
            assert cache_dir.exists()
            assert cache_dir == temp_path / "custom_data" / "cache"

            # Test backup directory creation
            backup_dir = config.get_backup_dir()
            assert backup_dir.exists()
            assert backup_dir == temp_path / "custom_data" / "backups"

    def test_json_and_yaml_support(self):
        """Test support for both JSON and YAML configuration formats."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test YAML format
            yaml_config_file = temp_path / "config.yaml"
            manager_yaml = ConfigManager(config_file=yaml_config_file, auto_load=True)
            manager_yaml.update_config(app_name="yaml-test")
            assert yaml_config_file.exists()

            # Test JSON format
            json_config_file = temp_path / "config.json"
            manager_json = ConfigManager(config_file=json_config_file, auto_load=True)
            manager_json.update_config(app_name="json-test")
            assert json_config_file.exists()

            # Verify files contain correct format
            with open(yaml_config_file, 'r') as f:
                yaml_content = f.read()
                assert "app_name: yaml-test" in yaml_content

            with open(json_config_file, 'r') as f:
                json_content = json.load(f)
                assert json_content["app_name"] == "json-test"

    def test_concurrent_access_safety(self):
        """Test configuration system handles concurrent access safely."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_file = temp_path / "config.yaml"

            # Create multiple managers
            manager1 = ConfigManager(config_file=config_file, auto_load=True)
            manager2 = ConfigManager(config_file=config_file, auto_load=True)

            # Update configuration through both managers
            manager1.update_config(app_name="manager1-update")
            manager2.update_config(app_name="manager2-update")

            # Verify both can read the final state
            # Note: In a real scenario, you might need file locking
            # This test ensures the basic functionality works
            assert manager1.config.app_name == "manager2-update"
            assert manager2.config.app_name == "manager2-update"