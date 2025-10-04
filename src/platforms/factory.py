"""
Platform adapter factory for creating appropriate adapter instances.

This module provides a factory pattern implementation for creating the correct
platform adapter based on the current operating system.
"""

import platform
from typing import Type

from .base_adapter import BaseAdapter, PlatformType
from .windows_adapter import WindowsAdapter
from .macos_adapter import MacOSAdapter
from .linux_adapter import LinuxAdapter


class PlatformAdapterFactory:
    """Factory class for creating platform-specific adapters."""

    _adapter_map = {
        PlatformType.WINDOWS: WindowsAdapter,
        PlatformType.MACOS: MacOSAdapter,
        PlatformType.LINUX: LinuxAdapter,
    }

    @classmethod
    def create_adapter(cls, platform_type: PlatformType = None) -> BaseAdapter:
        """
        Create a platform adapter instance.

        Args:
            platform_type: Specific platform type to create adapter for.
                          If None, detects current platform automatically.

        Returns:
            Platform adapter instance for the specified or detected platform.

        Raises:
            UnsupportedPlatformError: If the platform is not supported.
        """
        if platform_type is None:
            platform_type = cls._detect_current_platform()

        adapter_class = cls._adapter_map.get(platform_type)
        if adapter_class is None:
            from .base_adapter import UnsupportedPlatformError
            raise UnsupportedPlatformError(f"Platform {platform_type.value} is not supported")

        return adapter_class()

    @classmethod
    def _detect_current_platform(self) -> PlatformType:
        """Detect the current platform automatically."""
        system = platform.system().lower()

        if system == 'windows':
            return PlatformType.WINDOWS
        elif system == 'darwin':
            return PlatformType.MACOS
        elif system == 'linux':
            return PlatformType.LINUX
        else:
            from .base_adapter import UnsupportedPlatformError
            raise UnsupportedPlatformError(f"Unsupported platform: {system}")

    @classmethod
    def get_supported_platforms(cls) -> list[PlatformType]:
        """Get list of supported platform types."""
        return list(cls._adapter_map.keys())

    @classmethod
    def is_platform_supported(cls, platform_type: PlatformType) -> bool:
        """Check if a platform type is supported."""
        return platform_type in cls._adapter_map


def get_platform_adapter(platform_type: PlatformType = None) -> BaseAdapter:
    """
    Convenience function to get a platform adapter instance.

    Args:
        platform_type: Specific platform type. If None, auto-detects.

    Returns:
        Platform adapter instance.
    """
    return PlatformAdapterFactory.create_adapter(platform_type)