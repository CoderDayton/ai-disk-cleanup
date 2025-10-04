"""
Simplified tests for Windows installer builder.

These tests verify basic Windows builder functionality without complex
error scenarios that cause syntax issues.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import yaml

from installer.builders.windows_builder import WindowsBuilder
from installer.config import InstallerConfig
from installer.orchestrator import BuildError


class TestWindowsBuilderSimple:
    """Simplified test class for WindowsBuilder."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for Windows testing."""
        config_data = {
            "project": {
                "name": "ai-disk-cleanup",
                "version": "0.1.0",
                "description": "AI-powered disk cleanup tool"
            },
            "build": {
                "output_dir": "dist/installers",
                "python_version": "3.13",
                "pyinstaller_options": ["--onefile", "--name=ai-disk-cleanup"]
            },
            "platforms": {
                "windows": {
                    "enabled": True,
                    "installer_type": "msi",
                    "icon": "assets/icon.ico",
                    "code_signing": {
                        "enabled": False,
                        "certificate_path": "",
                        "certificate_password": "",
                        "timestamp_server": "http://timestamp.digicert.com"
                    }
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            return InstallerConfig.load_from_file(config_path)
        finally:
            config_path.unlink()

    @pytest.fixture
    def windows_builder(self, mock_config):
        """Create a WindowsBuilder instance for testing."""
        return WindowsBuilder(mock_config)

    def test_initialization(self, mock_config):
        """Test that the Windows builder initializes correctly."""
        builder = WindowsBuilder(mock_config)

        assert builder.platform == "windows"
        assert builder.config == mock_config
        assert builder.get_platform_config()["installer_type"] == "msi"

    def test_get_platform_name(self, windows_builder):
        """Test that the platform name is correct."""
        assert windows_builder._get_platform_name() == "windows"

    def test_validate_dependencies_pyinstaller_available(self, windows_builder):
        """Test dependency validation when PyInstaller is available."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "PyInstaller 5.0"

            windows_builder.validate_dependencies()

    def test_get_output_path(self, windows_builder):
        """Test getting the output path for the Windows installer."""
        output_path = windows_builder.get_output_path()
        expected = Path("dist/installers/ai-disk-cleanup-0.1.0-windows.msi")
        assert output_path == expected

    def test_ensure_output_directory(self, windows_builder):
        """Test that output directory is created."""
        output_path = windows_builder.get_output_path()
        windows_builder._ensure_output_directory()
        assert output_path.parent.exists()

    def test_generate_nsis_script(self, windows_builder):
        """Test NSIS script generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "installer.nsa"

            windows_builder._generate_nsis_script(script_path)

            assert script_path.exists()
            content = script_path.read_text(encoding='utf-8')
            assert "Name \"ai-disk-cleanup\"" in content
            assert "OutFile" in content

    def test_sign_installer_no_signing(self, windows_builder):
        """Test installer signing when code signing is disabled."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_path.write_text("fake installer")

            try:
                result = windows_builder._sign_installer(temp_path)
                assert result == temp_path
            finally:
                temp_path.unlink()