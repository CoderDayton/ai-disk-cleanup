"""
File Scanner Component for AI Disk Cleanup.

Provides privacy-first file metadata extraction without accessing file contents.
Implements platform-agnostic file scanning with cross-platform compatibility.
"""

import os
import pathlib
import stat
import time
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Set, Union
from datetime import datetime
import logging

from .path_security import PathSecurityValidator, PathValidationError
from .security.input_sanitizer import get_sanitizer


@dataclass
class FileMetadata:
    """Immutable file metadata container."""

    name: str
    extension: str
    size_bytes: int
    modified_date: datetime
    directory_path: str
    file_type: str
    full_path: str
    is_readable: bool
    is_writable: bool
    is_hidden: bool

    @classmethod
    def from_path(cls, file_path: Union[str, pathlib.Path]) -> "FileMetadata":
        """Create FileMetadata from a file path."""
        path = pathlib.Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        try:
            stat_info = path.stat()
            size = stat_info.st_size
            modified_timestamp = stat_info.st_mtime
            modified_date = datetime.fromtimestamp(modified_timestamp)

            # Extract extension without the dot and normalize to lowercase
            extension = path.suffix[1:].lower() if path.suffix else ""

            # Determine file type based on extension
            file_type = cls._determine_file_type(extension)

            # Check permissions
            is_readable = os.access(path, os.R_OK)
            is_writable = os.access(path, os.W_OK)

            # Check if hidden (platform-specific)
            is_hidden = cls._is_hidden(path)

            return cls(
                name=path.name,
                extension=extension,
                size_bytes=size,
                modified_date=modified_date,
                directory_path=str(path.parent),
                file_type=file_type,
                full_path=str(path.absolute()),
                is_readable=is_readable,
                is_writable=is_writable,
                is_hidden=is_hidden
            )
        except (OSError, PermissionError) as e:
            raise PermissionError(f"Cannot access file metadata: {file_path}") from e

    @staticmethod
    def _determine_file_type(extension: str) -> str:
        """Determine file type based on extension."""
        extension_lower = extension.lower()

        # Document types
        document_extensions = {
            "pdf", "doc", "docx", "txt", "rtf", "odt", "pages", "tex",
            "xls", "xlsx", "csv", "ods", "numbers", "ppt", "pptx", "odp", "key"
        }

        # Image types
        image_extensions = {
            "jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "svg",
            "webp", "ico", "psd", "raw", "heic", "heif"
        }

        # Video types
        video_extensions = {
            "mp4", "avi", "mov", "wmv", "flv", "mkv", "webm", "m4v",
            "3gp", "ogv", "mpg", "mpeg", "m2v"
        }

        # Audio types
        audio_extensions = {
            "mp3", "wav", "flac", "aac", "ogg", "wma", "m4a", "opus",
            "aiff", "au", "ra", "amr"
        }

        # Archive types
        archive_extensions = {
            "zip", "rar", "7z", "tar", "gz", "bz2", "xz", "z", "lzma",
            "tar.gz", "tgz", "tar.bz2", "tar.xz"
        }

        # Code types
        code_extensions = {
            "py", "js", "html", "css", "java", "cpp", "c", "h", "hpp",
            "cs", "php", "rb", "go", "rs", "swift", "kt", "scala", "r",
            "sql", "sh", "bat", "ps1", "xml", "json", "yaml", "yml"
        }

        # Executable types
        executable_extensions = {
            "exe", "msi", "dmg", "pkg", "deb", "rpm", "appimage", "run",
            "bin", "command", "app"
        }

        if extension_lower in document_extensions:
            return "document"
        elif extension_lower in image_extensions:
            return "image"
        elif extension_lower in video_extensions:
            return "video"
        elif extension_lower in audio_extensions:
            return "audio"
        elif extension_lower in archive_extensions:
            return "archive"
        elif extension_lower in code_extensions:
            return "code"
        elif extension_lower in executable_extensions:
            return "executable"
        elif extension_lower == "":
            return "no_extension"
        else:
            return "unknown"

    @staticmethod
    def _is_hidden(path: pathlib.Path) -> bool:
        """Check if file is hidden (platform-specific)."""
        if os.name == 'nt':  # Windows
            try:
                import win32api
                import win32con
                attribute = win32api.GetFileAttributes(str(path))
                return attribute & (win32con.FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_SYSTEM)
            except ImportError:
                # Fallback for Windows without win32api
                return path.name.startswith('.')
            except (OSError, AttributeError):
                return False
        else:  # Unix-like systems
            return path.name.startswith('.')


