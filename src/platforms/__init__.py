"""
Platform adapter module for cross-platform file operations.

This module provides platform-specific adapters that implement a unified interface
for file operations across Windows, macOS, and Linux.
"""

from .base_adapter import (
    BaseAdapter,
    PlatformType,
    FileOperationResult,
    PlatformAdapterError,
    UnsupportedPlatformError,
    FileOperationError
)

from .windows_adapter import WindowsAdapter
from .macos_adapter import MacOSAdapter
from .linux_adapter import LinuxAdapter
from .factory import PlatformAdapterFactory, get_platform_adapter

__all__ = [
    'BaseAdapter',
    'PlatformType',
    'FileOperationResult',
    'PlatformAdapterError',
    'UnsupportedPlatformError',
    'FileOperationError',
    'WindowsAdapter',
    'MacOSAdapter',
    'LinuxAdapter',
    'PlatformAdapterFactory',
    'get_platform_adapter'
]