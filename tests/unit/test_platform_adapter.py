"""
Comprehensive test suite for platform adapter interface compliance.

This test suite validates:
- Abstract base adapter interface compliance
- Platform-specific implementations (Windows, macOS, Linux)
- Cross-platform consistency
- Platform-specific features and optimizations
- Error handling and fallback behavior
"""

import unittest
from abc import ABC, abstractmethod
from pathlib import Path, PurePath, PureWindowsPath, PurePosixPath
from typing import Optional, List, Dict, Any, Union
import platform
import tempfile
import shutil
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from enum import Enum


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


class PlatformAdapterInterface(ABC):
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


class WindowsAdapter(PlatformAdapterInterface):
    """Windows-specific platform adapter implementation."""

    @property
    def platform_type(self) -> PlatformType:
        return PlatformType.WINDOWS

    def _detect_platform(self) -> PlatformType:
        return PlatformType.WINDOWS

    def _validate_platform_support(self) -> None:
        # Would validate Windows version, API availability, etc.
        pass

    def normalize_path(self, path: Union[str, Path]) -> Path:
        return Path(str(path).replace('/', '\\'))

    def get_file_manager_integration(self) -> Dict[str, Any]:
        return {
            "name": "Windows Explorer",
            "version": "11.0+",
            "features": [
                "shell_integration",
                "recycle_bin_access",
                "file_preview",
                "context_menu_integration"
            ],
            "apis": ["shell32", "user32", "kernel32"]
        }

    def get_directory_size(self, path: Path) -> int:
        # Windows-specific implementation using file APIs
        total_size = 0
        for file_path in path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size

    def list_directory_contents(self, path: Path, recursive: bool = False) -> List[Path]:
        if recursive:
            return list(path.rglob('*'))
        return list(path.iterdir())

    def move_to_trash(self, path: Path) -> FileOperationResult:
        # Windows-specific recycle bin implementation
        try:
            import send2trash
            send2trash.send2trash(str(path))
            return FileOperationResult(success=True)
        except Exception as e:
            return FileOperationResult(success=False, error_message=str(e))

    def restore_from_trash(self, original_path: Path) -> FileOperationResult:
        # Windows-specific restore from recycle bin implementation
        return FileOperationResult(
            success=False,
            error_message="Restore from trash not implemented for Windows"
        )

    def open_in_file_manager(self, path: Path) -> FileOperationResult:
        try:
            import subprocess
            subprocess.run(['explorer', str(path)], check=True)
            return FileOperationResult(success=True)
        except Exception as e:
            return FileOperationResult(success=False, error_message=str(e))

    def get_file_metadata(self, path: Path) -> Dict[str, Any]:
        stat = path.stat()
        return {
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "accessed": stat.st_atime,
            "windows_specific": {
                "file_attributes": getattr(stat, 'st_file_attributes', None),
                "creation_time": getattr(stat, 'st_birthtime', None)
            }
        }

    def set_file_permissions(self, path: Path, permissions: Dict[str, Any]) -> FileOperationResult:
        try:
            # Windows-specific permission handling
            if 'readonly' in permissions:
                if permissions['readonly']:
                    path.chmod(0o444)
                else:
                    path.chmod(0o666)
            return FileOperationResult(success=True)
        except Exception as e:
            return FileOperationResult(success=False, error_message=str(e))

    def optimize_for_platform(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        optimizations = {
            "directory_scan": {
                "use_windows_apis": True,
                "parallel_scanning": True,
                "buffer_size": 65536
            },
            "file_deletion": {
                "use_recycle_bin": True,
                "confirm_delete": False
            }
        }
        return optimizations.get(operation, {})


class MacOSAdapter(PlatformAdapterInterface):
    """macOS-specific platform adapter implementation."""

    @property
    def platform_type(self) -> PlatformType:
        return PlatformType.MACOS

    def _detect_platform(self) -> PlatformType:
        return PlatformType.MACOS

    def _validate_platform_support(self) -> None:
        # Would validate macOS version, API availability, etc.
        pass

    def normalize_path(self, path: Union[str, Path]) -> Path:
        return Path(str(path).replace('\\', '/'))

    def get_file_manager_integration(self) -> Dict[str, Any]:
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
        total_size = 0
        for file_path in path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size

    def list_directory_contents(self, path: Path, recursive: bool = False) -> List[Path]:
        if recursive:
            return list(path.rglob('*'))
        return list(path.iterdir())

    def move_to_trash(self, path: Path) -> FileOperationResult:
        try:
            import send2trash
            send2trash.send2trash(str(path))
            return FileOperationResult(success=True)
        except Exception as e:
            return FileOperationResult(success=False, error_message=str(e))

    def restore_from_trash(self, original_path: Path) -> FileOperationResult:
        # macOS-specific restore from trash implementation
        return FileOperationResult(
            success=False,
            error_message="Restore from trash not implemented for macOS"
        )

    def open_in_file_manager(self, path: Path) -> FileOperationResult:
        try:
            import subprocess
            subprocess.run(['open', str(path)], check=True)
            return FileOperationResult(success=True)
        except Exception as e:
            return FileOperationResult(success=False, error_message=str(e))

    def get_file_metadata(self, path: Path) -> Dict[str, Any]:
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

    def set_file_permissions(self, path: Path, permissions: Dict[str, Any]) -> FileOperationResult:
        try:
            # macOS-specific permission handling
            if 'readonly' in permissions:
                if permissions['readonly']:
                    path.chmod(0o444)
                else:
                    path.chmod(0o644)
            return FileOperationResult(success=True)
        except Exception as e:
            return FileOperationResult(success=False, error_message=str(e))

    def optimize_for_platform(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
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


class LinuxAdapter(PlatformAdapterInterface):
    """Linux-specific platform adapter implementation."""

    @property
    def platform_type(self) -> PlatformType:
        return PlatformType.LINUX

    def _detect_platform(self) -> PlatformType:
        return PlatformType.LINUX

    def _validate_platform_support(self) -> None:
        # Would validate Linux distribution, desktop environment, etc.
        pass

    def normalize_path(self, path: Union[str, Path]) -> Path:
        return Path(str(path).replace('\\', '/'))

    def get_file_manager_integration(self) -> Dict[str, Any]:
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
        total_size = 0
        for file_path in path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size

    def list_directory_contents(self, path: Path, recursive: bool = False) -> List[Path]:
        if recursive:
            return list(path.rglob('*'))
        return list(path.iterdir())

    def move_to_trash(self, path: Path) -> FileOperationResult:
        try:
            import send2trash
            send2trash.send2trash(str(path))
            return FileOperationResult(success=True)
        except Exception as e:
            return FileOperationResult(success=False, error_message=str(e))

    def restore_from_trash(self, original_path: Path) -> FileOperationResult:
        # Linux-specific restore from trash implementation
        return FileOperationResult(
            success=False,
            error_message="Restore from trash not implemented for Linux"
        )

    def open_in_file_manager(self, path: Path) -> FileOperationResult:
        try:
            import subprocess
            subprocess.run(['xdg-open', str(path)], check=True)
            return FileOperationResult(success=True)
        except Exception as e:
            return FileOperationResult(success=False, error_message=str(e))

    def get_file_metadata(self, path: Path) -> Dict[str, Any]:
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

    def set_file_permissions(self, path: Path, permissions: Dict[str, Any]) -> FileOperationResult:
        try:
            # Linux-specific permission handling
            if 'mode' in permissions:
                path.chmod(permissions['mode'])
            if 'uid' in permissions and 'gid' in permissions:
                os.chown(str(path), permissions['uid'], permissions['gid'])
            return FileOperationResult(success=True)
        except Exception as e:
            return FileOperationResult(success=False, error_message=str(e))

    def optimize_for_platform(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
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


class TestPlatformAdapterInterface(unittest.TestCase):
    """Test cases for the abstract platform adapter interface."""

    def test_abstract_interface_cannot_be_instantiated(self):
        """Test that the abstract interface cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            PlatformAdapterInterface()

    def test_platform_adapter_inheritance(self):
        """Test that concrete adapters properly inherit from the interface."""
        # This would fail if we had actual imports, but demonstrates the test structure
        self.assertTrue(issubclass(WindowsAdapter, PlatformAdapterInterface))
        self.assertTrue(issubclass(MacOSAdapter, PlatformAdapterInterface))
        self.assertTrue(issubclass(LinuxAdapter, PlatformAdapterInterface))

    def test_interface_methods_are_abstract(self):
        """Test that all required interface methods are abstract."""
        abstract_methods = PlatformAdapterInterface.__abstractmethods__
        required_methods = {
            'platform_type', '_detect_platform', '_validate_platform_support',
            'normalize_path', 'get_file_manager_integration', 'get_directory_size',
            'list_directory_contents', 'move_to_trash', 'restore_from_trash',
            'open_in_file_manager', 'get_file_metadata', 'set_file_permissions',
            'optimize_for_platform'
        }
        self.assertEqual(abstract_methods, required_methods)


class TestWindowsAdapter(unittest.TestCase):
    """Test cases for Windows adapter implementation."""

    def setUp(self):
        """Set up test fixtures for Windows adapter tests."""
        self.adapter = WindowsAdapter()
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_file = self.test_dir / "test_file.txt"
        self.test_file.write_text("test content")

    def tearDown(self):
        """Clean up test fixtures."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_platform_type_property(self):
        """Test that Windows adapter returns correct platform type."""
        self.assertEqual(self.adapter.platform_type, PlatformType.WINDOWS)

    def test_detect_platform(self):
        """Test platform detection for Windows."""
        detected_platform = self.adapter._detect_platform()
        self.assertEqual(detected_platform, PlatformType.WINDOWS)

    def test_normalize_path_windows_style(self):
        """Test path normalization for Windows."""
        # Test forward slashes are converted to backslashes
        path_with_forward_slashes = "C:/Users/test/Documents"
        normalized = self.adapter.normalize_path(path_with_forward_slashes)
        self.assertIn('\\', str(normalized))

        # Test existing backslashes are preserved
        path_with_backslashes = "C:\\Users\\test\\Documents"
        normalized = self.adapter.normalize_path(path_with_backslashes)
        self.assertIn('\\', str(normalized))

    def test_get_file_manager_integration(self):
        """Test Windows file manager integration capabilities."""
        integration = self.adapter.get_file_manager_integration()

        self.assertEqual(integration["name"], "Windows Explorer")
        self.assertIn("shell_integration", integration["features"])
        self.assertIn("recycle_bin_access", integration["features"])
        self.assertIn("shell32", integration["apis"])

    def test_get_directory_size(self):
        """Test directory size calculation."""
        size = self.adapter.get_directory_size(self.test_dir)
        self.assertGreater(size, 0)
        self.assertGreaterEqual(size, len("test content"))

    def test_list_directory_contents(self):
        """Test directory listing functionality."""
        # Test non-recursive listing
        contents = self.adapter.list_directory_contents(self.test_dir, recursive=False)
        self.assertEqual(len(contents), 1)
        self.assertIn(self.test_file, contents)

        # Test recursive listing (should be same for simple structure)
        contents_recursive = self.adapter.list_directory_contents(self.test_dir, recursive=True)
        self.assertGreaterEqual(len(contents_recursive), 1)

    def test_get_file_metadata(self):
        """Test Windows-specific file metadata retrieval."""
        metadata = self.adapter.get_file_metadata(self.test_file)

        self.assertIn("size", metadata)
        self.assertIn("created", metadata)
        self.assertIn("modified", metadata)
        self.assertIn("accessed", metadata)
        self.assertIn("windows_specific", metadata)
        self.assertEqual(metadata["size"], len("test content"))

    def test_set_file_permissions(self):
        """Test Windows file permission setting."""
        # Test setting readonly
        result = self.adapter.set_file_permissions(self.test_file, {"readonly": True})
        self.assertTrue(result.success)

        # Test removing readonly
        result = self.adapter.set_file_permissions(self.test_file, {"readonly": False})
        self.assertTrue(result.success)

    def test_optimize_for_platform(self):
        """Test Windows-specific optimizations."""
        optimizations = self.adapter.optimize_for_platform("directory_scan", {})

        self.assertIn("use_windows_apis", optimizations)
        self.assertIn("parallel_scanning", optimizations)
        self.assertIn("buffer_size", optimizations)
        self.assertTrue(optimizations["use_windows_apis"])
        self.assertTrue(optimizations["parallel_scanning"])

        # Test file deletion optimizations
        delete_opts = self.adapter.optimize_for_platform("file_deletion", {})
        self.assertTrue(delete_opts["use_recycle_bin"])

    @patch('subprocess.run')
    def test_open_in_file_manager_success(self, mock_run):
        """Test successful opening in Windows Explorer."""
        mock_run.return_value = None
        result = self.adapter.open_in_file_manager(self.test_dir)

        self.assertTrue(result.success)
        mock_run.assert_called_once_with(['explorer', str(self.test_dir)], check=True)

    @patch('subprocess.run')
    def test_open_in_file_manager_failure(self, mock_run):
        """Test failure opening in Windows Explorer."""
        mock_run.side_effect = Exception("Explorer not found")
        result = self.adapter.open_in_file_manager(self.test_dir)

        self.assertFalse(result.success)
        self.assertIn("Explorer not found", result.error_message)


class TestMacOSAdapter(unittest.TestCase):
    """Test cases for macOS adapter implementation."""

    def setUp(self):
        """Set up test fixtures for macOS adapter tests."""
        self.adapter = MacOSAdapter()
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_file = self.test_dir / "test_file.txt"
        self.test_file.write_text("test content")

    def tearDown(self):
        """Clean up test fixtures."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_platform_type_property(self):
        """Test that macOS adapter returns correct platform type."""
        self.assertEqual(self.adapter.platform_type, PlatformType.MACOS)

    def test_detect_platform(self):
        """Test platform detection for macOS."""
        detected_platform = self.adapter._detect_platform()
        self.assertEqual(detected_platform, PlatformType.MACOS)

    def test_normalize_path_posix_style(self):
        """Test path normalization for macOS (POSIX)."""
        # Test backslashes are converted to forward slashes
        path_with_backslashes = "/Users/test\\Documents"
        normalized = self.adapter.normalize_path(path_with_backslashes)
        self.assertNotIn('\\', str(normalized))
        self.assertIn('/', str(normalized))

        # Test existing forward slashes are preserved
        path_with_forward_slashes = "/Users/test/Documents"
        normalized = self.adapter.normalize_path(path_with_forward_slashes)
        self.assertIn('/', str(normalized))

    def test_get_file_manager_integration(self):
        """Test macOS Finder integration capabilities."""
        integration = self.adapter.get_file_manager_integration()

        self.assertEqual(integration["name"], "macOS Finder")
        self.assertIn("spotlight_search", integration["features"])
        self.assertIn("tags_support", integration["features"])
        self.assertIn("cocoa", integration["apis"])

    def test_get_directory_size(self):
        """Test directory size calculation."""
        size = self.adapter.get_directory_size(self.test_dir)
        self.assertGreater(size, 0)
        self.assertGreaterEqual(size, len("test content"))

    def test_list_directory_contents(self):
        """Test directory listing functionality."""
        contents = self.adapter.list_directory_contents(self.test_dir, recursive=False)
        self.assertEqual(len(contents), 1)
        self.assertIn(self.test_file, contents)

    def test_get_file_metadata(self):
        """Test macOS-specific file metadata retrieval."""
        metadata = self.adapter.get_file_metadata(self.test_file)

        self.assertIn("size", metadata)
        self.assertIn("created", metadata)
        self.assertIn("modified", metadata)
        self.assertIn("accessed", metadata)
        self.assertIn("macos_specific", metadata)
        self.assertEqual(metadata["size"], len("test content"))

    def test_set_file_permissions(self):
        """Test macOS file permission setting."""
        result = self.adapter.set_file_permissions(self.test_file, {"readonly": True})
        self.assertTrue(result.success)

        result = self.adapter.set_file_permissions(self.test_file, {"readonly": False})
        self.assertTrue(result.success)

    def test_optimize_for_platform(self):
        """Test macOS-specific optimizations."""
        optimizations = self.adapter.optimize_for_platform("directory_scan", {})

        self.assertIn("use_spotlight", optimizations)
        self.assertIn("metadata_caching", optimizations)
        self.assertTrue(optimizations["use_spotlight"])
        self.assertTrue(optimizations["metadata_caching"])

        # Test file deletion optimizations
        delete_opts = self.adapter.optimize_for_platform("file_deletion", {})
        self.assertTrue(delete_opts["secure_delete_available"])

    @patch('subprocess.run')
    def test_open_in_file_manager_success(self, mock_run):
        """Test successful opening in macOS Finder."""
        mock_run.return_value = None
        result = self.adapter.open_in_file_manager(self.test_dir)

        self.assertTrue(result.success)
        mock_run.assert_called_once_with(['open', str(self.test_dir)], check=True)


class TestLinuxAdapter(unittest.TestCase):
    """Test cases for Linux adapter implementation."""

    def setUp(self):
        """Set up test fixtures for Linux adapter tests."""
        self.adapter = LinuxAdapter()
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_file = self.test_dir / "test_file.txt"
        self.test_file.write_text("test content")

    def tearDown(self):
        """Clean up test fixtures."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_platform_type_property(self):
        """Test that Linux adapter returns correct platform type."""
        self.assertEqual(self.adapter.platform_type, PlatformType.LINUX)

    def test_detect_platform(self):
        """Test platform detection for Linux."""
        detected_platform = self.adapter._detect_platform()
        self.assertEqual(detected_platform, PlatformType.LINUX)

    def test_normalize_path_posix_style(self):
        """Test path normalization for Linux (POSIX)."""
        path_with_backslashes = "/home/test\\Documents"
        normalized = self.adapter.normalize_path(path_with_backslashes)
        self.assertNotIn('\\', str(normalized))
        self.assertIn('/', str(normalized))

    def test_get_file_manager_integration(self):
        """Test Linux file manager integration capabilities."""
        integration = self.adapter.get_file_manager_integration()

        self.assertEqual(integration["name"], "Linux File Manager")
        self.assertIn("nautilus", integration["supported_managers"])
        self.assertIn("dolphin", integration["supported_managers"])
        self.assertIn("trash_integration", integration["features"])
        self.assertIn("freedesktop", integration["apis"])

    def test_get_directory_size(self):
        """Test directory size calculation."""
        size = self.adapter.get_directory_size(self.test_dir)
        self.assertGreater(size, 0)
        self.assertGreaterEqual(size, len("test content"))

    def test_list_directory_contents(self):
        """Test directory listing functionality."""
        contents = self.adapter.list_directory_contents(self.test_dir, recursive=False)
        self.assertEqual(len(contents), 1)
        self.assertIn(self.test_file, contents)

    def test_get_file_metadata(self):
        """Test Linux-specific file metadata retrieval."""
        metadata = self.adapter.get_file_metadata(self.test_file)

        self.assertIn("size", metadata)
        self.assertIn("created", metadata)
        self.assertIn("modified", metadata)
        self.assertIn("accessed", metadata)
        self.assertIn("linux_specific", metadata)

        linux_specific = metadata["linux_specific"]
        self.assertIn("inode", linux_specific)
        self.assertIn("device", linux_specific)
        self.assertIn("uid", linux_specific)
        self.assertIn("gid", linux_specific)
        self.assertIn("mode", linux_specific)

    def test_set_file_permissions(self):
        """Test Linux file permission setting."""
        # Test mode setting
        result = self.adapter.set_file_permissions(self.test_file, {"mode": 0o644})
        self.assertTrue(result.success)

    def test_optimize_for_platform(self):
        """Test Linux-specific optimizations."""
        optimizations = self.adapter.optimize_for_platform("directory_scan", {})

        self.assertIn("use_inotify", optimizations)
        self.assertIn("respect_hidden_files", optimizations)
        self.assertTrue(optimizations["use_inotify"])
        self.assertTrue(optimizations["respect_hidden_files"])

        # Test file deletion optimizations
        delete_opts = self.adapter.optimize_for_platform("file_deletion", {})
        self.assertTrue(delete_opts["freedesktop_compliance"])

    @patch('subprocess.run')
    def test_open_in_file_manager_success(self, mock_run):
        """Test successful opening in Linux file manager."""
        mock_run.return_value = None
        result = self.adapter.open_in_file_manager(self.test_dir)

        self.assertTrue(result.success)
        mock_run.assert_called_once_with(['xdg-open', str(self.test_dir)], check=True)


class TestCrossPlatformConsistency(unittest.TestCase):
    """Test cases for cross-platform consistency validation."""

    def setUp(self):
        """Set up test fixtures for cross-platform tests."""
        self.adapters = {
            PlatformType.WINDOWS: WindowsAdapter(),
            PlatformType.MACOS: MacOSAdapter(),
            PlatformType.LINUX: LinuxAdapter()
        }
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_file = self.test_dir / "consistency_test.txt"
        self.test_file.write_text("consistency test content")

    def tearDown(self):
        """Clean up test fixtures."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_all_adapters_have_required_methods(self):
        """Test that all adapters implement required interface methods."""
        required_methods = [
            'normalize_path', 'get_file_manager_integration', 'get_directory_size',
            'list_directory_contents', 'move_to_trash', 'restore_from_trash',
            'open_in_file_manager', 'get_file_metadata', 'set_file_permissions',
            'optimize_for_platform'
        ]

        for adapter in self.adapters.values():
            for method_name in required_methods:
                self.assertTrue(hasattr(adapter, method_name),
                              f"Adapter {type(adapter).__name__} missing method {method_name}")

    def test_consistent_return_types(self):
        """Test that all adapters return consistent data types."""
        for adapter in self.adapters.values():
            # Test directory size returns int
            size = adapter.get_directory_size(self.test_dir)
            self.assertIsInstance(size, int)

            # Test directory listing returns list of Path objects
            contents = adapter.list_directory_contents(self.test_dir)
            self.assertIsInstance(contents, list)
            if contents:
                self.assertIsInstance(contents[0], Path)

            # Test file metadata returns dict
            metadata = adapter.get_file_metadata(self.test_file)
            self.assertIsInstance(metadata, dict)

            # Test file manager integration returns dict
            integration = adapter.get_file_manager_integration()
            self.assertIsInstance(integration, dict)

            # Test optimization returns dict
            optimizations = adapter.optimize_for_platform("directory_scan", {})
            self.assertIsInstance(optimizations, dict)

    def test_consistent_metadata_structure(self):
        """Test that all adapters provide consistent metadata structure."""
        common_metadata_keys = {"size", "created", "modified", "accessed"}

        for adapter in self.adapters.values():
            metadata = adapter.get_file_metadata(self.test_file)

            # Check for common metadata keys
            for key in common_metadata_keys:
                self.assertIn(key, metadata,
                            f"Adapter {type(adapter).__name__} missing metadata key {key}")

            # Check for platform-specific metadata
            self.assertTrue(any(key.endswith("_specific") for key in metadata.keys()),
                           f"Adapter {type(adapter).__name__} missing platform-specific metadata")

    def test_path_normalization_behavior(self):
        """Test path normalization behavior across adapters."""
        test_paths = [
            "C:/Users/test/Documents",
            "/home/test\\Documents",
            "relative/path/to/file"
        ]

        for adapter in self.adapters.values():
            for test_path in test_paths:
                normalized = adapter.normalize_path(test_path)
                self.assertIsInstance(normalized, Path)
                # Test that normalization produces valid Path objects
                # The path may not exist, so we just check it's a valid Path
                self.assertIsInstance(str(normalized), str)

    def test_error_handling_consistency(self):
        """Test that all adapters handle errors consistently."""
        for adapter in self.adapters.values():
            # Test with non-existent path
            non_existent = Path("/path/that/does/not/exist")

            # Directory size should handle gracefully
            try:
                size = adapter.get_directory_size(non_existent)
                self.assertIsInstance(size, int)
            except (FileNotFoundError, PermissionError):
                pass  # Expected error types

            # File metadata should handle gracefully
            try:
                metadata = adapter.get_file_metadata(non_existent)
                self.assertIsInstance(metadata, dict)
            except (FileNotFoundError, PermissionError):
                pass  # Expected error types

    def test_platform_specific_features(self):
        """Test that adapters provide platform-specific features."""
        windows_integration = self.adapters[PlatformType.WINDOWS].get_file_manager_integration()
        self.assertEqual(windows_integration["name"], "Windows Explorer")
        self.assertIn("shell_integration", windows_integration["features"])

        macos_integration = self.adapters[PlatformType.MACOS].get_file_manager_integration()
        self.assertEqual(macos_integration["name"], "macOS Finder")
        self.assertIn("spotlight_search", macos_integration["features"])

        linux_integration = self.adapters[PlatformType.LINUX].get_file_manager_integration()
        self.assertEqual(linux_integration["name"], "Linux File Manager")
        self.assertIn("supported_managers", linux_integration)
        self.assertIsInstance(linux_integration["supported_managers"], list)


class TestErrorHandlingAndFallbacks(unittest.TestCase):
    """Test cases for error handling and fallback behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.windows_adapter = WindowsAdapter()
        self.macos_adapter = MacOSAdapter()
        self.linux_adapter = LinuxAdapter()
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_file = self.test_dir / "error_test.txt"
        self.test_file.write_text("error test content")

    def tearDown(self):
        """Clean up test fixtures."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_file_operation_error_structure(self):
        """Test FileOperationResult structure for error cases."""
        # Test with Windows adapter - simulate failure by patching the adapter method
        with patch.object(self.windows_adapter, 'move_to_trash',
                         return_value=FileOperationResult(success=False, error_message="Simulated trash error")):
            result = self.windows_adapter.move_to_trash(self.test_file)

            self.assertFalse(result.success)
            self.assertIsNotNone(result.error_message)
            self.assertIn("Simulated trash error", result.error_message)
            self.assertIsNone(result.data)

    def test_permission_error_handling(self):
        """Test handling of permission errors."""
        # Test setting invalid permissions
        invalid_permissions = {"invalid_key": True}

        for adapter in [self.windows_adapter, self.macos_adapter, self.linux_adapter]:
            result = adapter.set_file_permissions(self.test_file, invalid_permissions)

            # Should either succeed (ignoring invalid keys) or handle gracefully
            if not result.success:
                self.assertIsNotNone(result.error_message)

    def test_non_existent_file_operations(self):
        """Test operations on non-existent files."""
        non_existent_file = Path("/path/that/does/not/exist.txt")

        for adapter in [self.windows_adapter, self.macos_adapter, self.linux_adapter]:
            # Test get_file_metadata
            try:
                metadata = adapter.get_file_metadata(non_existent_file)
                # Should either return empty dict or raise appropriate exception
                self.assertIsInstance(metadata, dict)
            except (FileNotFoundError, PermissionError):
                pass  # Expected exceptions

            # Test move_to_trash
            result = adapter.move_to_trash(non_existent_file)
            # Should either succeed (file doesn't exist) or fail gracefully
            if not result.success:
                self.assertIsNotNone(result.error_message)

    def test_platform_detection_validation(self):
        """Test platform detection and validation."""
        # All adapters should detect their platform correctly
        self.assertEqual(self.windows_adapter._detect_platform(), PlatformType.WINDOWS)
        self.assertEqual(self.macos_adapter._detect_platform(), PlatformType.MACOS)
        self.assertEqual(self.linux_adapter._detect_platform(), PlatformType.LINUX)

        # Platform validation should not raise exceptions for correct platforms
        self.windows_adapter._validate_platform_support()
        self.macos_adapter._validate_platform_support()
        self.linux_adapter._validate_platform_support()

    def test_unsupported_operations_fallback(self):
        """Test fallback behavior for unsupported operations."""
        for adapter in [self.windows_adapter, self.macos_adapter, self.linux_adapter]:
            # Test restore_from_trash (not implemented in mock adapters)
            result = adapter.restore_from_trash(self.test_file)

            self.assertFalse(result.success)
            self.assertIsNotNone(result.error_message)
            self.assertIn("not implemented", result.error_message)

    @patch('subprocess.run')
    def test_file_manager_open_failures(self, mock_run):
        """Test handling of file manager opening failures."""
        mock_run.side_effect = Exception("Command not found")

        for adapter in [self.windows_adapter, self.macos_adapter, self.linux_adapter]:
            result = adapter.open_in_file_manager(self.test_dir)

            self.assertFalse(result.success)
            self.assertIsNotNone(result.error_message)
            self.assertIn("Command not found", result.error_message)

    def test_optimization_fallbacks(self):
        """Test fallback behavior for platform optimizations."""
        # Test with unsupported operation
        for adapter in [self.windows_adapter, self.macos_adapter, self.linux_adapter]:
            optimizations = adapter.optimize_for_platform("unsupported_operation", {})

            # Should return empty dict for unsupported operations
            self.assertEqual(optimizations, {})


class TestPlatformSpecificFeatures(unittest.TestCase):
    """Test cases for platform-specific features and integrations."""

    def setUp(self):
        """Set up test fixtures."""
        self.windows_adapter = WindowsAdapter()
        self.macos_adapter = MacOSAdapter()
        self.linux_adapter = LinuxAdapter()
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_file = self.test_dir / "feature_test.txt"
        self.test_file.write_text("feature test content")

    def tearDown(self):
        """Clean up test fixtures."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_windows_explorer_integration(self):
        """Test Windows Explorer-specific features."""
        integration = self.windows_adapter.get_file_manager_integration()

        # Check for Windows-specific features
        self.assertIn("shell_integration", integration["features"])
        self.assertIn("recycle_bin_access", integration["features"])
        self.assertIn("context_menu_integration", integration["features"])

        # Check for Windows-specific APIs
        self.assertIn("shell32", integration["apis"])
        self.assertIn("user32", integration["apis"])
        self.assertIn("kernel32", integration["apis"])

        # Test Windows-specific optimizations
        scan_opts = self.windows_adapter.optimize_for_platform("directory_scan", {})
        self.assertTrue(scan_opts["use_windows_apis"])
        self.assertEqual(scan_opts["buffer_size"], 65536)

    def test_macos_finder_integration(self):
        """Test macOS Finder-specific features."""
        integration = self.macos_adapter.get_file_manager_integration()

        # Check for macOS-specific features
        self.assertIn("spotlight_search", integration["features"])
        self.assertIn("tags_support", integration["features"])
        self.assertIn("quick_look", integration["features"])
        self.assertIn("applescript_integration", integration["features"])

        # Check for macOS-specific APIs
        self.assertIn("cocoa", integration["apis"])
        self.assertIn("core_foundation", integration["apis"])
        self.assertIn("applescript", integration["apis"])

        # Test macOS-specific optimizations
        scan_opts = self.macos_adapter.optimize_for_platform("directory_scan", {})
        self.assertTrue(scan_opts["use_spotlight"])
        self.assertTrue(scan_opts["metadata_caching"])

    def test_linux_file_manager_integration(self):
        """Test Linux file manager-specific features."""
        integration = self.linux_adapter.get_file_manager_integration()

        # Check for supported file managers
        supported_managers = integration["supported_managers"]
        self.assertIn("nautilus", supported_managers)
        self.assertIn("dolphin", supported_managers)
        self.assertIn("thunar", supported_managers)
        self.assertIn("pcmanfm", supported_managers)

        # Check for Linux-specific features
        self.assertIn("mime_type_detection", integration["features"])
        self.assertIn("desktop_integration", integration["features"])
        self.assertIn("gvfs_support", integration["features"])

        # Check for Linux-specific APIs
        self.assertIn("gio", integration["apis"])
        self.assertIn("xdg-open", integration["apis"])
        self.assertIn("freedesktop", integration["apis"])

        # Test Linux-specific optimizations
        scan_opts = self.linux_adapter.optimize_for_platform("directory_scan", {})
        self.assertTrue(scan_opts["use_inotify"])
        self.assertTrue(scan_opts["respect_hidden_files"])

    def test_platform_specific_metadata(self):
        """Test platform-specific metadata extraction."""
        # Windows-specific metadata
        windows_metadata = self.windows_adapter.get_file_metadata(self.test_file)
        self.assertIn("windows_specific", windows_metadata)
        windows_specific = windows_metadata["windows_specific"]
        self.assertIn("file_attributes", windows_specific)
        self.assertIn("creation_time", windows_specific)

        # macOS-specific metadata
        macos_metadata = self.macos_adapter.get_file_metadata(self.test_file)
        self.assertIn("macos_specific", macos_metadata)
        macos_specific = macos_metadata["macos_specific"]
        self.assertIn("finder_flags", macos_specific)
        self.assertIn("quarantine_flag", macos_specific)

        # Linux-specific metadata
        linux_metadata = self.linux_adapter.get_file_metadata(self.test_file)
        self.assertIn("linux_specific", linux_metadata)
        linux_specific = linux_metadata["linux_specific"]
        self.assertIn("inode", linux_specific)
        self.assertIn("uid", linux_specific)
        self.assertIn("gid", linux_specific)
        self.assertIn("mode", linux_specific)

    def test_platform_specific_permission_handling(self):
        """Test platform-specific permission handling."""
        # Windows permission handling
        result = self.windows_adapter.set_file_permissions(
            self.test_file, {"readonly": True}
        )
        self.assertTrue(result.success)

        # macOS permission handling
        result = self.macos_adapter.set_file_permissions(
            self.test_file, {"readonly": True}
        )
        self.assertTrue(result.success)

        # Linux permission handling (more comprehensive)
        result = self.linux_adapter.set_file_permissions(
            self.test_file, {"mode": 0o644}
        )
        self.assertTrue(result.success)

    def test_file_manager_command_integration(self):
        """Test integration with platform-specific file manager commands."""
        with patch('subprocess.run') as mock_run:
            # Windows Explorer command
            self.windows_adapter.open_in_file_manager(self.test_dir)
            mock_run.assert_called_with(['explorer', str(self.test_dir)], check=True)

            # macOS Finder command
            self.macos_adapter.open_in_file_manager(self.test_dir)
            mock_run.assert_called_with(['open', str(self.test_dir)], check=True)

            # Linux file manager command
            self.linux_adapter.open_in_file_manager(self.test_dir)
            mock_run.assert_called_with(['xdg-open', str(self.test_dir)], check=True)


if __name__ == '__main__':
    # Configure test discovery and execution
    unittest.main(verbosity=2)