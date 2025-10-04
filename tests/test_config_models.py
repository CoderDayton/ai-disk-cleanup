"""Tests for configuration data models."""

import pytest
from pathlib import Path
from ai_disk_cleanup.core.config_models import (
    AppConfig,
    UserPreferences,
    AIModelConfig,
    SecurityConfig,
    UserInterfaceConfig,
    CleanupConfig,
    ConfidenceLevel,
    ProtectionMode,
    CleanupScope,
)


class TestAppConfig:
    """Test AppConfig model."""

    def test_default_config_creation(self):
        """Test creating default configuration."""
        config = AppConfig()

        assert config.app_name == "ai-disk-cleanup"
        assert config.version == "0.1.0"
        assert config.config_version == "1.0"
        assert isinstance(config.ai_model, AIModelConfig)
        assert isinstance(config.security, SecurityConfig)
        assert isinstance(config.ui, UserInterfaceConfig)
        assert isinstance(config.cleanup, CleanupConfig)

    def test_config_customization(self):
        """Test customizing configuration values."""
        config = AppConfig(
            app_name="custom-app",
            version="2.0.0"
        )

        assert config.app_name == "custom-app"
        assert config.version == "2.0.0"

    def test_data_directory_creation(self, tmp_path):
        """Test data directory creation."""
        config = AppConfig(data_dir=tmp_path / "test_data")

        data_dir = config.get_data_dir()
        assert data_dir.exists()
        assert data_dir == tmp_path / "test_data"

    def test_cache_directory_creation(self, tmp_path):
        """Test cache directory creation."""
        config = AppConfig(cache_dir=tmp_path / "test_cache")

        cache_dir = config.get_cache_dir()
        assert cache_dir.exists()
        assert cache_dir == tmp_path / "test_cache"

    def test_backup_directory_creation(self, tmp_path):
        """Test backup directory creation."""
        config = AppConfig(backup_dir=tmp_path / "test_backup")

        backup_dir = config.get_backup_dir()
        assert backup_dir.exists()
        assert backup_dir == tmp_path / "test_backup"

    def test_config_serialization(self):
        """Test configuration serialization."""
        config = AppConfig()
        config_dict = config.dict()

        assert "app_name" in config_dict
        assert "ai_model" in config_dict
        assert "security" in config_dict
        assert "ui" in config_dict
        assert "cleanup" in config_dict

    def test_config_validation(self):
        """Test configuration validation."""
        # Test valid configuration
        config = AppConfig()
        assert config is not None

        # Test validation with invalid data
        with pytest.raises(ValueError):
            AIModelConfig(temperature=3.0)  # Invalid temperature value


class TestAIModelConfig:
    """Test AIModelConfig model."""

    def test_default_ai_config(self):
        """Test default AI model configuration."""
        config = AIModelConfig()

        assert config.provider == "openai"
        assert config.model_name == "gpt-4"
        assert config.max_tokens == 4096
        assert config.temperature == 0.1
        assert config.timeout_seconds == 30

    def test_ai_config_validation(self):
        """Test AI model configuration validation."""
        # Valid temperature values
        config = AIModelConfig(temperature=0.5)
        assert config.temperature == 0.5

        # Test temperature rounding
        config = AIModelConfig(temperature=0.123456)
        assert config.temperature == 0.12

        # Invalid temperature values
        with pytest.raises(ValueError):
            AIModelConfig(temperature=-0.1)

        with pytest.raises(ValueError):
            AIModelConfig(temperature=2.1)

    def test_ai_config_customization(self):
        """Test AI model configuration customization."""
        config = AIModelConfig(
            provider="anthropic",
            model_name="claude-3",
            max_tokens=2048,
            temperature=0.7,
            timeout_seconds=60
        )

        assert config.provider == "anthropic"
        assert config.model_name == "claude-3"
        assert config.max_tokens == 2048
        assert config.temperature == 0.7
        assert config.timeout_seconds == 60


class TestSecurityConfig:
    """Test SecurityConfig model."""

    def test_default_security_config(self):
        """Test default security configuration."""
        config = SecurityConfig()

        assert config.min_confidence_threshold == ConfidenceLevel.HIGH
        assert isinstance(config.protected_paths, list)
        assert isinstance(config.protected_extensions, list)
        assert isinstance(config.protected_patterns, list)
        assert config.require_confirmation is True
        assert config.backup_before_delete is True

    def test_security_config_customization(self):
        """Test security configuration customization."""
        config = SecurityConfig(
            min_confidence_threshold=ConfidenceLevel.VERY_HIGH,
            require_confirmation=False,
            backup_before_delete=False,
            backup_retention_days=7
        )

        assert config.min_confidence_threshold == ConfidenceLevel.VERY_HIGH
        assert config.require_confirmation is False
        assert config.backup_before_delete is False
        assert config.backup_retention_days == 7

    def test_protected_defaults(self):
        """Test default protected paths and extensions."""
        config = SecurityConfig()

        # Check default protected extensions
        assert '.exe' in config.protected_extensions
        assert '.dll' in config.protected_extensions
        assert '.sys' in config.protected_extensions

        # Check default protected patterns
        assert '*.system*' in config.protected_patterns
        assert '*critical*' in config.protected_patterns


