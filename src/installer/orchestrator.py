"""
Build orchestrator for cross-platform installers.

This module coordinates the build process across different platforms,
managing the overall build workflow and handling errors gracefully.
"""

import sys
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .config import InstallerConfig, ConfigValidationError


@dataclass
class BuildResult:
    """Result of a build operation."""
    success: bool
    platform: str
    output_path: Optional[Path] = None
    error: Optional[Exception] = None
    build_time: Optional[float] = None


class BuildError(Exception):
    """Raised when a build operation fails."""
    pass


class BuildOrchestrator:
    """
    Orchestrates the build process for cross-platform installers.

    This class manages the overall build workflow, coordinates between
    different platform builders, and handles error recovery.
    """

    def __init__(self, config: InstallerConfig):
        """
        Initialize the build orchestrator.

        Args:
            config: Installer configuration
        """
        self.config = config
        self.builders: Dict[str, Any] = {}
        self.build_state: Dict[str, BuildResult] = {}

    def register_builder(self, platform: str, builder) -> None:
        """
        Register a platform-specific builder.

        Args:
            platform: Platform name (windows, linux, macos)
            builder: Platform builder instance

        Raises:
            BuildError: If a builder for the platform is already registered
        """
        if platform in self.builders:
            raise BuildError(f"Builder for platform '{platform}' already registered")

        self.builders[platform] = builder

    def validate_build_environment(self) -> None:
        """
        Validate that the build environment is properly set up.

        Raises:
            BuildError: If the environment is not suitable for building
        """
        # Check Python version
        required_python = (3, 13)
        if sys.version_info < required_python:
            raise BuildError(
                f"Python {required_python[0]}.{required_python[1]} or higher is required, "
                f"found {sys.version_info[0]}.{sys.version_info[1]}"
            )

        # Check if PyInstaller is available
        try:
            result = subprocess.run(
                ["pyinstaller", "--version"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                raise BuildError("PyInstaller is required but not found")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            raise BuildError("PyInstaller is required but not found in PATH")

    def build_platform(self, platform: str) -> BuildResult:
        """
        Build installer for a specific platform.

        Args:
            platform: Platform name to build for

        Returns:
            BuildResult with the outcome of the build

        Raises:
            BuildError: If the platform is not enabled or no builder is registered
        """
        import time
        start_time = time.time()

        # Validate platform is enabled
        if not self.config.is_platform_enabled(platform):
            raise BuildError(f"Platform '{platform}' is not enabled in configuration")

        # Check if builder is registered
        if platform not in self.builders:
            raise BuildError(f"No builder registered for platform '{platform}'")

        # Create output directory
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Run the build
            builder = self.builders[platform]
            output_path = builder.build()

            build_time = time.time() - start_time
            result = BuildResult(
                success=True,
                platform=platform,
                output_path=output_path,
                build_time=build_time
            )

            self.build_state[platform] = result
            return result

        except Exception as e:
            build_time = time.time() - start_time
            result = BuildResult(
                success=False,
                platform=platform,
                error=e,
                build_time=build_time
            )

            self.build_state[platform] = result
            return result

    def build_all(self) -> Dict[str, BuildResult]:
        """
        Build installers for all enabled platforms.

        Returns:
            Dictionary mapping platform names to build results
        """
        results = {}
        enabled_platforms = self.config.get_enabled_platforms()

        for platform in enabled_platforms:
            try:
                results[platform] = self.build_platform(platform)
            except Exception as e:
                # Create a failed result if build_platform itself fails
                results[platform] = BuildResult(
                    success=False,
                    platform=platform,
                    error=e
                )

        return results

    def get_build_status(self) -> Dict[str, Dict[str, any]]:
        """
        Get the current build status for all platforms.

        Returns:
            Dictionary with build status information
        """
        status = {}
        for platform, result in self.build_state.items():
            status[platform] = {
                "success": result.success,
                "output_path": str(result.output_path) if result.output_path else None,
                "error": str(result.error) if result.error else None,
                "build_time": result.build_time
            }

        return status

    def clean_build_directory(self) -> None:
        """
        Clean the build output directory.

        Removes all generated installers and intermediate files.
        """
        if self.config.output_dir.exists():
            shutil.rmtree(self.config.output_dir)

        # Clear build state
        self.build_state.clear()

    def get_builder(self, platform: str) -> Any:
        """
        Get the registered builder for a platform.

        Args:
            platform: Platform name

        Returns:
            Platform builder instance

        Raises:
            BuildError: If no builder is registered for the platform
        """
        if platform not in self.builders:
            raise BuildError(f"No builder registered for platform '{platform}'")

        return self.builders[platform]

    def get_build_summary(self) -> Dict[str, any]:
        """
        Get a summary of the most recent builds.

        Returns:
            Build summary with statistics and results
        """
        total_builds = len(self.build_state)
        successful_builds = sum(1 for result in self.build_state.values() if result.success)
        failed_builds = total_builds - successful_builds

        total_build_time = sum(
            result.build_time for result in self.build_state.values()
            if result.build_time is not None
        )

        return {
            "total_builds": total_builds,
            "successful_builds": successful_builds,
            "failed_builds": failed_builds,
            "success_rate": successful_builds / total_builds if total_builds > 0 else 0,
            "total_build_time": total_build_time,
            "platforms": list(self.build_state.keys()),
            "build_state": self.get_build_status()
        }