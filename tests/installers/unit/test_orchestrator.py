"""
Tests for the build orchestrator.

These tests verify that the build orchestrator can correctly coordinate
the build process across different platforms.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from installer.orchestrator import BuildOrchestrator, BuildError
from installer.config import InstallerConfig


class TestBuildOrchestrator:
    """Test the BuildOrchestrator class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        config = Mock(spec=InstallerConfig)
        config.project_name = "ai-disk-cleanup"
        config.version = "0.1.0"
        config.output_dir = Path("dist/installers")
        config.get_enabled_platforms.return_value = ["windows", "linux"]
        config.get_platform_config.side_effect = lambda platform: {
            "windows": {"installer_type": "msi", "code_signing": True},
            "linux": {"installer_type": "appimage", "code_signing": True}
        }[platform]
        config.get_output_path.side_effect = lambda platform: {
            "windows": Path("dist/installers/ai-disk-cleanup-0.1.0-windows.msi"),
            "linux": Path("dist/installers/ai-disk-cleanup-0.1.0-linux.AppImage")
        }[platform]
        return config

    @pytest.fixture
    def orchestrator(self, mock_config):
        """Create a BuildOrchestrator instance for testing."""
        return BuildOrchestrator(mock_config)

    def test_initialization(self, mock_config):
        """Test that the orchestrator initializes correctly."""
        orchestrator = BuildOrchestrator(mock_config)

        assert orchestrator.config == mock_config
        assert len(orchestrator.builders) == 0
        assert orchestrator.build_state == {}

    def test_register_builder(self, orchestrator):
        """Test registering a platform builder."""
        mock_builder = Mock()
        mock_builder.platform = "windows"

        orchestrator.register_builder("windows", mock_builder)

        assert "windows" in orchestrator.builders
        assert orchestrator.builders["windows"] == mock_builder

    def test_register_builder_duplicate_platform(self, orchestrator):
        """Test that registering a builder for an existing platform raises an error."""
        mock_builder = Mock()
        mock_builder.platform = "windows"

        orchestrator.register_builder("windows", mock_builder)

        # Try to register another builder for the same platform
        with pytest.raises(BuildError, match="Builder for platform 'windows' already registered"):
            orchestrator.register_builder("windows", mock_builder)

    def test_build_single_platform(self, orchestrator):
        """Test building for a single platform."""
        # Register a mock builder
        mock_builder = Mock()
        mock_builder.platform = "windows"
        mock_builder.build.return_value = Path("dist/installers/test.msi")

        orchestrator.register_builder("windows", mock_builder)

        # Build for Windows only
        result = orchestrator.build_platform("windows")

        assert result.success is True
        assert result.output_path == Path("dist/installers/test.msi")
        mock_builder.build.assert_called_once()

    def test_build_single_platform_not_enabled(self, orchestrator):
        """Test building for a platform that's not enabled in config."""
        # Configure the mock to return enabled platforms
        orchestrator.config.get_enabled_platforms.return_value = ["windows", "linux"]
        # Configure the mock to return False for macos
        orchestrator.config.is_platform_enabled.return_value = False

        with pytest.raises(BuildError, match="Platform 'macos' is not enabled"):
            orchestrator.build_platform("macos")

    def test_build_single_platform_no_builder(self, orchestrator):
        """Test building for a platform with no registered builder."""
        # Windows is enabled but no builder is registered
        with pytest.raises(BuildError, match="No builder registered for platform 'windows'"):
            orchestrator.build_platform("windows")

    def test_build_all_platforms_success(self, orchestrator):
        """Test building for all enabled platforms."""
        # Register mock builders
        windows_builder = Mock()
        windows_builder.platform = "windows"
        windows_builder.build.return_value = Path("dist/installers/test.msi")

        linux_builder = Mock()
        linux_builder.platform = "linux"
        linux_builder.build.return_value = Path("dist/installers/test.AppImage")

        orchestrator.register_builder("windows", windows_builder)
        orchestrator.register_builder("linux", linux_builder)

        # Build all platforms
        results = orchestrator.build_all()

        assert len(results) == 2
        assert "windows" in results
        assert "linux" in results
        assert results["windows"].success is True
        assert results["linux"].success is True

        windows_builder.build.assert_called_once()
        linux_builder.build.assert_called_once()

    def test_build_all_platforms_partial_failure(self, orchestrator):
        """Test building when one platform fails."""
        # Register mock builders
        windows_builder = Mock()
        windows_builder.platform = "windows"
        windows_builder.build.return_value = Path("dist/installers/test.msi")

        linux_builder = Mock()
        linux_builder.platform = "linux"
        linux_builder.build.side_effect = BuildError("Linux build failed")

        orchestrator.register_builder("windows", windows_builder)
        orchestrator.register_builder("linux", linux_builder)

        # Build all platforms
        results = orchestrator.build_all()

        assert len(results) == 2
        assert results["windows"].success is True
        assert results["linux"].success is False
        assert "Linux build failed" in str(results["linux"].error)

    def test_build_platform_with_error(self, orchestrator):
        """Test handling of build errors."""
        # Register a builder that fails
        mock_builder = Mock()
        mock_builder.platform = "windows"
        mock_builder.build.side_effect = BuildError("Build failed")

        orchestrator.register_builder("windows", mock_builder)

        # Build should handle the error gracefully
        result = orchestrator.build_platform("windows")

        assert result.success is False
        assert "Build failed" in str(result.error)

    def test_get_build_status(self, orchestrator):
        """Test getting build status."""
        # Initially no builds have been attempted
        status = orchestrator.get_build_status()
        assert len(status) == 0

        # Register a builder and simulate a build
        mock_builder = Mock()
        mock_builder.platform = "windows"
        mock_builder.build.return_value = Path("test.msi")

        orchestrator.register_builder("windows", mock_builder)
        result = orchestrator.build_platform("windows")

        # Now status should show the build result
        status = orchestrator.get_build_status()
        assert len(status) == 1
        assert "windows" in status
        assert status["windows"]["success"] is True

    def test_clean_build_directory(self, orchestrator):
        """Test cleaning the build directory."""
        # Mock the file system operations
        with patch('shutil.rmtree') as mock_rmtree, \
             patch('pathlib.Path.exists', return_value=True):

            orchestrator.clean_build_directory()

            mock_rmtree.assert_called_once_with(orchestrator.config.output_dir)

    def test_validate_build_environment_success(self, orchestrator):
        """Test successful build environment validation."""
        with patch('sys.version_info', (3, 13, 0)), \
             patch('subprocess.run') as mock_subprocess:

            mock_subprocess.return_value.returncode = 0
            mock_subprocess.return_value.stdout = "PyInstaller 5.0"

            # Should not raise any errors
            orchestrator.validate_build_environment()

    def test_validate_build_environment_wrong_python_version(self, orchestrator):
        """Test build environment validation with wrong Python version."""
        with patch('sys.version_info', (3, 11, 0)):
            with pytest.raises(BuildError, match="Python 3.13 or higher is required"):
                orchestrator.validate_build_environment()

    def test_validate_build_environment_pyinstaller_missing(self, orchestrator):
        """Test build environment validation when PyInstaller is missing."""
        with patch('sys.version_info', (3, 13, 0)), \
             patch('subprocess.run') as mock_subprocess:

            # Simulate PyInstaller not found
            mock_subprocess.side_effect = FileNotFoundError()

            with pytest.raises(BuildError, match="PyInstaller is required"):
                orchestrator.validate_build_environment()