class TestUserInterfaceConfig:
    """Test UserInterfaceConfig model."""

    def test_default_ui_config(self):
        """Test default UI configuration."""
        config = UserInterfaceConfig()

        assert config.theme == "dark"
        assert config.log_level == "INFO"
        assert config.show_progress is True
        assert config.verbose_output is False
        assert config.language == "en"
        assert config.auto_save_preferences is True

    def test_ui_config_customization(self):
        """Test UI configuration customization."""
        config = UserInterfaceConfig(
            theme="light",
            log_level="DEBUG",
            verbose_output=True,
            language="fr"
        )

        assert config.theme == "light"
        assert config.log_level == "DEBUG"
        assert config.verbose_output is True
        assert config.language == "fr"


class TestCleanupConfig:
    """Test CleanupConfig model."""

    def test_default_cleanup_config(self):
        """Test default cleanup configuration."""
        config = CleanupConfig()

        assert config.default_scope == CleanupScope.HOME_DIRECTORY
        assert isinstance(config.custom_paths, list)
        assert isinstance(config.exclude_paths, list)
        assert config.file_age_threshold_days == 30
        assert config.dry_run_by_default is True
        assert config.batch_size == 50

    def test_cleanup_config_customization(self):
        """Test cleanup configuration customization."""
        config = CleanupConfig(
            default_scope=CleanupScope.CUSTOM_PATHS,
            file_age_threshold_days=7,
            dry_run_by_default=False,
            batch_size=100
        )

        assert config.default_scope == CleanupScope.CUSTOM_PATHS
        assert config.file_age_threshold_days == 7
        assert config.dry_run_by_default is False
        assert config.batch_size == 100

    def test_default_exclude_paths(self):
        """Test default exclude paths."""
        config = CleanupConfig()

        assert "~/.config" in config.exclude_paths
        assert "~/.ssh" in config.exclude_paths
        assert "~/.gnupg" in config.exclude_paths


class TestUserPreferences:
    """Test UserPreferences model."""

    def test_default_user_preferences(self):
        """Test default user preferences."""
        prefs = UserPreferences()

        assert isinstance(prefs.favorite_paths, list)
        assert isinstance(prefs.recent_scans, list)
        assert isinstance(prefs.custom_rules, dict)
        assert isinstance(prefs.shortcuts, dict)
        assert isinstance(prefs.statistics, dict)
        assert prefs.last_scan_time is None

    def test_user_preferences_customization(self):
        """Test user preferences customization."""
        prefs = UserPreferences(
            favorite_paths=["/home/user/documents", "/home/user/downloads"],
            recent_scans=["/tmp", "/var/log"],
            custom_rules={"temp_files": {"age_days": 1}},
            shortcuts={"ctrl+s": "save", "ctrl+q": "quit"}
        )

        assert len(prefs.favorite_paths) == 2
        assert "/home/user/documents" in prefs.favorite_paths
        assert len(prefs.recent_scans) == 2
        assert "/tmp" in prefs.recent_scans
        assert "temp_files" in prefs.custom_rules
        assert "ctrl+s" in prefs.shortcuts


class TestEnums:
    """Test enumeration values."""

    def test_confidence_levels(self):
        """Test confidence level enum values."""
        assert ConfidenceLevel.LOW.value == "low"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.VERY_HIGH.value == "very_high"

    def test_protection_modes(self):
        """Test protection mode enum values."""
        assert ProtectionMode.PROTECT_NONE.value == "protect_none"
        assert ProtectionMode.PROTECT_LOW.value == "protect_low"
        assert ProtectionMode.PROTECT_MEDIUM.value == "protect_medium"
        assert ProtectionMode.PROTECT_HIGH.value == "protect_high"
        assert ProtectionMode.PROTECT_CRITICAL.value == "protect_critical"

    def test_cleanup_scopes(self):
        """Test cleanup scope enum values."""
        assert CleanupScope.HOME_DIRECTORY.value == "home_directory"
        assert CleanupScope.CUSTOM_PATHS.value == "custom_paths"
        assert CleanupScope.TEMP_FILES.value == "temp_files"
        assert CleanupScope.SYSTEM_CACHE.value == "system_cache"