"""
Tests for installer configuration management.

These tests verify that the installer can correctly load, validate, and manage
configuration for different platforms and build scenarios.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import yaml

from installer.config import InstallerConfig, ConfigValidationError


class TestInstallerConfig:
    """Test the InstallerConfig class."""

    def test_load_valid_config(self):
        """Test loading a valid configuration file."""
        # Create a temporary config file
        config_data = {
            "project": {
                "name": "ai-disk-cleanup",
                "version": "0.1.0",
                "description": "AI-powered disk cleanup tool"
            },
            "build": {
                "output_dir": "dist/installers",
                "python_version": "3.13"
            },
            "platforms": {
                "windows": {
                    "enabled": True,
                    "installer_type": "msi",
                    "code_signing": True
                },
                "linux": {
                    "enabled": True,
                    "installer_type": "appimage",
                    "code_signing": True
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # Test loading the config
            config = InstallerConfig.load_from_file(config_path)

            assert config.project_name == "ai-disk-cleanup"
            assert config.version == "0.1.0"
            assert config.windows_enabled is True
            assert config.linux_enabled is True
            assert config.windows_installer_type == "msi"
            assert config.linux_installer_type == "appimage"

        finally:
            config_path.unlink()

    def test_load_invalid_config_missing_required_fields(self):
        """Test that loading config with missing required fields raises an error."""
        config_data = {
            "project": {
                "name": "ai-disk-cleanup"
                # Missing version
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            with pytest.raises(ConfigValidationError, match="Missing required section"):
                InstallerConfig.load_from_file(config_path)

        finally:
            config_path.unlink()

    def test_platform_validation(self):
        """Test platform-specific validation."""
        config_data = {
            "project": {
                "name": "ai-disk-cleanup",
                "version": "0.1.0",
                "description": "Test"
            },
            "build": {
                "output_dir": "dist",
                "python_version": "3.13"
            },
            "platforms": {
                "windows": {
                    "enabled": True,
                    "installer_type": "msi"
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            config = InstallerConfig.load_from_file(config_path)

            # Should work - Windows is configured
            assert config.get_enabled_platforms() == ["windows"]

            # Should raise error - no platforms enabled
            config._config["platforms"]["windows"]["enabled"] = False
            with pytest.raises(ConfigValidationError, match="No platforms are enabled"):
                config._validate()

        finally:
            config_path.unlink()

    def test_get_platform_config(self):
        """Test getting platform-specific configuration."""
        config_data = {
            "project": {
                "name": "ai-disk-cleanup",
                "version": "0.1.0",
                "description": "Test"
            },
            "build": {
                "output_dir": "dist",
                "python_version": "3.13"
            },
            "platforms": {
                "windows": {
                    "enabled": True,
                    "installer_type": "msi",
                    "code_signing": {
                        "enabled": True,
                        "certificate_path": "/path/to/cert.p12"
                    }
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            config = InstallerConfig.load_from_file(config_path)

            windows_config = config.get_platform_config("windows")
            assert windows_config["installer_type"] == "msi"
            assert windows_config["code_signing"]["enabled"] is True
            assert windows_config["code_signing"]["certificate_path"] == "/path/to/cert.p12"

            # Test getting non-existent platform
            with pytest.raises(ConfigValidationError, match="Platform 'macos' not found"):
                config.get_platform_config("macos")

        finally:
            config_path.unlink()

    def test_output_paths(self):
        """Test that output paths are correctly generated."""
        config_data = {
            "project": {
                "name": "ai-disk-cleanup",
                "version": "0.1.0",
                "description": "Test"
            },
            "build": {
                "output_dir": "dist/installers",
                "python_version": "3.13"
            },
            "platforms": {
                "windows": {
                    "enabled": True,
                    "installer_type": "msi"
                },
                "linux": {
                    "enabled": True,
                    "installer_type": "appimage"
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            config = InstallerConfig.load_from_file(config_path)

            windows_path = config.get_output_path("windows")
            assert windows_path == Path("dist/installers/ai-disk-cleanup-0.1.0-windows.msi")

            linux_path = config.get_output_path("linux")
            assert linux_path == Path("dist/installers/ai-disk-cleanup-0.1.0-linux.AppImage")

        finally:
            config_path.unlink()