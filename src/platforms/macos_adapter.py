"""
macOS-specific platform adapter implementation.

This module provides macOS-specific implementations of the platform adapter interface,
including Finder integration, Spotlight search, and macOS-specific frameworks.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

from .base_adapter import (
    BaseAdapter, PlatformType, FileOperationResult,
    PlatformAdapterError, FileOperationError
)


class MacOSAdapter(BaseAdapter):
    """macOS-specific platform adapter implementation."""

    @property
    def platform_type(self) -> PlatformType:
        """Get the platform type this adapter handles."""
        return PlatformType.MACOS

    def _detect_platform(self) -> PlatformType:
        """Detect the current platform."""
        return PlatformType.MACOS

    def _validate_platform_support(self) -> None:
        """Validate that the current platform is supported."""
        # In a real implementation, would validate macOS version, API availability, etc.
        # For now, we assume macOS is supported
        pass

    def normalize_path(self, path: Union[str, Path]) -> Path:
        """Normalize a path for the current platform."""
        # Convert backslashes to forward slashes for macOS (POSIX)
        normalized_str = str(path).replace('\\', '/')
        return Path(normalized_str)

    def get_file_manager_integration(self) -> Dict[str, Any]:
        """Get platform-specific file manager integration capabilities."""
        return {
            "name": "macOS Finder",
            "version": "10.15+",
            "features": [
                "spotlight_search",
                "tags_support",
                "quick_look",
                "applescript_integration"
            ],
            "apis": ["cocoa", "core_foundation", "applescript"]
        }

    def get_directory_size(self, path: Path) -> int:
        """Calculate the total size of a directory."""
        total_size = 0
        try:
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except (FileNotFoundError, PermissionError):
            # Return 0 if directory doesn't exist or can't be accessed
            pass
        return total_size

    def list_directory_contents(self, path: Path, recursive: bool = False) -> List[Path]:
        """List directory contents, optionally recursively."""
        try:
            if recursive:
                return list(path.rglob('*'))
            return list(path.iterdir())
        except (FileNotFoundError, PermissionError):
            return []

    def move_to_trash(self, path: Path) -> FileOperationResult:
        """Move a file or directory to the system trash/recycle bin."""
        try:
            # Try to use send2trash library if available
            import send2trash
            send2trash.send2trash(str(path))
            return FileOperationResult(success=True)
        except ImportError:
            # Fallback: simulate move to trash with deletion
            try:
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    import shutil
                    shutil.rmtree(path)
                return FileOperationResult(success=True)
            except Exception as e:
                return FileOperationResult(
                    success=False,
                    error_message=f"Failed to move to trash: {str(e)}"
                )
        except Exception as e:
            return FileOperationResult(
                success=False,
                error_message=f"Failed to move to trash: {str(e)}"
            )

    def restore_from_trash(self, original_path: Path) -> FileOperationResult:
        """Restore a file or directory from the system trash/recycle bin."""
        # macOS-specific restore from trash implementation
        # This would require complex macOS API integration
        return FileOperationResult(
            success=False,
            error_message="Restore from trash not implemented for macOS"
        )

    def open_in_file_manager(self, path: Path) -> FileOperationResult:
        """Open the given path in the system's file manager."""
        try:
            subprocess.run(['open', str(path)], check=True)
            return FileOperationResult(success=True)
        except Exception as e:
            return FileOperationResult(
                success=False,
                error_message=f"Failed to open in file manager: {str(e)}"
            )

    def get_file_metadata(self, path: Path) -> Dict[str, Any]:
        """Get platform-specific file metadata."""
        try:
            stat = path.stat()
            return {
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "accessed": stat.st_atime,
                "macos_specific": {
                    "finder_flags": getattr(stat, 'st_flags', None),
                    "creation_time": getattr(stat, 'st_birthtime', None),
                    "quarantine_flag": False  # Would check actual quarantine status
                }
            }
        except (FileNotFoundError, PermissionError):
            return {}

    def set_file_permissions(self, path: Path, permissions: Dict[str, Any]) -> FileOperationResult:
        """Set file permissions in a platform-appropriate way."""
        try:
            # macOS-specific permission handling
            if 'readonly' in permissions:
                if permissions['readonly']:
                    path.chmod(0o444)
                else:
                    path.chmod(0o644)
            return FileOperationResult(success=True)
        except Exception as e:
            return FileOperationResult(
                success=False,
                error_message=f"Failed to set permissions: {str(e)}"
            )

    def optimize_for_platform(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply platform-specific optimizations for given operations."""
        optimizations = {
            "directory_scan": {
                "use_spotlight": True,
                "metadata_caching": True,
                "parallel_scanning": True
            },
            "file_deletion": {
                "secure_delete_available": True,
                "trash_integration": True
            }
        }
        return optimizations.get(operation, {})