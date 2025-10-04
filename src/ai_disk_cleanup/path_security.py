"""
Path Security Module - Comprehensive path validation and traversal protection.

This module provides robust path validation to prevent directory traversal attacks,
symlink exploits, and unauthorized file system access across all platforms.
"""

import os
import pathlib
import platform
import stat
from typing import List, Optional, Set, Union, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PathValidationError(Exception):
    """Raised when path validation fails."""
    pass


class PathSecurityValidator:
    """
    Comprehensive path security validator preventing traversal attacks.

    Features:
    - Directory traversal prevention
    - Symlink security validation
    - Cross-platform path normalization
    - System path protection
    - Canonical path resolution
    """

    def __init__(self):
        self.system = platform.system().lower()
        self.allowed_base_paths: Set[str] = set()
        self.protected_system_paths = self._get_protected_system_paths()
        self.dangerous_patterns = self._get_dangerous_patterns()

    def _get_protected_system_paths(self) -> List[str]:
        """Get platform-specific protected system paths."""
        # Include paths from all platforms for cross-platform testing
        all_paths = []

        # Windows paths (include for testing on all platforms)
        windows_paths = [
            "C:\\Windows",
            "C:\\Windows\\System32",
            "C:\\Windows\\SysWOW64",
            "C:\\Windows\\Drivers",
            "C:\\Program Files",
            "C:\\Program Files (x86)",
            "C:\\ProgramData",
            "C:\\Users",
            "C:\\Documents and Settings",
            "C:\\System Volume Information",
            "C:\\Recovery",
            "C:\\Boot",
            "C:\\EFI",
            # Also include forward-slash versions for cross-platform testing
            "C:/Windows",
            "C:/Windows/System32",
            "C:/Windows/SysWOW64",
            "C:/Windows/Drivers",
            "C:/Program Files",
            "C:/Program Files (x86)",
            "C:/ProgramData",
            "C:/Users",
            "C:/Documents and Settings",
            "C:/System Volume Information",
            "C:/Recovery",
            "C:/Boot",
            "C:/EFI",
        ]
        all_paths.extend(windows_paths)

        # macOS paths (include for testing on all platforms)
        macos_paths = [
            "/System",
            "/Library",
            "/usr/bin",
            "/usr/lib",
            "/usr/sbin",
            "/sbin",
            "/bin",
            "/etc",
            "/var",
            "/Applications",
            "/Users/Shared",
            "/System/Library",
            "/Library/Application Support",
            "/private",
            "/dev",
            "/automount",
            "/net",
            "/home",
        ]
        all_paths.extend(macos_paths)

        # Linux paths (include for testing on all platforms)
        linux_paths = [
            "/bin",
            "/sbin",
            "/usr/bin",
            "/usr/sbin",
            "/usr/lib",
            "/usr/local/bin",
            "/usr/local/sbin",
            "/lib",
            "/lib64",
            "/etc",
            "/boot",
            "/sys",
            "/proc",
            "/dev",
            "/root",
            "/var",
            "/opt",
            "/srv",
            "/selinux",
            "/run",
        ]
        all_paths.extend(linux_paths)

        return all_paths

    def _get_dangerous_patterns(self) -> List[str]:
        """Get patterns that indicate dangerous path constructs."""
        patterns = [
            "..",  # Parent directory traversal
            "~",   # Home directory expansion
            "$",   # Environment variable expansion
            "&",   # Command chaining
            ";",   # Command separation
            "|",   # Command pipe
            "<",   # Input redirection
            ">",   # Output redirection
            "`",   # Command substitution
            "'",   # Quote injection
            "\"",  # Quote injection
            "\\",  # Escape sequences
        ]
        return patterns

    def add_allowed_base_path(self, path: Union[str, Path]) -> None:
        """
        Add a base path that is explicitly allowed for file operations.

        Args:
            path: The base path to allow

        Raises:
            PathValidationError: If path is invalid or dangerous
        """
        try:
            abs_path = os.path.abspath(str(path))
            normalized_path = os.path.normpath(abs_path)

            # Validate the path doesn't contain dangerous patterns
            self._validate_path_characters(normalized_path)

            # Check if path overlaps with protected system paths
            if self._is_protected_system_path(normalized_path):
                logger.warning(f"Added allowed path overlaps with protected system path: {normalized_path}")

            self.allowed_base_paths.add(normalized_path)
            logger.info(f"Added allowed base path: {normalized_path}")

        except Exception as e:
            raise PathValidationError(f"Failed to add allowed base path {path}: {e}")

    def remove_allowed_base_path(self, path: Union[str, Path]) -> None:
        """Remove an allowed base path."""
        abs_path = os.path.abspath(str(path))
        normalized_path = os.path.normpath(abs_path)
        self.allowed_base_paths.discard(normalized_path)
        logger.info(f"Removed allowed base path: {normalized_path}")

    def validate_directory_path(self, directory_path: Union[str, Path]) -> str:
        """
        Validate a directory path for scanning operations.

        Args:
            directory_path: The directory path to validate

        Returns:
            Normalized and validated absolute path

        Raises:
            PathValidationError: If path is invalid or dangerous
        """
        try:
            # Convert to string and normalize
            path_str = str(directory_path)

            # Check for dangerous patterns
            self._validate_path_characters(path_str)

            # Convert to absolute path
            abs_path = os.path.abspath(path_str)

            # Normalize path separators and resolve . and ..
            normalized_path = os.path.normpath(abs_path)

            # Validate path traversal attempts
            self._validate_traversal_prevention(path_str, normalized_path)

            # Validate against allowed base paths
            self._validate_against_allowed_paths(normalized_path)

            # Check if it's a protected system path
            if self._is_protected_system_path(normalized_path):
                raise PathValidationError(f"Access to protected system path is not allowed: {normalized_path}")

            # Validate path exists and is a directory (if it exists)
            if os.path.exists(normalized_path) and not os.path.isdir(normalized_path):
                raise PathValidationError(f"Path exists but is not a directory: {normalized_path}")

            logger.debug(f"Validated directory path: {normalized_path}")
            return normalized_path

        except PathValidationError:
            raise
        except Exception as e:
            raise PathValidationError(f"Failed to validate directory path {directory_path}: {e}")

    def validate_file_path(self, file_path: Union[str, Path], base_directory: Optional[Union[str, Path]] = None) -> str:
        """
        Validate a file path for file operations.

        Args:
            file_path: The file path to validate
            base_directory: Optional base directory to validate against

        Returns:
            Normalized and validated absolute path

        Raises:
            PathValidationError: If path is invalid or dangerous
        """
        try:
            path_str = str(file_path)

            # Check for dangerous patterns
            self._validate_path_characters(path_str)

            # Convert to absolute path
            if base_directory:
                # Resolve relative to base directory
                base_abs = os.path.abspath(str(base_directory))
                combined_path = os.path.join(base_abs, path_str)
                abs_path = os.path.abspath(combined_path)
            else:
                abs_path = os.path.abspath(path_str)

            # Normalize path separators and resolve . and ..
            normalized_path = os.path.normpath(abs_path)

            # Validate path traversal attempts
            self._validate_traversal_prevention(path_str, normalized_path)

            # Validate against allowed base paths
            self._validate_against_allowed_paths(normalized_path)

            # Check if it's a protected system file
            if self._is_protected_system_path(normalized_path):
                raise PathValidationError(f"Access to protected system file is not allowed: {normalized_path}")

            logger.debug(f"Validated file path: {normalized_path}")
            return normalized_path

        except PathValidationError:
            raise
        except Exception as e:
            raise PathValidationError(f"Failed to validate file path {file_path}: {e}")

    def validate_symlink(self, symlink_path: Union[str, Path]) -> Tuple[str, str]:
        """
        Validate a symlink for security.

        Args:
            symlink_path: The symlink path to validate

        Returns:
            Tuple of (symlink_path, target_path)

        Raises:
            PathValidationError: If symlink is invalid or dangerous
        """
        try:
            symlink_str = str(symlink_path)

            # First validate the symlink path itself
            validated_symlink_path = self.validate_file_path(symlink_str)

            # Check if it's actually a symlink
            if not os.path.islink(validated_symlink_path):
                raise PathValidationError(f"Path is not a symlink: {validated_symlink_path}")

            # Resolve the symlink target
            target_path = os.readlink(validated_symlink_path)

            # Validate the target path
            if not os.path.isabs(target_path):
                # Relative symlink - resolve relative to symlink directory
                symlink_dir = os.path.dirname(validated_symlink_path)
                target_abs = os.path.abspath(os.path.join(symlink_dir, target_path))
            else:
                target_abs = os.path.abspath(target_path)

            target_normalized = os.path.normpath(target_abs)

            # Check for dangerous patterns in target
            self._validate_path_characters(target_path)

            # Validate target doesn't escape allowed boundaries
            self._validate_traversal_prevention(target_path, target_normalized)
            self._validate_against_allowed_paths(target_normalized)

            # Check if target is a protected system path
            if self._is_protected_system_path(target_normalized):
                raise PathValidationError(f"Symlink points to protected system path: {target_normalized}")

            # Check for symlink loops
            if self._detect_symlink_loop(validated_symlink_path):
                raise PathValidationError(f"Symlink loop detected: {validated_symlink_path}")

            logger.debug(f"Validated symlink: {validated_symlink_path} -> {target_normalized}")
            return validated_symlink_path, target_normalized

        except PathValidationError:
            raise
        except Exception as e:
            raise PathValidationError(f"Failed to validate symlink {symlink_path}: {e}")

    def _validate_path_characters(self, path: str) -> None:
        """Validate path for dangerous character patterns."""
        # Check for null bytes
        if '\x00' in path:
            raise PathValidationError("Path contains null bytes")

        # Check for dangerous patterns that might indicate command injection
        path_lower = path.lower()
        for pattern in self.dangerous_patterns:
            if pattern in path:
                # Allow some legitimate uses of patterns
                if pattern == ".." and self._is_legitimate_parent_reference(path):
                    continue
                if pattern in ["'", "\"", "\\"] and self._is_legitimate_quote_usage(path):
                    continue
                raise PathValidationError(f"Path contains potentially dangerous pattern: {pattern}")

        # Check for extremely long paths that might cause buffer overflows
        if len(path) > 4096:  # Reasonable limit
            raise PathValidationError("Path is too long")

    def _is_legitimate_parent_reference(self, path: str) -> bool:
        """Check if '..' in path is legitimate (not for traversal)."""
        # This is a simplified check - in practice, you'd want more sophisticated logic
        return path.count("..") <= 1 and not path.startswith("../")

    def _is_legitimate_quote_usage(self, path: str) -> bool:
        """Check if quotes in path are legitimate."""
        # Allow quotes in file names but not at start/end (might indicate injection)
        return not (path.startswith("'") or path.startswith('"') or
                   path.endswith("'") or path.endswith('"'))

    def _validate_traversal_prevention(self, original_path: str, normalized_path: str) -> None:
        """Validate that path normalization didn't reveal traversal attempts."""
        # If the normalized path is significantly different from original, investigate
        original_abs = os.path.abspath(original_path)

        # Check if normalization resolved path outside expected bounds
        if normalized_path != os.path.normpath(original_abs):
            # Additional checks for traversal attempts
            if ".." in original_path:
                # Count parent directory references in original
                parent_count = original_path.count("..")
                # If there are multiple parent references, it's suspicious
                if parent_count > 2:
                    raise PathValidationError(f"Multiple parent directory references detected: {original_path}")

                # Check if path tries to escape from current directory
                current_dir = os.getcwd()
                if not normalized_path.startswith(current_dir):
                    # Check if it's in allowed base paths
                    if not any(normalized_path.startswith(base) for base in self.allowed_base_paths):
                        raise PathValidationError(f"Path traversal attempt detected: {original_path}")

    def _validate_against_allowed_paths(self, path: str) -> None:
        """Validate that path is within allowed base paths."""
        if not self.allowed_base_paths:
            # No restrictions if no base paths are set
            return

        # Check if path is within any allowed base path
        for base_path in self.allowed_base_paths:
            if path.startswith(base_path):
                return

        raise PathValidationError(f"Path is not within allowed base paths: {path}")

    def _is_protected_system_path(self, path: str) -> bool:
        """Check if path is a protected system path across all platforms."""
        normalized_path = os.path.normpath(path)

        # Normalize path separators for cross-platform comparison
        normalized_path = normalized_path.replace('\\', '/')

        for protected_path in self.protected_system_paths:
            normalized_protected = os.path.normpath(protected_path).replace('\\', '/')

            # Check if the path starts with the protected path
            if normalized_path.lower().startswith(normalized_protected.lower()):
                return True

        return False

    def _detect_symlink_loop(self, path: str, visited: Optional[Set[str]] = None, max_depth: int = 10) -> bool:
        """Detect if a symlink chain creates a loop."""
        if visited is None:
            visited = set()

        if max_depth <= 0:
            return True  # Assume loop if too deep

        if path in visited:
            return True

        visited.add(path)

        try:
            if os.path.islink(path):
                target = os.readlink(path)
                if not os.path.isabs(target):
                    target = os.path.abspath(os.path.join(os.path.dirname(path), target))

                return self._detect_symlink_loop(target, visited.copy(), max_depth - 1)
        except (OSError, PermissionError):
            return False

        return False

    def is_safe_to_scan(self, path: Union[str, Path]) -> bool:
        """
        Check if a path is safe to scan.

        Args:
            path: Path to check

        Returns:
            True if safe to scan, False otherwise
        """
        try:
            self.validate_directory_path(path)
            return True
        except PathValidationError:
            return False

    def is_safe_to_access(self, path: Union[str, Path]) -> bool:
        """
        Check if a file path is safe to access.

        Args:
            path: Path to check

        Returns:
            True if safe to access, False otherwise
        """
        try:
            self.validate_file_path(path)
            return True
        except PathValidationError:
            return False

    def get_allowed_base_paths(self) -> List[str]:
        """Get list of allowed base paths."""
        return list(self.allowed_base_paths)

    def clear_allowed_base_paths(self) -> None:
        """Clear all allowed base paths."""
        self.allowed_base_paths.clear()
        logger.info("Cleared all allowed base paths")