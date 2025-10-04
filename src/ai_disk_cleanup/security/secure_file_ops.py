"""
Secure File Operations Module - Provides secure file handling with proper permissions,
atomic operations, and temporary file management to prevent information disclosure.

This module addresses the following security vulnerabilities:
- MEDIUM (CVSS 6.5): Insecure temporary file creation
- MEDIUM: Temporary file information disclosure
"""

import os
import json
import hashlib
import tempfile
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Union, Iterator, BinaryIO, TextIO
import logging
import stat


class SecurityLevel(Enum):
    """Security levels for file operations."""
    PUBLIC = 0o644      # Read/write by owner, read by others
    SENSITIVE = 0o600   # Read/write by owner only
    CRITICAL = 0o400    # Read-only by owner


class FileOperationError(Exception):
    """Raised when secure file operations fail."""
    pass


class FileIntegrityError(Exception):
    """Raised when file integrity validation fails."""
    pass


class SecureFileOperations:
    """
    Provides secure file operations with atomic writes, proper permissions,
    and temporary file management to prevent information disclosure.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize secure file operations.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self._active_temp_files: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._cleanup_interval = timedelta(hours=1)
        self._last_cleanup = datetime.now()

        # Platform-specific settings
        self._is_windows = os.name == 'nt'
        self._has_chmod = hasattr(os, 'chmod')

    @contextmanager
    def secure_open(
        self,
        file_path: Union[str, Path],
        mode: str = 'r',
        security_level: SecurityLevel = SecurityLevel.PUBLIC,
        encoding: str = 'utf-8',
        create_directories: bool = True
    ) -> Iterator[Union[TextIO, BinaryIO]]:
        """
        Securely open a file with proper permissions and atomic operations.

        Args:
            file_path: Path to the file
            mode: File mode ('r', 'w', 'a', 'rb', 'wb', 'ab')
            security_level: Security level for file permissions
            encoding: Text encoding (for text modes)
            create_directories: Create parent directories if they don't exist

        Yields:
            File handle

        Raises:
            FileOperationError: If file operation fails
        """
        file_path = Path(file_path)

        # Validate path for security
        self._validate_file_path(file_path)

        temp_path = None
        file_handle = None

        try:
            # Create parent directories if needed
            if create_directories and ('w' in mode or 'a' in mode):
                file_path.parent.mkdir(parents=True, exist_ok=True)
                self._secure_directory(file_path.parent)

            # Handle write operations with temporary files for atomicity
            if 'w' in mode:
                temp_path = self._create_temp_file(file_path.parent, prefix=f"tmp_{file_path.name}")
                actual_path = temp_path
            else:
                actual_path = file_path

            # Determine binary mode
            binary_mode = 'b' in mode
            open_mode = mode.replace('b', '')

            # Open the file
            if binary_mode:
                file_handle = open(actual_path, mode, encoding=None)
            else:
                file_handle = open(actual_path, mode, encoding=encoding)

            # Set secure permissions for new files
            if 'w' in mode and not self._is_windows and self._has_chmod:
                try:
                    os.chmod(actual_path, security_level.value)
                except OSError as e:
                    self.logger.warning(f"Failed to set permissions on {actual_path}: {e}")

            yield file_handle

            # If we used a temporary file, atomically move it to the final location
            if temp_path is not None:
                file_handle.close()
                file_handle = None
                self._atomic_move(temp_path, file_path)
                # Ensure final file has correct permissions
                if not self._is_windows and self._has_chmod:
                    try:
                        os.chmod(file_path, security_level.value)
                    except OSError as e:
                        self.logger.warning(f"Failed to set final permissions on {file_path}: {e}")

        except Exception as e:
            # Clean up temporary file on error
            if temp_path is not None and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise FileOperationError(f"Secure file operation failed for {file_path}: {e}")
        finally:
            if file_handle is not None:
                file_handle.close()

    def write_json_secure(
        self,
        file_path: Union[str, Path],
        data: Dict[str, Any],
        security_level: SecurityLevel = SecurityLevel.SENSITIVE,
        indent: Optional[int] = 2,
        redact_sensitive_fields: bool = True
    ) -> None:
        """
        Securely write JSON data with atomic operations and sensitive data redaction.

        Args:
            file_path: Path to write the JSON file
            data: Data to write
            security_level: Security level for file permissions
            indent: JSON indentation
            redact_sensitive_fields: Whether to redact sensitive fields

        Raises:
            FileOperationError: If write operation fails
        """
        file_path = Path(file_path)

        # Use file-level locking to prevent race conditions
        lock_file = file_path.with_suffix(file_path.suffix + '.lock')

        try:
            # Acquire lock
            self._acquire_file_lock(lock_file)

            # Create a copy and redact sensitive fields if requested
            write_data = data.copy() if redact_sensitive_fields else data

            if redact_sensitive_fields:
                write_data = self._redact_sensitive_data(write_data)

            # Calculate checksum for integrity verification
            json_content = json.dumps(write_data, sort_keys=True, indent=indent)
            checksum = hashlib.sha256(json_content.encode()).hexdigest()

            # Write atomically with secure permissions
            with self.secure_open(file_path, 'w', security_level) as f:
                f.write(json_content)

            # Verify file integrity
            self._verify_file_integrity(file_path, checksum)

            self.logger.info(f"Securely wrote JSON to {file_path} (level: {security_level.name})")

        except Exception as e:
            raise FileOperationError(f"Failed to securely write JSON to {file_path}: {e}")
        finally:
            # Release lock
            self._release_file_lock(lock_file)

    def _acquire_file_lock(self, lock_file: Path, timeout: float = 10.0) -> None:
        """Acquire a file lock to prevent race conditions."""
        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Try to create lock file
                lock_file.touch(exist_ok=False)
                return
            except FileExistsError:
                # Lock exists, wait and retry
                time.sleep(0.1)

        raise FileOperationError(f"Failed to acquire file lock for {lock_file} within {timeout}s")

    def _release_file_lock(self, lock_file: Path) -> None:
        """Release a file lock."""
        try:
            if lock_file.exists():
                lock_file.unlink()
        except OSError:
            pass  # Lock file cleanup failed, but that's not critical

    def read_json_secure(
        self,
        file_path: Union[str, Path],
        verify_integrity: bool = True
    ) -> Dict[str, Any]:
        """
        Securely read JSON data with integrity verification.

        Args:
            file_path: Path to read the JSON file
            verify_integrity: Whether to verify file integrity

        Returns:
            Parsed JSON data

        Raises:
            FileOperationError: If read operation fails
            FileIntegrityError: If integrity verification fails
        """
        file_path = Path(file_path)

        try:
            if not file_path.exists():
                raise FileOperationError(f"File does not exist: {file_path}")

            # Check file permissions
            if not self._is_windows and self._has_chmod:
                file_stat = file_path.stat()
                if file_stat.st_mode & 0o077:  # Check if others have read/write permissions
                    self.logger.warning(f"File {file_path} has insecure permissions: {oct(file_stat.st_mode & 0o777)}")

            # Read the file
            with self.secure_open(file_path, 'r') as f:
                data = json.load(f)

            # Verify integrity if requested
            if verify_integrity:
                checksum = self._calculate_file_checksum(file_path)
                stored_checksum = self._get_stored_checksum(file_path)
                if stored_checksum and checksum != stored_checksum:
                    raise FileIntegrityError(f"File integrity verification failed for {file_path}")

            self.logger.info(f"Securely read JSON from {file_path}")
            return data

        except json.JSONDecodeError as e:
            raise FileOperationError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise FileOperationError(f"Failed to securely read JSON from {file_path}: {e}")

    @contextmanager
    def secure_temp_file(
        self,
        directory: Optional[Union[str, Path]] = None,
        prefix: str = "secure_tmp",
        suffix: str = "",
        security_level: SecurityLevel = SecurityLevel.SENSITIVE,
        auto_cleanup: bool = True
    ) -> Iterator[Path]:
        """
        Create a secure temporary file with proper permissions and automatic cleanup.

        Args:
            directory: Directory for temporary file (default: system temp)
            prefix: File name prefix
            suffix: File name suffix
            security_level: Security level for file permissions
            auto_cleanup: Whether to automatically cleanup the file

        Yields:
            Path to the temporary file

        Raises:
            FileOperationError: If temporary file creation fails
        """
        temp_path = None
        file_id = str(uuid.uuid4())

        try:
            # Create temporary file
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)
                self._secure_directory(Path(directory))

            fd, temp_path = tempfile.mkstemp(
                prefix=prefix,
                suffix=suffix,
                dir=str(directory) if directory else None
            )
            os.close(fd)  # Close the file descriptor, we'll manage the file ourselves

            temp_path = Path(temp_path)

            # Set secure permissions
            if not self._is_windows and self._has_chmod:
                try:
                    os.chmod(temp_path, security_level.value)
                except OSError as e:
                    self.logger.warning(f"Failed to set permissions on temp file {temp_path}: {e}")

            # Register for cleanup if auto_cleanup is False
            if not auto_cleanup:
                with self._lock:
                    self._active_temp_files[file_id] = {
                        'path': temp_path,
                        'created_at': datetime.now(),
                        'auto_cleanup': auto_cleanup
                    }

            self.logger.debug(f"Created secure temporary file: {temp_path}")
            yield temp_path

        except Exception as e:
            # Clean up on error
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise FileOperationError(f"Failed to create secure temporary file: {e}")
        finally:
            # Clean up if auto_cleanup is enabled
            if auto_cleanup and temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                    self.logger.debug(f"Auto-cleaned temporary file: {temp_path}")
                except OSError as e:
                    self.logger.warning(f"Failed to cleanup temporary file {temp_path}: {e}")

            # Unregister from active files
            with self._lock:
                self._active_temp_files.pop(file_id, None)

    def cleanup_temp_files(self, max_age: Optional[timedelta] = None) -> int:
        """
        Clean up abandoned temporary files.

        Args:
            max_age: Maximum age for files to cleanup (default: 1 hour)

        Returns:
            Number of files cleaned up
        """
        if max_age is None:
            max_age = timedelta(hours=1)

        cleaned_count = 0
        now = datetime.now()

        with self._lock:
            expired_files = []

            for file_id, file_info in self._active_temp_files.items():
                file_path = file_info['path']
                created_at = file_info['created_at']

                # Check if file is expired
                if now - created_at > max_age:
                    expired_files.append((file_id, file_path))

            # Clean up expired files
            for file_id, file_path in expired_files:
                try:
                    if file_path.exists():
                        file_path.unlink()
                        cleaned_count += 1
                        self.logger.debug(f"Cleaned up expired temporary file: {file_path}")
                except OSError as e:
                    self.logger.warning(f"Failed to cleanup expired temp file {file_path}: {e}")
                finally:
                    self._active_temp_files.pop(file_id, None)

        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} expired temporary files")

        return cleaned_count

    def verify_file_permissions(
        self,
        file_path: Union[str, Path],
        expected_security_level: SecurityLevel
    ) -> bool:
        """
        Verify that a file has the expected security permissions.

        Args:
            file_path: Path to the file
            expected_security_level: Expected security level

        Returns:
            True if permissions are correct, False otherwise
        """
        if self._is_windows or not self._has_chmod:
            return True  # Skip permission checks on Windows

        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return False

            file_stat = file_path.stat()
            current_mode = file_stat.st_mode & 0o777
            expected_mode = expected_security_level.value

            # Check exact permissions
            if current_mode == expected_mode:
                return True

            # Log permission mismatch
            self.logger.warning(
                f"File {file_path} has incorrect permissions: "
                f"expected {oct(expected_mode)}, got {oct(current_mode)}"
            )
            return False

        except OSError as e:
            self.logger.error(f"Failed to verify permissions for {file_path}: {e}")
            return False

    def _create_temp_file(self, directory: Path, prefix: str) -> Path:
        """Create a temporary file in the specified directory."""
        fd, temp_path = tempfile.mkstemp(prefix=prefix, dir=str(directory))
        os.close(fd)
        return Path(temp_path)

    def _atomic_move(self, source: Path, destination: Path) -> None:
        """Atomically move a file from source to destination."""
        if self._is_windows:
            # Windows doesn't support atomic rename when destination exists
            if destination.exists():
                destination.unlink()

        source.replace(destination)

    def _secure_directory(self, directory: Path) -> None:
        """Set secure permissions on a directory."""
        if not self._is_windows and self._has_chmod:
            try:
                os.chmod(directory, 0o700)  # Read/write/execute by owner only
            except OSError as e:
                self.logger.warning(f"Failed to set directory permissions for {directory}: {e}")

    def _redact_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive fields from data."""
        sensitive_patterns = [
            'password', 'token', 'key', 'secret', 'credential', 'auth',
            'api_key', 'private', 'confidential', 'ssn', 'social_security',
            'sensitive'  # Add 'sensitive' to catch 'sensitive_field'
        ]

        if isinstance(data, dict):
            redacted = {}
            for key, value in data.items():
                key_lower = str(key).lower()
                if any(pattern in key_lower for pattern in sensitive_patterns):
                    redacted[key] = '[REDACTED]'
                else:
                    redacted[key] = self._redact_sensitive_data(value)
            return redacted
        elif isinstance(data, list):
            return [self._redact_sensitive_data(item) for item in data]
        else:
            return data

    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file."""
        with open(file_path, 'rb') as f:
            content = f.read()
            return hashlib.sha256(content).hexdigest()

    def _get_stored_checksum(self, file_path: Path) -> Optional[str]:
        """Get stored checksum from a sidecar file."""
        checksum_file = file_path.with_suffix(file_path.suffix + '.checksum')
        if checksum_file.exists():
            try:
                with open(checksum_file, 'r') as f:
                    return f.read().strip()
            except OSError:
                pass
        return None

    def _validate_file_path(self, file_path: Path) -> None:
        """Validate file path for security vulnerabilities."""
        path_str = str(file_path)

        # Check for empty paths
        if not path_str.strip():
            raise ValueError("File path cannot be empty")

        # Check for path traversal attempts
        if '..' in path_str:
            raise ValueError("Path traversal detected in file path")

        # Check for dangerous paths on Unix
        if not self._is_windows:
            dangerous_paths = ['/etc/passwd', '/etc/shadow', '/root/', '/proc/']
            for dangerous in dangerous_paths:
                if path_str.startswith(dangerous):
                    raise ValueError(f"Access to dangerous system path detected: {path_str}")

        # Check for dangerous paths on Windows
        if self._is_windows:
            dangerous_paths = [
                'C:\\Windows\\System32\\config\\',
                'C:\\Windows\\System32\\drivers\\etc\\hosts',
                '\\.\\PhysicalDrive',
                '\\.\\COM'
            ]
            path_upper = path_str.upper()
            for dangerous in dangerous_paths:
                if dangerous.upper() in path_upper:
                    raise ValueError(f"Access to dangerous system path detected: {path_str}")

    def _verify_file_integrity(self, file_path: Path, expected_checksum: str) -> None:
        """Verify file integrity by comparing checksums."""
        calculated_checksum = self._calculate_file_checksum(file_path)
        if calculated_checksum != expected_checksum:
            raise FileIntegrityError(
                f"File integrity verification failed for {file_path}: "
                f"expected {expected_checksum}, got {calculated_checksum}"
            )

        # Store checksum for future verification
        checksum_file = file_path.with_suffix(file_path.suffix + '.checksum')
        try:
            with self.secure_open(checksum_file, 'w', SecurityLevel.SENSITIVE) as f:
                f.write(expected_checksum)
        except Exception as e:
            self.logger.warning(f"Failed to store checksum for {file_path}: {e}")

    def _redact_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive fields from data."""
        sensitive_patterns = [
            'password', 'token', 'key', 'secret', 'credential', 'auth',
            'api_key', 'private', 'confidential', 'ssn', 'social_security',
            'sensitive'  # Add 'sensitive' to catch 'sensitive_field'
        ]

        if isinstance(data, dict):
            redacted = {}
            for key, value in data.items():
                key_lower = str(key).lower()
                if any(pattern in key_lower for pattern in sensitive_patterns):
                    redacted[key] = '[REDACTED]'
                else:
                    redacted[key] = self._redact_sensitive_data(value)
            return redacted
        elif isinstance(data, list):
            return [self._redact_sensitive_data(item) for item in data]
        else:
            return data

    def get_security_status(self) -> Dict[str, Any]:
        """Get security status information."""
        with self._lock:
            active_temp_count = len(self._active_temp_files)

        return {
            "platform": "Windows" if self._is_windows else "Unix-like",
            "chmod_available": self._has_chmod,
            "active_temp_files": active_temp_count,
            "last_cleanup": self._last_cleanup.isoformat(),
            "cleanup_interval_hours": self._cleanup_interval.total_seconds() / 3600
        }


# Global instance for easy access
_secure_ops = SecureFileOperations()


def get_secure_file_ops(logger: Optional[logging.Logger] = None) -> SecureFileOperations:
    """Get a secure file operations instance."""
    if logger:
        return SecureFileOperations(logger)
    return _secure_ops


# Convenience functions for common operations
def write_json_secure(
    file_path: Union[str, Path],
    data: Dict[str, Any],
    security_level: SecurityLevel = SecurityLevel.SENSITIVE,
    logger: Optional[logging.Logger] = None
) -> None:
    """Convenience function to write JSON securely."""
    ops = get_secure_file_ops(logger)
    ops.write_json_secure(file_path, data, security_level)


def read_json_secure(
    file_path: Union[str, Path],
    logger: Optional[logging.Logger] = None
) -> Dict[str, Any]:
    """Convenience function to read JSON securely."""
    ops = get_secure_file_ops(logger)
    return ops.read_json_secure(file_path)


def secure_temp_file(
    directory: Optional[Union[str, Path]] = None,
    prefix: str = "secure_tmp",
    logger: Optional[logging.Logger] = None
):
    """Convenience context manager for secure temporary files."""
    ops = get_secure_file_ops(logger)
    return ops.secure_temp_file(directory, prefix)