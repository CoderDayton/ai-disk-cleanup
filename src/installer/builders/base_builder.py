"""
Base builder interface for platform-specific installers.

This module defines the abstract interface that all platform builders
must implement, ensuring consistent behavior across platforms.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional

from ..config import InstallerConfig


class BaseBuilder(ABC):
    """
    Abstract base class for platform-specific installers.

    This class defines the interface that all platform builders must implement,
    ensuring consistent behavior and capabilities across different platforms.
    """

    def __init__(self, config: InstallerConfig):
        """
        Initialize the builder with configuration.

        Args:
            config: Installer configuration
        """
        self.config = config
        self.platform = self._get_platform_name()

    @abstractmethod
    def _get_platform_name(self) -> str:
        """
        Get the platform name this builder handles.

        Returns:
            Platform name (e.g., "windows", "linux", "macos")
        """
        pass

    @abstractmethod
    def build(self) -> Path:
        """
        Build the installer for this platform.

        Returns:
            Path to the generated installer file

        Raises:
            BuildError: If the build fails
        """
        pass

    @abstractmethod
    def validate_dependencies(self) -> None:
        """
        Validate that all required dependencies are available.

        Raises:
            BuildError: If required dependencies are missing
        """
        pass

    def get_output_path(self) -> Path:
        """
        Get the output path for the installer.

        Returns:
            Path where the installer should be written
        """
        return self.config.get_output_path(self.platform)

    def get_platform_config(self) -> Dict[str, Any]:
        """
        Get platform-specific configuration.

        Returns:
            Platform configuration dictionary
        """
        return self.config.get_platform_config(self.platform)

    def get_code_signing_config(self) -> Dict[str, Any]:
        """
        Get code signing configuration for this platform.

        Returns:
            Code signing configuration
        """
        return self.config.get_code_signing_config(self.platform)

    def _ensure_output_directory(self) -> None:
        """Ensure the output directory exists."""
        output_path = self.get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)

    def _log_info(self, message: str) -> None:
        """Log an informational message."""
        print(f"[{self.platform.upper()}] {message}")

    def _log_error(self, message: str) -> None:
        """Log an error message."""
        print(f"[{self.platform.upper()} ERROR] {message}")

    def _log_warning(self, message: str) -> None:
        """Log a warning message."""
        print(f"[{self.platform.upper()} WARNING] {message}")