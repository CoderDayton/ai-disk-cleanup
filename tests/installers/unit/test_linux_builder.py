"""
Tests for Linux AppImage builder.

These tests verify that the Linux builder can correctly create AppImage installers
with proper dependency management, GPG signing, and Linux distribution compatibility.
"""

import pytest
import tempfile
import stat
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import yaml

from installer.builders.linux_builder import LinuxBuilder
from installer.config import InstallerConfig
from installer.orchestrator import BuildError


class TestLinuxBuilder:
    """Test the LinuxBuilder class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for Linux testing."""
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
                "linux": {
                    "enabled": True,
                    "installer_type": "appimage",
                    "icon": "assets/icon.png",
                    "dependencies": ["python3", "tkinter"],
                    "code_signing": {
                        "enabled": False,
                        "gpg_key_id": "",
                        "gpg_key_path": ""
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
    def linux_builder(self, mock_config):
        """Create a LinuxBuilder instance for testing."""
        return LinuxBuilder(mock_config)

    def test_initialization(self, mock_config):
        """Test that the Linux builder initializes correctly."""
        builder = LinuxBuilder(mock_config)

        assert builder.platform == "linux"
        assert builder.config == mock_config
        assert builder.get_platform_config()["installer_type"] == "appimage"

    def test_get_platform_name(self, linux_builder):
        """Test that the platform name is correct."""
        assert linux_builder._get_platform_name() == "linux"

    def test_validate_dependencies_pyinstaller_available(self, linux_builder):
        """Test dependency validation when PyInstaller is available."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "PyInstaller 5.0"

            linux_builder.validate_dependencies()

    def test_validate_dependencies_pyinstaller_missing(self, linux_builder):
        """Test dependency validation when PyInstaller is missing."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()

            with pytest.raises(BuildError, match="PyInstaller is required"):
                linux_builder.validate_dependencies()

    def test_detect_linux_distribution(self, linux_builder):
        """Test Linux distribution detection."""
        with patch('platform.system', return_value='Linux'), \
             patch('subprocess.run') as mock_run:

            # Mock different distributions
            test_cases = [
                ("Ubuntu 20.04", "ubuntu"),
                ("CentOS Linux 8", "centos"),
                ("Fedora 38", "fedora"),
                ("Debian GNU/Linux 12", "debian"),
                ("Arch Linux", "arch")
            ]

            for output, expected in test_cases:
                mock_run.return_value.stdout = output
                distro = linux_builder._detect_linux_distribution()
                assert distro == expected

    def test_detect_linux_distribution_failure(self, linux_builder):
        """Test distribution detection failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, 'lsb_release')

            # Should fall back to generic detection
            distro = linux_builder._detect_linux_distribution()
            assert distro in ["generic", "unknown"]

    def test_get_dependencies_for_distribution(self, linux_builder):
        """Test getting distribution-specific dependencies."""
        platform_config = linux_builder.get_platform_config()
        base_deps = platform_config.get("dependencies", [])

        # Test Ubuntu dependencies
        ubuntu_deps = linux_builder._get_dependencies_for_distribution("ubuntu")
        assert base_deps[0] in ubuntu_deps  # Should include base dependencies
        assert any("python3-tk" in dep for dep in ubuntu_deps)  # Should include tkinter

        # Test CentOS dependencies
        centos_deps = linux_builder._get_dependencies_for_distribution("centos")
        assert base_deps[0] in centos_deps
        assert any("python3-tkinter" in dep for dep in centos_deps)

        # Test generic dependencies
        generic_deps = linux_builder._get_dependencies_for_distribution("unknown")
        assert generic_deps == base_deps

    def test_create_appimage_script(self, linux_builder):
        """Test AppImage script creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "AppRun"

            linux_builder._create_appimage_script(script_path)

            assert script_path.exists()
            content = script_path.read_text(encoding='utf-8')

            # Check that key elements are present
            assert "#!/bin/bash" in content
            assert "exec" in content
            assert "ai-disk-cleanup" in content

            # Check script is executable
            assert script_path.stat().st_mode & stat.S_IXUSR

    def test_create_appimage_desktop_file(self, linux_builder):
        """Test AppImage desktop file creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            desktop_path = Path(temp_dir) / "ai-disk-cleanup.desktop"

            linux_builder._create_appimage_desktop_file(desktop_path)

            assert desktop_path.exists()
            content = desktop_path.read_text(encoding='utf-8')

            # Check required desktop file sections
            assert "[Desktop Entry]" in content
            assert "Name=AI Disk Cleanup" in content
            assert "Exec=" in content
            assert "Icon=" in content
            assert "Categories=" in content

    def test_create_appimage_structure(self, linux_builder):
        """Test AppImage directory structure creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            appdir_path = Path(temp_dir) / "AI_Disk Cleanup.AppDir"
            executable_path = Path(temp_dir) / "ai-disk-cleanup"

            # Create a fake executable
            executable_path.write_text("fake executable")
            executable_path.chmod(0o755)

            linux_builder._create_appimage_structure(
                executable_path,
                appdir_path
            )

            # Check structure was created
            assert appdir_path.exists()
            assert (appdir_path / "AppRun").exists()
            assert (appdir_path / "ai-disk-cleanup.desktop").exists()
            assert (appdir_path / "usr" / "bin" / "ai-disk-cleanup").exists()
            assert (appdir_path / "ai-disk-cleanup.png").exists()

    def test_run_pyinstaller(self, linux_builder):
        """Test PyInstaller execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "Build successful"

                output_path = linux_builder._run_pyinstaller(temp_dir)

                mock_run.assert_called_once()
                args, kwargs = mock_run.call_args
                assert args[0][0] == "pyinstaller"
                assert "--onefile" in args[0]

                expected_path = temp_dir / "dist" / "ai-disk-cleanup"
                assert output_path == expected_path

    def test_run_pyinstaller_failure(self, linux_builder):
        """Test PyInstaller execution failure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 1
                mock_run.return_value.stderr = "Build failed"

                with pytest.raises(BuildError, match="PyInstaller build failed"):
                    linux_builder._run_pyinstaller(temp_dir)

    def test_create_appimage_with_appimagetool(self, linux_builder):
        """Test AppImage creation with AppImageTool."""
        with tempfile.TemporaryDirectory() as temp_dir:
            appdir_path = temp_dir / "AI_DiskCleanup.AppDir"
            appdir_path.mkdir()

            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0

                appimage_path = linux_builder._create_appimage_with_appimagetool(
                    appdir_path,
                    temp_dir
                )

                mock_run.assert_called_once()
                args = mock_run.call_args[0][0]
                assert "appimagetool" in " ".join(args)
                assert str(appdir_path) in " ".join(args)

                expected_path = temp_dir / "AI_DiskCleanup.AppImage"
                assert appimage_path == expected_path

    def test_create_appimage_with_appimagetool_failure(self, linux_builder):
        """Test AppImage creation failure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            appdir_path = temp_dir / "AI_DiskCleanup.AppDir"
            appdir_path.mkdir()

            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 1
                mock_run.return_value.stderr = "AppImage creation failed"

                with pytest.raises(BuildError, match="AppImage creation failed"):
                    linux_builder._create_appimage_with_appimagetool(appdir_path, temp_dir)

    def test_create_fallback_appimage(self, linux_builder):
        """Test fallback AppImage creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            appdir_path = temp_dir / "AI_DiskCleanup.AppDir"
            appdir_path.mkdir()

            # Create fake executable
            (appdir_path / "AppRun").write_text("#!/bin/bash\nexec echo test")
            (appdir_path / "AppRun").chmod(0o755)

            appimage_path = linux_builder._create_fallback_appimage(appdir_path, temp_dir)

            assert appimage_path.exists()
            assert appimage_path.name == "AI_DiskCleanup.AppImage"

    def test_sign_appimage_no_signing(self, linux_builder):
        """Test AppImage signing when GPG signing is disabled."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_path.write_text("fake appimage")

            try:
                result = linux_builder._sign_appimage(temp_path)
                assert result == temp_path

            finally:
                temp_path.unlink()

    def test_sign_appimage_with_gpg(self):
        """Test AppImage signing with GPG."""
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
                "linux": {
                    "enabled": True,
                    "installer_type": "appimage",
                    "code_signing": {
                        "enabled": True,
                        "gpg_key_id": "test@key.com",
                        "gpg_key_path": "/path/to/key.gpg"
                    }
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            config = InstallerConfig.load_from_file(config_path)
            builder = LinuxBuilder(config)

            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = Path(temp_file.name)
                temp_path.write_text("fake appimage")

                with patch('subprocess.run') as mock_run:
                    mock_run.return_value.returncode = 0

                    try:
                        result = builder._sign_appimage(temp_path)
                        assert result == temp_path

                        mock_run.assert_called()
                        args = mock_run.call_args[0][0]
                        assert "gpg" in args
                        assert "--detach-sign" in args

                    finally:
                        temp_path.unlink()

        finally:
            config_path.unlink()

    def test_build_success(self, linux_builder):
        """Test successful build process."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(linux_builder, 'validate_dependencies'), \
                 patch.object(linux_builder, '_run_pyinstaller') as mock_pyinstaller, \
                 patch.object(linux_builder, '_create_appimage_structure') as mock_structure, \
                 patch.object(linux_builder, '_create_appimage_with_appimagetool') as mock_appimage, \
                 patch.object(linux_builder, '_sign_appimage') as mock_sign:

                # Mock successful steps
                temp_dir_path = Path(temp_dir)
                mock_pyinstaller.return_value = temp_dir_path / "dist" / "ai-disk-cleanup"
                mock_appimage.return_value = temp_dir_path / "AI_DiskCleanup.AppImage"
                mock_sign.return_value = temp_dir_path / "AI_DiskCleanup.AppImage"

                result = linux_builder.build()

                # Verify all steps were called
                linux_builder.validate_dependencies.assert_called_once()
                mock_pyinstaller.assert_called_once()
                mock_structure.assert_called_once()
                mock_appimage.assert_called_once()
                mock_sign.assert_called_once()

                assert result == linux_builder.get_output_path()

    def test_get_output_path(self, linux_builder):
        """Test getting the output path for the Linux AppImage."""
        output_path = linux_builder.get_output_path()
        expected = Path("dist/installers/ai-disk-cleanup-0.1.0-linux.AppImage")
        assert output_path == expected