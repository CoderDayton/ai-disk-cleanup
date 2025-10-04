"""
Tests for Windows installer builder.

These tests verify that the Windows builder can correctly create MSI installers
using PyInstaller and NSIS integration with proper code signing.
"""

import pytest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import yaml

from installer.builders.windows_builder import WindowsBuilder
from installer.config import InstallerConfig
from installer.orchestrator import BuildError


class TestWindowsBuilder:
    """Test the WindowsBuilder class."""

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
            # Mock PyInstaller being available
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "PyInstaller 5.0"

            # Should not raise any errors
            windows_builder.validate_dependencies()

    def test_validate_dependencies_pyinstaller_missing(self, windows_builder):
        """Test dependency validation when PyInstaller is missing."""
        with patch('subprocess.run') as mock_run:
            # Mock PyInstaller not found
            mock_run.side_effect = FileNotFoundError()

            with pytest.raises(BuildError, match="PyInstaller is required"):
                windows_builder.validate_dependencies()

    def test_validate_dependencies_pyinstaller_command_fails(self, windows_builder):
        """Test dependency validation when PyInstaller command fails."""
        with patch('subprocess.run') as mock_run:
            # Mock PyInstaller command failing
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "Command not found"

            with pytest.raises(BuildError, match="PyInstaller check failed"):
                windows_builder.validate_dependencies()

    def test_generate_nsis_script(self, windows_builder):
        """Test NSIS script generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "installer.nsi"

            windows_builder._generate_nsis_script(script_path)

            assert script_path.exists()
            content = script_path.read_text(encoding='utf-8')

            # Check that key sections are present
            assert "Name \"ai-disk-cleanup\"" in content
            assert "OutFile" in content
            assert "InstallDir" in content
            assert "Section \"MainSection\"" in content

    def test_generate_nsis_script_with_code_signing(self):
        """Test NSIS script generation with code signing enabled."""
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
                        "certificate_path": "/path/to/cert.p12",
                        "certificate_password": "password123"
                    }
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            config = InstallerConfig.load_from_file(config_path)
            builder = WindowsBuilder(config)

            with tempfile.TemporaryDirectory() as temp_dir:
                script_path = Path(temp_dir) / "installer.nsi"
                builder._generate_nsis_script(script_path)

                content = script_path.read_text(encoding='utf-8')
                assert "!execute" in content  # Code signing command
                assert "signtool" in content

        finally:
            config_path.unlink()

    def test_run_pyinstaller(self, windows_builder):
        """Test PyInstaller execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock PyInstaller execution
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "Build successful"

                output_path = windows_builder._run_pyinstaller(temp_dir)

                # Check that PyInstaller was called correctly
                mock_run.assert_called_once()
                args, kwargs = mock_run.call_args
                assert args[0][0] == "pyinstaller"
                assert "--onefile" in args[0]
                assert "--name=ai-disk-cleanup" in args[0]

                # Check output path
                assert output_path == Path(temp_dir) / "dist" / "ai-disk-cleanup.exe"

    def test_run_pyinstaller_failure(self, windows_builder):
        """Test PyInstaller execution failure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('subprocess.run') as mock_run:
                # Mock PyInstaller failure
                mock_run.return_value.returncode = 1
                mock_run.return_value.stderr = "Build failed"

                with pytest.raises(BuildError, match="PyInstaller build failed"):
                    windows_builder._run_pyinstaller(temp_dir)

    def test_sign_installer_no_signing(self, windows_builder):
        """Test installer signing when code signing is disabled."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_path.write_text("fake installer")

            try:
                # Should return the original path when signing is disabled
                result = windows_builder._sign_installer(temp_path)
                assert result == temp_path

            finally:
                temp_path.unlink()

    def test_sign_installer_with_signing(self):
        """Test installer signing when code signing is enabled."""
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
                        "certificate_path": "/path/to/cert.p12",
                        "certificate_password": "password123",
                        "timestamp_server": "http://timestamp.digicert.com"
                    }
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            config = InstallerConfig.load_from_file(config_path)
            builder = WindowsBuilder(config)

            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = Path(temp_file.name)
                temp_path.write_text("fake installer")

                with patch('subprocess.run') as mock_run:
                    mock_run.return_value.returncode = 0

                    try:
                        result = builder._sign_installer(temp_path)
                        assert result == temp_path

                        # Check that signtool was called
                        mock_run.assert_called()
                        args = mock_run.call_args[0][0]
                        assert "signtool" in args
                        assert "sign" in args
                        assert "/f" in args

                    finally:
                        temp_path.unlink()

        finally:
            config_path.unlink()

    def test_sign_installer_signing_failure(self):
        """Test installer signing failure handling."""
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
                        "certificate_path": "/path/to/cert.p12",
                        "certificate_password": "password123"
                    }
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            config = InstallerConfig.load_from_file(config_path)
            builder = WindowsBuilder(config)

            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = Path(temp_file.name)
                temp_path.write_text("fake installer")

                try:
                    with patch('subprocess.run') as mock_run:
                        # Mock signing failure
                        mock_run.return_value.returncode = 1
                        mock_run.return_value.stderr = "Signing failed"

                        with pytest.raises(BuildError, match="Code signing failed"):
                            builder._sign_installer(temp_path)
                finally:
                    temp_path.unlink()

        finally:
            config_path.unlink()

    def test_build_success(self, windows_builder):
        """Test successful build process."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(windows_builder, 'validate_dependencies'), \
                 patch.object(windows_builder, '_run_pyinstaller') as mock_pyinstaller, \
                 patch.object(windows_builder, '_generate_nsis_script') as mock_nsis, \
                 patch.object(windows_builder, '_sign_installer') as mock_sign:

                # Mock successful steps
                mock_pyinstaller.return_value = Path(temp_dir) / "dist" / "ai-disk-cleanup.exe"
                mock_sign.return_value = Path(temp_dir) / "installer.exe"

                result = windows_builder.build()

                # Verify all steps were called
                windows_builder.validate_dependencies.assert_called_once()
                mock_pyinstaller.assert_called_once()
                mock_nsis.assert_called_once()
                mock_sign.assert_called_once()

                assert result == Path(temp_dir) / "installer.exe"

    def test_build_pyinstaller_failure(self, windows_builder):
        """Test build failure when PyInstaller fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(windows_builder, 'validate_dependencies'), \
                 patch.object(windows_builder, '_run_pyinstaller') as mock_pyinstaller:

                # Mock PyInstaller failure
                mock_pyinstaller.side_effect = BuildError("PyInstaller failed")

                with pytest.raises(BuildError, match="PyInstaller failed"):
                    windows_builder.build()

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