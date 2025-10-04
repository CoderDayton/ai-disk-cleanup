"""
Installer configuration management.

This module provides configuration management for the cross-platform installer,
including validation of build settings and platform-specific configurations.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml


class ConfigValidationError(Exception):
    """Raised when there's an error in the installer configuration."""
    pass


class InstallerConfig:
    """
    Configuration manager for the cross-platform installer.

    Handles loading, validation, and access to configuration settings
    for different platforms and build scenarios.
    """

    def __init__(self, config_data: Dict[str, Any]):
        """Initialize configuration from loaded data."""
        self._config = config_data
        self._validate()

    @classmethod
    def load_from_file(cls, config_path: Path) -> "InstallerConfig":
        """
        Load configuration from a YAML file.

        Args:
            config_path: Path to the configuration file

        Returns:
            InstallerConfig instance

        Raises:
            ConfigValidationError: If the config file is invalid
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Invalid YAML in config file: {e}")
        except FileNotFoundError:
            raise ConfigValidationError(f"Configuration file not found: {config_path}")

        return cls(config_data)

    def _validate(self) -> None:
        """Validate the configuration data."""
        # Check required top-level sections
        if "project" not in self._config:
            raise ConfigValidationError("Missing required section: project")

        if "build" not in self._config:
            raise ConfigValidationError("Missing required section: build")

        if "platforms" not in self._config:
            raise ConfigValidationError("Missing required section: platforms")

        # Validate project section
        project = self._config["project"]
        required_project_fields = ["name", "version", "description"]
        for field in required_project_fields:
            if field not in project:
                raise ConfigValidationError(f"Missing required field: project.{field}")

        # Validate build section
        build = self._config["build"]
        if "output_dir" not in build:
            raise ConfigValidationError("Missing required field: build.output_dir")

        # Validate platforms section
        platforms = self._config["platforms"]
        if not platforms:
            raise ConfigValidationError("At least one platform must be configured")

        # Check that at least one platform is enabled
        enabled_platforms = self.get_enabled_platforms()
        if not enabled_platforms:
            raise ConfigValidationError("No platforms are enabled")

    @property
    def project_name(self) -> str:
        """Get the project name."""
        return self._config["project"]["name"]

    @property
    def version(self) -> str:
        """Get the project version."""
        return self._config["project"]["version"]

    @property
    def description(self) -> str:
        """Get the project description."""
        return self._config["project"]["description"]

    @property
    def output_dir(self) -> Path:
        """Get the output directory for installers."""
        return Path(self._config["build"]["output_dir"])

    @property
    def python_version(self) -> str:
        """Get the required Python version."""
        return self._config["build"].get("python_version", "3.13")

    def is_platform_enabled(self, platform: str) -> bool:
        """
        Check if a platform is enabled in the configuration.

        Args:
            platform: Platform name (windows, linux, macos)

        Returns:
            True if the platform is enabled, False otherwise
        """
        platform_config = self._config["platforms"].get(platform, {})
        return platform_config.get("enabled", False)

    @property
    def windows_enabled(self) -> bool:
        """Check if Windows installer is enabled."""
        return self.is_platform_enabled("windows")

    @property
    def linux_enabled(self) -> bool:
        """Check if Linux installer is enabled."""
        return self.is_platform_enabled("linux")

    @property
    def macos_enabled(self) -> bool:
        """Check if macOS installer is enabled."""
        return self.is_platform_enabled("macos")

    def get_enabled_platforms(self) -> List[str]:
        """
        Get a list of all enabled platforms.

        Returns:
            List of enabled platform names
        """
        enabled = []
        for platform in ["windows", "linux", "macos"]:
            if self.is_platform_enabled(platform):
                enabled.append(platform)
        return enabled

    def get_platform_config(self, platform: str) -> Dict[str, Any]:
        """
        Get platform-specific configuration.

        Args:
            platform: Platform name

        Returns:
            Platform configuration dictionary

        Raises:
            ConfigValidationError: If platform is not configured
        """
        if platform not in self._config["platforms"]:
            raise ConfigValidationError(f"Platform '{platform}' not found in configuration")

        return self._config["platforms"][platform]

    def get_output_path(self, platform: str) -> Path:
        """
        Get the output path for a platform's installer.

        Args:
            platform: Platform name

        Returns:
            Path where the installer should be written
        """
        config = self.get_platform_config(platform)
        installer_type = config.get("installer_type", "unknown")

        # Map installer types to file extensions
        extensions = {
            "msi": "msi",
            "appimage": "AppImage",
            "deb": "deb",
            "rpm": "rpm",
            "pkg": "pkg",
            "dmg": "dmg"
        }

        ext = extensions.get(installer_type.lower(), "bin")
        filename = f"{self.project_name}-{self.version}-{platform}.{ext}"

        return self.output_dir / filename

    @property
    def windows_installer_type(self) -> str:
        """Get the Windows installer type."""
        config = self.get_platform_config("windows")
        return config.get("installer_type", "msi")

    @property
    def linux_installer_type(self) -> str:
        """Get the Linux installer type."""
        config = self.get_platform_config("linux")
        return config.get("installer_type", "appimage")

    def get_code_signing_config(self, platform: str) -> Dict[str, Any]:
        """
        Get code signing configuration for a platform.

        Args:
            platform: Platform name

        Returns:
            Code signing configuration
        """
        config = self.get_platform_config(platform)
        return config.get("code_signing", {"enabled": False})

    def to_dict(self) -> Dict[str, Any]:
        """
        Get the configuration as a dictionary.

        Returns:
            Configuration dictionary
        """
        return self._config.copy()

    def save_to_file(self, config_path: Path) -> None:
        """
        Save the configuration to a YAML file.

        Args:
            config_path: Path where to save the configuration
        """
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, default_flow_style=False, indent=2)