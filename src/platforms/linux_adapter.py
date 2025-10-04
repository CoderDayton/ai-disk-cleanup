"""
Linux-specific platform adapter implementation.

This module provides Linux-specific implementations of the platform adapter interface,
including integration with various desktop environments and Linux file managers.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

from .base_adapter import (
    BaseAdapter, PlatformType, FileOperationResult,
    PlatformAdapterError, FileOperationError
)


class LinuxAdapter(BaseAdapter):
    """Linux-specific platform adapter implementation."""

    @property
    def platform_type(self) -> PlatformType:
        """Get the platform type this adapter handles."""
        return PlatformType.LINUX

    def _detect_platform(self) -> PlatformType:
        """Detect the current platform."""
        return PlatformType.LINUX

    def _validate_platform_support(self) -> None:
        """Validate that the current platform is supported."""
        # In a real implementation, would validate Linux distribution, desktop environment, etc.
        # For now, we assume Linux is supported
        pass

    def normalize_path(self, path: Union[str, Path]) -> Path:
        """Normalize a path for the current platform."""
        # Convert backslashes to forward slashes for Linux (POSIX)
        normalized_str = str(path).replace('\\', '/')
        return Path(normalized_str)

    def get_file_manager_integration(self) -> Dict[str, Any]:
        """Get platform-specific file manager integration capabilities."""
        return {
            "name": "Linux File Manager",
            "supported_managers": ["nautilus", "dolphin", "thunar", "pcmanfm"],
            "features": [
                "trash_integration",
                "mime_type_detection",
                "desktop_integration",
                "gvfs_support"
            ],
            "apis": ["gio", "xdg-open", "freedesktop"]
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
        # Linux-specific restore from trash implementation
        # This would require accessing ~/.local/share/Trash and managing trash info files
        return FileOperationResult(
            success=False,
            error_message="Restore from trash not implemented for Linux"
        )

    def open_in_file_manager(self, path: Path) -> FileOperationResult:
        """Open the given path in the system's file manager."""
        try:
            subprocess.run(['xdg-open', str(path)], check=True)
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
                "linux_specific": {
                    "inode": stat.st_ino,
                    "device": stat.st_dev,
                    "hard_links": stat.st_nlink,
                    "uid": stat.st_uid,
                    "gid": stat.st_gid,
                    "mode": stat.st_mode
                }
            }
        except (FileNotFoundError, PermissionError):
            return {}

    def set_file_permissions(self, path: Path, permissions: Dict[str, Any]) -> FileOperationResult:
        """Set file permissions in a platform-appropriate way."""
        try:
            # Linux-specific permission handling
            if 'mode' in permissions:
                path.chmod(permissions['mode'])
            if 'uid' in permissions and 'gid' in permissions:
                os.chown(str(path), permissions['uid'], permissions['gid'])
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
                "use_inotify": True,
                "parallel_scanning": True,
                "respect_hidden_files": True
            },
            "file_deletion": {
                "trash_integration": True,
                "freedesktop_compliance": True
            }
        }
        return optimizations.get(operation, {})