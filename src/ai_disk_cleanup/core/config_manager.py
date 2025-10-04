"""Configuration manager for AI disk cleanup application."""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, Union
import yaml

from .config_models import AppConfig, UserPreferences
from ..security.credential_store import CredentialStore
from ..security.input_sanitizer import get_sanitizer
from ..security.validation_schemas import CONFIG_SCHEMA, USER_PREFERENCE_SCHEMA


class ConfigManager:
    """Manages application configuration and user preferences."""

    def __init__(
        self,
        config_file: Optional[Union[str, Path]] = None,
        user_prefs_file: Optional[Union[str, Path]] = None,
        auto_load: bool = True
    ):
        """Initialize configuration manager.

        Args:
            config_file: Path to main configuration file
            user_prefs_file: Path to user preferences file
            auto_load: Whether to load configuration automatically
        """
        self.logger = logging.getLogger(__name__)

        # Determine config file paths
        if config_file is None:
            config_file = self._get_default_config_path()
        if user_prefs_file is None:
            user_prefs_file = self._get_default_prefs_path()

        self.config_file = Path(config_file)
        self.user_prefs_file = Path(user_prefs_file)

        # Initialize credential store
        self.credential_store = CredentialStore()

        # Initialize security components
        self.sanitizer = get_sanitizer(strict_mode=False)  # Default to normal mode for config

        # Configuration objects
        self._config: Optional[AppConfig] = None
        self._user_prefs: Optional[UserPreferences] = None

        # Load configuration if requested
        if auto_load:
            self.load_config()
            self.load_user_preferences()

    def _get_default_config_path(self) -> Path:
        """Get the default configuration file path."""
        import tempfile

        # Try environment variable first
        if 'AI_DISK_CLEANUP_CONFIG' in os.environ:
            return Path(os.environ['AI_DISK_CLEANUP_CONFIG'])

        # Use data directory
        temp_config = AppConfig()
        data_dir = temp_config.get_data_dir()
        return data_dir / 'config.yaml'

    def _get_default_prefs_path(self) -> Path:
        """Get the default user preferences file path."""
        import tempfile

        # Use data directory
        temp_config = AppConfig()
        data_dir = temp_config.get_data_dir()
        return data_dir / 'user_preferences.yaml'

    def load_config(self) -> AppConfig:
        """Load application configuration from file."""
        try:
            if self.config_file.exists():
                self.logger.info(f"Loading configuration from {self.config_file}")

                # Read configuration file
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    if self.config_file.suffix.lower() in ['.yaml', '.yml']:
                        config_data = yaml.safe_load(f)
                    else:
                        config_data = json.load(f)

                # Create config object with loaded data
                self._config = AppConfig(**config_data)
                self.logger.info("Configuration loaded successfully")
            else:
                self.logger.info("Configuration file not found, using defaults")
                self._config = AppConfig()
                self.save_config()  # Save default configuration

        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self.logger.info("Using default configuration")
            self._config = AppConfig()

        return self._config

    def save_config(self) -> bool:
        """Save current configuration to file."""
        if self._config is None:
            self.logger.error("No configuration to save")
            return False

        try:
            # Ensure parent directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            # Prepare configuration data
            config_data = self._config.dict(exclude_none=True)

            # Write configuration file
            with open(self.config_file, 'w', encoding='utf-8') as f:
                if self.config_file.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
                else:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Configuration saved to {self.config_file}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False

    def load_user_preferences(self) -> UserPreferences:
        """Load user preferences from file."""
        try:
            if self.user_prefs_file.exists():
                self.logger.info(f"Loading user preferences from {self.user_prefs_file}")

                # Read preferences file
                with open(self.user_prefs_file, 'r', encoding='utf-8') as f:
                    if self.user_prefs_file.suffix.lower() in ['.yaml', '.yml']:
                        prefs_data = yaml.safe_load(f) or {}
                    else:
                        prefs_data = json.load(f)

                # Create preferences object
                self._user_prefs = UserPreferences(**prefs_data)
                self.logger.info("User preferences loaded successfully")
            else:
                self.logger.info("User preferences file not found, using defaults")
                self._user_prefs = UserPreferences()
                self.save_user_preferences()  # Save default preferences

        except Exception as e:
            self.logger.error(f"Failed to load user preferences: {e}")
            self.logger.info("Using default user preferences")
            self._user_prefs = UserPreferences()

        return self._user_prefs

    def save_user_preferences(self) -> bool:
        """Save current user preferences to file."""
        if self._user_prefs is None:
            self.logger.error("No user preferences to save")
            return False

        try:
            # Ensure parent directory exists
            self.user_prefs_file.parent.mkdir(parents=True, exist_ok=True)

            # Prepare preferences data
            prefs_data = self._user_prefs.dict(exclude_none=True)

            # Write preferences file
            with open(self.user_prefs_file, 'w', encoding='utf-8') as f:
                if self.user_prefs_file.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(prefs_data, f, default_flow_style=False, indent=2)
                else:
                    json.dump(prefs_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"User preferences saved to {self.user_prefs_file}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save user preferences: {e}")
            return False

    @property
    def config(self) -> AppConfig:
        """Get current application configuration."""
        if self._config is None:
            self._config = self.load_config()
        return self._config

    @property
    def user_prefs(self) -> UserPreferences:
        """Get current user preferences."""
        if self._user_prefs is None:
            self._user_prefs = self.load_user_preferences()
        return self._user_prefs

    def update_config(self, **kwargs) -> bool:
        """Update configuration with new values."""
        if self._config is None:
            self._config = AppConfig()

        try:
            # Handle nested updates (e.g., ai_model__provider)
            current_data = self._config.model_dump()

            for key, value in kwargs.items():
                if '__' in key:
                    # Handle nested update like ai_model__provider
                    parts = key.split('__')
                    target = current_data
                    for part in parts[:-1]:
                        if part not in target:
                            target[part] = {}
                        target = target[part]
                    target[parts[-1]] = value
                else:
                    # Direct update
                    current_data[key] = value

            self._config = AppConfig(**current_data)

            # Save if auto-save is enabled
            if self.config.ui.auto_save_preferences:
                return self.save_config()

            return True

        except Exception as e:
            self.logger.error(f"Failed to update configuration: {e}")
            return False

    def update_user_preferences(self, **kwargs) -> bool:
        """Update user preferences with new values."""
        if self._user_prefs is None:
            self._user_prefs = UserPreferences()

        try:
            # Create new preferences with updated values
            current_data = self._user_prefs.model_dump()
            current_data.update(kwargs)
            self._user_prefs = UserPreferences(**current_data)

            # Save if auto-save is enabled
            if self.config.ui.auto_save_preferences:
                return self.save_user_preferences()

            return True

        except Exception as e:
            self.logger.error(f"Failed to update user preferences: {e}")
            return False

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for specified provider."""
        try:
            return self.credential_store.get_api_key(provider)
        except Exception as e:
            self.logger.error(f"Failed to get API key for {provider}: {e}")
            return None

    def set_api_key(self, provider: str, api_key: str) -> bool:
        """Set API key for specified provider."""
        try:
            return self.credential_store.set_api_key(provider, api_key)
        except Exception as e:
            self.logger.error(f"Failed to set API key for {provider}: {e}")
            return False

    def delete_api_key(self, provider: str) -> bool:
        """Delete API key for specified provider."""
        try:
            return self.credential_store.delete_api_key(provider)
        except Exception as e:
            self.logger.error(f"Failed to delete API key for {provider}: {e}")
            return False

    def reset_to_defaults(self) -> bool:
        """Reset configuration to default values."""
        try:
            self._config = AppConfig()
            self._user_prefs = UserPreferences()

            # Save default configuration
            return self.save_config() and self.save_user_preferences()

        except Exception as e:
            self.logger.error(f"Failed to reset configuration: {e}")
            return False

    def export_config(self, export_path: Union[str, Path]) -> bool:
        """Export current configuration to specified file."""
        try:
            export_path = Path(export_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)

            # Prepare export data
            export_data = {
                'config': self.config.dict(exclude_none=True),
                'user_preferences': self.user_prefs.dict(exclude_none=True),
                'export_timestamp': str(Path().resolve()),
                'version': self.config.version
            }

            # Write export file
            with open(export_path, 'w', encoding='utf-8') as f:
                if export_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(export_data, f, default_flow_style=False, indent=2)
                else:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Configuration exported to {export_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export configuration: {e}")
            return False

    def import_config(self, import_path: Union[str, Path]) -> bool:
        """Import configuration from specified file."""
        try:
            import_path = Path(import_path)

            if not import_path.exists():
                raise FileNotFoundError(f"Import file not found: {import_path}")

            # Validate import path
            path_validation = self.sanitizer.sanitize_file_path(import_path)
            if not path_validation.is_valid:
                self.logger.error(f"Invalid import path: {path_validation.security_events}")
                return False

            # Read import file
            with open(import_path, 'r', encoding='utf-8') as f:
                if import_path.suffix.lower() in ['.yaml', '.yml']:
                    import_data = yaml.safe_load(f)
                else:
                    import_data = json.load(f)

            # Validate import data structure
            if not isinstance(import_data, dict):
                self.logger.error("Import data must be a dictionary")
                return False

            # Import configuration with validation
            if 'config' in import_data:
                config_data = import_data['config']
                if not isinstance(config_data, dict):
                    self.logger.error("Configuration data must be a dictionary")
                    return False

                # Sanitize and validate each configuration value
                sanitized_config = {}
                for key, value in config_data.items():
                    validation_result = self.sanitizer.sanitize_config_value(
                        key, value, CONFIG_SCHEMA
                    )
                    if not validation_result.is_valid:
                        self.logger.error(f"Invalid config value for '{key}': {validation_result.security_events}")
                        return False
                    sanitized_config[key] = validation_result.sanitized_value

                # Log any security warnings
                for key, value in config_data.items():
                    validation_result = self.sanitizer.sanitize_config_value(key, value, CONFIG_SCHEMA)
                    for event in validation_result.security_events:
                        if 'WARNING' in event:
                            self.logger.warning(f"Security warning in config import: {event}")

                self._config = AppConfig(**sanitized_config)

            # Import user preferences with validation
            if 'user_preferences' in import_data:
                prefs_data = import_data['user_preferences']
                if not isinstance(prefs_data, dict):
                    self.logger.error("User preferences data must be a dictionary")
                    return False

                # Sanitize and validate each preference value
                sanitized_prefs = {}
                for key, value in prefs_data.items():
                    validation_result = self.sanitizer.sanitize_config_value(
                        key, value, USER_PREFERENCE_SCHEMA
                    )
                    if not validation_result.is_valid:
                        self.logger.error(f"Invalid preference value for '{key}': {validation_result.security_events}")
                        return False
                    sanitized_prefs[key] = validation_result.sanitized_value

                self._user_prefs = UserPreferences(**sanitized_prefs)

            # Save imported configuration
            return self.save_config() and self.save_user_preferences()

        except Exception as e:
            self.logger.error(f"Failed to import configuration: {e}")
            return False

    def validate_config(self) -> Dict[str, Any]:
        """Validate current configuration and return validation results."""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        try:
            # Validate configuration object
            if self._config is not None:
                config_dict = self._config.model_dump()
                AppConfig(**config_dict)  # This will raise if invalid
            else:
                validation_results['errors'].append("Configuration not loaded")
                validation_results['valid'] = False

            # Validate user preferences
            if self._user_prefs is not None:
                prefs_dict = self._user_prefs.model_dump()
                UserPreferences(**prefs_dict)  # This will raise if invalid
            else:
                validation_results['warnings'].append("User preferences not loaded")

            # Check API key availability
            if self.config.ai_model.provider:
                api_key = self.get_api_key(self.config.ai_model.provider)
                if not api_key:
                    validation_results['warnings'].append(
                        f"No API key configured for provider: {self.config.ai_model.provider}"
                    )

            # Check data directories
            try:
                data_dir = self.config.get_data_dir()
                if not data_dir.exists():
                    validation_results['warnings'].append(f"Data directory does not exist: {data_dir}")

                cache_dir = self.config.get_cache_dir()
                if not cache_dir.exists():
                    validation_results['warnings'].append(f"Cache directory does not exist: {cache_dir}")

                backup_dir = self.config.get_backup_dir()
                if not backup_dir.exists():
                    validation_results['warnings'].append(f"Backup directory does not exist: {backup_dir}")

            except Exception as e:
                validation_results['errors'].append(f"Failed to access data directories: {e}")
                validation_results['valid'] = False

        except Exception as e:
            validation_results['errors'].append(f"Configuration validation failed: {e}")
            validation_results['valid'] = False

        return validation_results


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> AppConfig:
    """Get the current application configuration."""
    return get_config_manager().config


def get_user_preferences() -> UserPreferences:
    """Get the current user preferences."""
    return get_config_manager().user_prefs