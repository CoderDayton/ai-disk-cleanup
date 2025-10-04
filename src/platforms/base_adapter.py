"""
Base platform adapter defining the abstract interface for all platform-specific implementations.

This module provides the abstract base class that ensures consistent behavior across all
platforms while allowing platform-specific optimizations and integrations.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from dataclasses import dataclass


class PlatformType(Enum):
    """Enumeration of supported platforms."""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"


@dataclass
class FileOperationResult:
    """Result of a file operation."""
    success: bool
    error_message: Optional[str] = None
    data: Optional[Any] = None


class PlatformAdapterError(Exception):
    """Base exception for platform adapter errors."""
    pass


class UnsupportedPlatformError(PlatformAdapterError):
    """Raised when the current platform is not supported."""
    pass


class FileOperationError(PlatformAdapterError):
    """Raised when a file operation fails."""
    pass


class BaseAdapter(ABC):
    """
    Abstract base class defining the platform adapter interface.

    This interface ensures consistent behavior across all platforms while
    allowing platform-specific optimizations and integrations.
    """

    def __init__(self):
        self._platform_type = self._detect_platform()
        self._validate_platform_support()

    @property
    @abstractmethod
    def platform_type(self) -> PlatformType:
        """Get the platform type this adapter handles."""
        pass

    @abstractmethod
    def _detect_platform(self) -> PlatformType:
        """Detect the current platform."""
        pass

    @abstractmethod
    def _validate_platform_support(self) -> None:
        """Validate that the current platform is supported."""
        pass

    @abstractmethod
    def normalize_path(self, path: Union[str, Path]) -> Path:
        """Normalize a path for the current platform."""
        pass

    @abstractmethod
    def get_file_manager_integration(self) -> Dict[str, Any]:
        """Get platform-specific file manager integration capabilities."""
        pass

    @abstractmethod
    def get_directory_size(self, path: Path) -> int:
        """Calculate the total size of a directory."""
        pass

    @abstractmethod
    def list_directory_contents(self, path: Path, recursive: bool = False) -> List[Path]:
        """List directory contents, optionally recursively."""
        pass

    @abstractmethod
    def move_to_trash(self, path: Path) -> FileOperationResult:
        """Move a file or directory to the system trash/recycle bin."""
        pass

    @abstractmethod
    def restore_from_trash(self, original_path: Path) -> FileOperationResult:
        """Restore a file or directory from the system trash/recycle bin."""
        pass

    @abstractmethod
    def open_in_file_manager(self, path: Path) -> FileOperationResult:
        """Open the given path in the system's file manager."""
        pass

    @abstractmethod
    def get_file_metadata(self, path: Path) -> Dict[str, Any]:
        """Get platform-specific file metadata."""
        pass

    @abstractmethod
    def set_file_permissions(self, path: Path, permissions: Dict[str, Any]) -> FileOperationResult:
        """Set file permissions in a platform-appropriate way."""
        pass

    @abstractmethod
    def optimize_for_platform(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply platform-specific optimizations for given operations."""
        pass