class FileScanner:
    """
    High-performance file scanner for metadata extraction.

    Scans directories recursively and extracts file metadata without accessing
    file contents, ensuring privacy and performance.
    """

    def __init__(self,
                 include_hidden: bool = False,
                 follow_symlinks: bool = False,
                 max_file_size: Optional[int] = None,
                 allowed_base_paths: Optional[List[Union[str, pathlib.Path]]] = None):
        """
        Initialize FileScanner.

        Args:
            include_hidden: Whether to include hidden files in scan results
            follow_symlinks: Whether to follow symbolic links
            max_file_size: Maximum file size to include in bytes (None for no limit)
            allowed_base_paths: List of base paths that are explicitly allowed for scanning
        """
        self.include_hidden = include_hidden
        self.follow_symlinks = follow_symlinks
        self.max_file_size = max_file_size
        self._scanned_extensions: Set[str] = set()
        self._scanned_directories: int = 0
        self._scanned_files: int = 0
        self._errors: List[str] = []

        # Initialize path security validator
        self.path_validator = PathSecurityValidator()
        self.logger = logging.getLogger(__name__)

        # Set up allowed base paths
        if allowed_base_paths:
            for base_path in allowed_base_paths:
                self.path_validator.add_allowed_base_path(base_path)

    def scan_directory(self,
                      directory_path: Union[str, pathlib.Path],
                      recursive: bool = True,
                      file_filter: Optional[Set[str]] = None) -> List[FileMetadata]:
        """
        Scan a directory and return metadata for all files.

        Args:
            directory_path: Path to directory to scan
            recursive: Whether to scan subdirectories
            file_filter: Set of file extensions to include (without dots)

        Returns:
            List of FileMetadata objects

        Raises:
            ValueError: If directory_path is not a valid directory
            PermissionError: If directory cannot be accessed
            PathValidationError: If path is potentially dangerous
        """
        self._reset_counters()

        # Validate directory path for security
        try:
            validated_path = self.path_validator.validate_directory_path(directory_path)
            self.logger.info(f"Validated directory path: {validated_path}")
        except PathValidationError as e:
            self.logger.error(f"Directory path validation failed: {e}")
            raise ValueError(f"Invalid directory path: {e}") from e

        path = pathlib.Path(validated_path)

        if not path.exists():
            raise ValueError(f"Directory does not exist: {validated_path}")

        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {validated_path}")

        try:
            files = []
            for file_metadata in self._scan_directory_generator(path, recursive, file_filter):
                files.append(file_metadata)

            return files
        except (OSError, PermissionError) as e:
            raise PermissionError(f"Cannot scan directory: {validated_path}") from e

    def scan_directory_generator(self,
                                directory_path: Union[str, pathlib.Path],
                                recursive: bool = True,
                                file_filter: Optional[Set[str]] = None) -> Iterator[FileMetadata]:
        """
        Scan a directory and yield file metadata objects.

        Generator version that yields results as they are found.
        More memory efficient for large directories.

        Args:
            directory_path: Path to directory to scan
            recursive: Whether to scan subdirectories
            file_filter: Set of file extensions to include (without dots)

        Yields:
            FileMetadata objects

        Raises:
            ValueError: If directory_path is not a valid directory
            PermissionError: If directory cannot be accessed
            PathValidationError: If path is potentially dangerous
        """
        self._reset_counters()

        # Validate directory path for security
        try:
            validated_path = self.path_validator.validate_directory_path(directory_path)
            self.logger.info(f"Validated directory path: {validated_path}")
        except PathValidationError as e:
            self.logger.error(f"Directory path validation failed: {e}")
            raise ValueError(f"Invalid directory path: {e}") from e

        path = pathlib.Path(validated_path)

        if not path.exists():
            raise ValueError(f"Directory does not exist: {validated_path}")

        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {validated_path}")

        try:
            yield from self._scan_directory_generator(path, recursive, file_filter)
        except (OSError, PermissionError) as e:
            raise PermissionError(f"Cannot scan directory: {validated_path}") from e

    def _scan_directory_generator(self,
                                 path: pathlib.Path,
                                 recursive: bool,
                                 file_filter: Optional[Set[str]]) -> Iterator[FileMetadata]:
        """Internal generator method for scanning directories."""
        try:
            self._scanned_directories += 1

            for entry in path.iterdir():
                try:
                    if entry.is_file():
                        # Skip hidden files if not included
                        if not self.include_hidden and FileMetadata._is_hidden(entry):
                            continue

                        # Apply file filter if specified
                        if file_filter is not None:
                            extension = entry.suffix[1:].lower() if entry.suffix else ""
                            if extension not in file_filter:
                                continue

                        # Handle symbolic links with security validation
                        if entry.is_symlink():
                            if not self.follow_symlinks:
                                continue

                            # Validate symlink security
                            try:
                                symlink_path, target_path = self.path_validator.validate_symlink(entry)
                                self.logger.debug(f"Validated symlink: {symlink_path} -> {target_path}")
                            except PathValidationError as e:
                                self._errors.append(f"Symlink security validation failed for {entry}: {str(e)}")
                                continue
                            except Exception as e:
                                self._errors.append(f"Error validating symlink {entry}: {str(e)}")
                                continue

                        # Check file size limit
                        if self.max_file_size is not None:
                            try:
                                stat_info = entry.stat()
                                if stat_info.st_size > self.max_file_size:
                                    continue
                            except (OSError, PermissionError):
                                continue

                        # Extract metadata
                        try:
                            metadata = FileMetadata.from_path(entry)
                            self._scanned_files += 1

                            if metadata.extension:
                                self._scanned_extensions.add(metadata.extension.lower())

                            yield metadata
                        except (OSError, PermissionError, FileNotFoundError, ValueError) as e:
                            self._errors.append(f"Error processing {entry}: {str(e)}")
                            continue

                    elif entry.is_dir() and recursive:
                        # Skip hidden directories if not included
                        if not self.include_hidden and FileMetadata._is_hidden(entry):
                            continue

                        # Validate directory path for security (in case of symlinks)
                        try:
                            validated_dir_path = self.path_validator.validate_directory_path(entry)
                        except PathValidationError as e:
                            self._errors.append(f"Directory path validation failed for {entry}: {str(e)}")
                            continue
                        except Exception as e:
                            self._errors.append(f"Error validating directory {entry}: {str(e)}")
                            continue

                        # Recursively scan subdirectories
                        yield from self._scan_directory_generator(pathlib.Path(validated_dir_path), recursive, file_filter)

                except (OSError, PermissionError):
                    # Skip entries that cannot be accessed
                    continue

        except (OSError, PermissionError):
            # Skip directories that cannot be accessed
            pass

    def get_scan_statistics(self) -> Dict[str, Union[int, Set[str]]]:
        """
        Get statistics from the last scan operation.

        Returns:
            Dictionary with scan statistics
        """
        return {
            "scanned_directories": self._scanned_directories,
            "scanned_files": self._scanned_files,
            "unique_extensions": self._scanned_extensions.copy(),
            "error_count": len(self._errors),
            "errors": self._errors.copy()
        }

    def _reset_counters(self) -> None:
        """Reset internal counters for a new scan operation."""
        self._scanned_extensions = set()
        self._scanned_directories = 0
        self._scanned_files = 0
        self._errors = []

    def add_allowed_base_path(self, path: Union[str, pathlib.Path]) -> None:
        """
        Add a base path that is explicitly allowed for scanning.

        Args:
            path: The base path to allow
        """
        try:
            self.path_validator.add_allowed_base_path(path)
            self.logger.info(f"Added allowed base path: {path}")
        except PathValidationError as e:
            self.logger.error(f"Failed to add allowed base path {path}: {e}")
            raise ValueError(f"Invalid base path: {e}") from e

    def remove_allowed_base_path(self, path: Union[str, pathlib.Path]) -> None:
        """
        Remove an allowed base path.

        Args:
            path: The base path to remove
        """
        self.path_validator.remove_allowed_base_path(path)
        self.logger.info(f"Removed allowed base path: {path}")

    def get_allowed_base_paths(self) -> List[str]:
        """Get list of allowed base paths."""
        return self.path_validator.get_allowed_base_paths()

    def clear_allowed_base_paths(self) -> None:
        """Clear all allowed base paths."""
        self.path_validator.clear_allowed_base_paths()
        self.logger.info("Cleared all allowed base paths")

    def is_path_safe_to_scan(self, path: Union[str, pathlib.Path]) -> bool:
        """
        Check if a path is safe to scan.

        Args:
            path: Path to check

        Returns:
            True if safe to scan, False otherwise
        """
        return self.path_validator.is_safe_to_scan(path)

    def is_path_safe_to_access(self, path: Union[str, pathlib.Path]) -> bool:
        """
        Check if a file path is safe to access.

        Args:
            path: Path to check

        Returns:
            True if safe to access, False otherwise
        """
        return self.path_validator.is_safe_to_access(path)