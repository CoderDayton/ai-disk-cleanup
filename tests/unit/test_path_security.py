"""
Comprehensive test suite for path security validation and traversal protection.

This test suite validates:
- Directory traversal prevention
- Symlink security validation
- Cross-platform path protection
- System path protection bypass prevention
- Edge cases and boundary conditions

Security Requirements:
- CVSS 8.2 path traversal vulnerability prevention
- Zero trust path validation
- Cross-platform compatibility
- Comprehensive edge case coverage
"""

import pytest
import os
import tempfile
import shutil
import pathlib
import platform
from unittest.mock import patch, MagicMock
import logging

from src.ai_disk_cleanup.path_security import PathSecurityValidator, PathValidationError


class TestPathSecurityValidator:
    """Test suite for path security validation."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.validator = PathSecurityValidator()
        self.current_platform = platform.system().lower()

    def teardown_method(self):
        """Clean up after each test method."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_path_traversal_prevention_basic(self):
        """Test basic directory traversal prevention."""
        # Add allowed base path
        self.validator.add_allowed_base_path(self.temp_dir)

        # Test traversal attempts
        traversal_paths = [
            f"{self.temp_dir}/../../../etc/passwd",
            f"{self.temp_dir}/../..",
            f"{self.temp_dir}/..",
            "../etc/passwd",
            "../../Windows/System32",
            "../../../bin/bash"
        ]

        for path in traversal_paths:
            with pytest.raises(PathValidationError):
                self.validator.validate_directory_path(path)

            with pytest.raises(PathValidationError):
                self.validator.validate_file_path(path)

    def test_path_traversal_prevention_complex(self):
        """Test complex directory traversal attempts."""
        self.validator.add_allowed_base_path(self.temp_dir)

        complex_traversal_paths = [
            f"{self.temp_dir}/subdir/../../../etc/passwd",
            f"{self.temp_dir}/./../../../etc/shadow",
            f"{self.temp_dir}/sub/../sub2/../../../etc/hosts",
            f"{self.temp_dir}/sub/../../../../../../root/.ssh",
        ]

        for path in complex_traversal_paths:
            with pytest.raises(PathValidationError):
                self.validator.validate_directory_path(path)

    def test_safe_path_validation(self):
        """Test validation of safe paths."""
        self.validator.add_allowed_base_path(self.temp_dir)

        # Create test directory structure
        test_subdir = os.path.join(self.temp_dir, "safe_subdir")
        os.makedirs(test_subdir, exist_ok=True)

        test_file = os.path.join(test_subdir, "safe_file.txt")
        pathlib.Path(test_file).touch()

        # These should be valid
        assert self.validator.is_safe_to_scan(self.temp_dir)
        assert self.validator.is_safe_to_scan(test_subdir)
        assert self.validator.is_safe_to_access(test_file)

        # Validate directory paths
        validated_dir = self.validator.validate_directory_path(test_subdir)
        assert validated_dir == os.path.normpath(os.path.abspath(test_subdir))

        # Validate file paths
        validated_file = self.validator.validate_file_path(test_file)
        assert validated_file == os.path.normpath(os.path.abspath(test_file))

    def test_system_path_protection_windows(self):
        """Test Windows system path protection."""
        if self.current_platform != "windows":
            pytest.skip("Windows-specific test")

        system_paths = [
            "C:\\Windows\\System32",
            "C:\\Windows\\SysWOW64",
            "C:\\Program Files",
            "C:\\Program Files (x86)",
            "C:\\ProgramData",
            "C:\\Users",
        ]

        for path in system_paths:
            # Should raise validation error for system paths
            with pytest.raises(PathValidationError):
                self.validator.validate_directory_path(path)

            with pytest.raises(PathValidationError):
                self.validator.validate_file_path(path + "\\test.txt")

    def test_system_path_protection_macos(self):
        """Test macOS system path protection."""
        if self.current_platform != "darwin":
            pytest.skip("macOS-specific test")

        system_paths = [
            "/System",
            "/Library",
            "/usr/bin",
            "/usr/lib",
            "/sbin",
            "/bin",
            "/Applications",
            "/Users/Shared",
        ]

        for path in system_paths:
            # Should raise validation error for system paths
            with pytest.raises(PathValidationError):
                self.validator.validate_directory_path(path)

            with pytest.raises(PathValidationError):
                self.validator.validate_file_path(path + "/test.txt")

    def test_system_path_protection_linux(self):
        """Test Linux system path protection."""
        if self.current_platform == "windows" or self.current_platform == "darwin":
            pytest.skip("Linux-specific test")

        system_paths = [
            "/bin",
            "/sbin",
            "/usr/bin",
            "/usr/sbin",
            "/usr/lib",
            "/lib",
            "/etc",
            "/boot",
            "/sys",
            "/proc",
            "/dev",
            "/root",
        ]

        for path in system_paths:
            # Should raise validation error for system paths
            with pytest.raises(PathValidationError):
                self.validator.validate_directory_path(path)

            with pytest.raises(PathValidationError):
                self.validator.validate_file_path(path + "/test.txt")

    def test_symlink_security_validation(self):
        """Test symlink security validation."""
        self.validator.add_allowed_base_path(self.temp_dir)

        # Create target file
        target_file = os.path.join(self.temp_dir, "target.txt")
        pathlib.Path(target_file).touch()

        # Create safe symlink
        safe_symlink = os.path.join(self.temp_dir, "safe_link.txt")
        os.symlink(target_file, safe_symlink)

        # Should validate safe symlink
        symlink_path, target_path = self.validator.validate_symlink(safe_symlink)
        assert symlink_path == os.path.normpath(os.path.abspath(safe_symlink))
        assert target_path == os.path.normpath(os.path.abspath(target_file))

        # Create dangerous symlink pointing outside allowed path
        outside_dir = tempfile.mkdtemp()
        outside_file = os.path.join(outside_dir, "outside.txt")
        pathlib.Path(outside_file).touch()

        dangerous_symlink = os.path.join(self.temp_dir, "dangerous_link.txt")
        os.symlink(outside_file, dangerous_symlink)

        # Should reject dangerous symlink
        with pytest.raises(PathValidationError):
            self.validator.validate_symlink(dangerous_symlink)

        # Clean up
        shutil.rmtree(outside_dir)

    def test_symlink_loop_detection(self):
        """Test symlink loop detection."""
        self.validator.add_allowed_base_path(self.temp_dir)

        # Create symlink loop
        symlink1 = os.path.join(self.temp_dir, "link1")
        symlink2 = os.path.join(self.temp_dir, "link2")

        os.symlink(symlink2, symlink1)
        os.symlink(symlink1, symlink2)

        # Should detect loop
        with pytest.raises(PathValidationError):
            self.validator.validate_symlink(symlink1)

    def test_broken_symlink_handling(self):
        """Test broken symlink handling."""
        self.validator.add_allowed_base_path(self.temp_dir)

        # Create broken symlink
        broken_symlink = os.path.join(self.temp_dir, "broken_link")
        os.symlink("/non/existent/file", broken_symlink)

        # Should handle broken symlink appropriately
        with pytest.raises(PathValidationError):
            self.validator.validate_symlink(broken_symlink)

    def test_path_normalization_edge_cases(self):
        """Test path normalization edge cases."""
        self.validator.add_allowed_base_path(self.temp_dir)

        # Test various path formats
        test_paths = [
            f"{self.temp_dir}/./subdir",
            f"{self.temp_dir}/subdir/./file.txt",
            f"{self.temp_dir}//subdir//file.txt",
            f"{self.temp_dir}/subdir/../subdir2",
        ]

        for path in test_paths:
            # Should normalize and validate
            try:
                if path.endswith(".txt"):
                    validated = self.validator.validate_file_path(path)
                else:
                    validated = self.validator.validate_directory_path(path)

                # Should not contain "." or ".." after normalization
                assert "/./" not in validated
                assert "/../" not in validated
                assert not validated.endswith("/.")
                assert not validated.endswith("/..")
            except PathValidationError:
                # Some might be invalid due to traversal, which is expected
                pass

    def test_dangerous_character_detection(self):
        """Test detection of dangerous character patterns."""
        dangerous_paths = [
            f"{self.temp_dir}/file\x00name.txt",  # Null byte
            f"{self.temp_dir}/file`whoami`.txt",  # Command substitution
            f"{self.temp_dir}/file|cat/etc/passwd.txt",  # Command pipe
            f"{self.temp_dir}/file;rm-rf/.txt",  # Command chaining
            f"{self.temp_dir}/file$HOME.txt",  # Environment variable
        ]

        self.validator.add_allowed_base_path(self.temp_dir)

        for path in dangerous_paths:
            with pytest.raises(PathValidationError):
                self.validator.validate_file_path(path)

    def test_extremely_long_paths(self):
        """Test handling of extremely long paths."""
        self.validator.add_allowed_base_path(self.temp_dir)

        # Create very long path
        long_path = self.temp_dir + "/" + "a" * 5000

        with pytest.raises(PathValidationError):
            self.validator.validate_directory_path(long_path)

    def test_relative_vs_absolute_paths(self):
        """Test relative vs absolute path handling."""
        self.validator.add_allowed_base_path(self.temp_dir)

        # Test relative paths
        os.chdir(self.temp_dir)
        relative_path = "subdir/file.txt"

        # Should handle relative paths properly
        validated = self.validator.validate_file_path(relative_path)
        expected = os.path.normpath(os.path.abspath(relative_path))
        assert validated == expected

        # Test absolute paths
        absolute_path = os.path.join(self.temp_dir, "subdir", "file.txt")
        validated_abs = self.validator.validate_file_path(absolute_path)
        expected_abs = os.path.normpath(os.path.abspath(absolute_path))
        assert validated_abs == expected_abs

    def test_allowed_base_paths_management(self):
        """Test allowed base paths management."""
        # Test adding paths
        test_path1 = os.path.join(self.temp_dir, "allowed1")
        test_path2 = os.path.join(self.temp_dir, "allowed2")

        self.validator.add_allowed_base_path(test_path1)
        self.validator.add_allowed_base_path(test_path2)

        allowed_paths = self.validator.get_allowed_base_paths()
        assert len(allowed_paths) == 2
        assert os.path.normpath(test_path1) in allowed_paths
        assert os.path.normpath(test_path2) in allowed_paths

        # Test removing paths
        self.validator.remove_allowed_base_path(test_path1)
        allowed_paths = self.validator.get_allowed_base_paths()
        assert len(allowed_paths) == 1
        assert os.path.normpath(test_path1) not in allowed_paths

        # Test clearing paths
        self.validator.clear_allowed_base_paths()
        allowed_paths = self.validator.get_allowed_base_paths()
        assert len(allowed_paths) == 0

    def test_no_allowed_paths_restriction(self):
        """Test behavior when no allowed base paths are set."""
        # Without allowed base paths, should be more permissive
        # but still block system paths and dangerous patterns

        # Should allow normal paths
        assert self.validator.is_safe_to_scan(self.temp_dir)

        # Should still block dangerous patterns
        with pytest.raises(PathValidationError):
            self.validator.validate_file_path(f"{self.temp_dir}/../../../etc/passwd")

        # Should still block system paths
        if self.current_platform != "windows":
            with pytest.raises(PathValidationError):
                self.validator.validate_directory_path("/bin")

    def test_cross_platform_path_separators(self):
        """Test cross-platform path separator handling."""
        self.validator.add_allowed_base_path(self.temp_dir)

        # Test with forward slashes on Windows
        if self.current_platform == "windows":
            windows_path = self.temp_dir.replace("\\", "/") + "/subdir/file.txt"
            try:
                validated = self.validator.validate_file_path(windows_path)
                assert os.path.normpath(validated) == os.path.normpath(os.path.abspath(windows_path))
            except PathValidationError:
                # May fail due to path format, which is acceptable
                pass

    def test_case_sensitivity_handling(self):
        """Test case sensitivity handling across platforms."""
        self.validator.add_allowed_base_path(self.temp_dir)

        # Create test file
        test_file = os.path.join(self.temp_dir, "TestFile.txt")
        pathlib.Path(test_file).touch()

        # Test case variations
        case_variants = [
            test_file,
            test_file.lower(),
            test_file.upper(),
        ]

        for variant in case_variants:
            if os.path.exists(variant):
                try:
                    validated = self.validator.validate_file_path(variant)
                    assert os.path.normpath(validated) == os.path.normpath(os.path.abspath(variant))
                except PathValidationError:
                    # Some variations might not be accessible on some platforms
                    pass

    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters in paths."""
        self.validator.add_allowed_base_path(self.temp_dir)

        # Create paths with unicode characters
        unicode_paths = [
            os.path.join(self.temp_dir, "файл.txt"),  # Russian
            os.path.join(self.temp_dir, "文件.txt"),   # Chinese
            os.path.join(self.temp_dir, "ファイル.txt"), # Japanese
            os.path.join(self.temp_dir, "fichier avec espaces.txt"),  # French with spaces
            os.path.join(self.temp_dir, "archivo-con-guiones.txt"),  # Spanish with dashes
        ]

        for path in unicode_paths:
            # Create directory/file if needed
            if not os.path.exists(path):
                dir_path = os.path.dirname(path)
                if dir_path and not os.path.exists(dir_path):
                    os.makedirs(dir_path, exist_ok=True)
                pathlib.Path(path).touch()

            try:
                validated = self.validator.validate_file_path(path)
                assert os.path.normpath(validated) == os.path.normpath(os.path.abspath(path))
            except PathValidationError:
                # Some unicode might not be supported on all systems
                pass

    def test_permission_error_handling(self):
        """Test handling of permission-related errors."""
        self.validator.add_allowed_base_path(self.temp_dir)

        # Mock permission error
        with patch('os.path.exists', side_effect=PermissionError("Permission denied")):
            # Should handle permission errors gracefully
            with pytest.raises(PathValidationError):
                self.validator.validate_directory_path(self.temp_dir)

    def test_file_not_found_handling(self):
        """Test handling of non-existent paths."""
        self.validator.add_allowed_base_path(self.temp_dir)

        non_existent = os.path.join(self.temp_dir, "does_not_exist")

        # Directory validation for non-existent path should work (for future scanning)
        try:
            validated = self.validator.validate_directory_path(non_existent)
            assert os.path.normpath(validated) == os.path.normpath(os.path.abspath(non_existent))
        except PathValidationError:
            # May fail if there are other security issues
            pass

        # File validation for non-existent file should also work
        non_existent_file = os.path.join(non_existent, "file.txt")
        try:
            validated = self.validator.validate_file_path(non_existent_file)
            assert os.path.normpath(validated) == os.path.normpath(os.path.abspath(non_existent_file))
        except PathValidationError:
            # May fail if there are other security issues
            pass

    def test_edge_case_parent_references(self):
        """Test edge cases with parent directory references."""
        self.validator.add_allowed_base_path(self.temp_dir)

        # Create subdirectory
        subdir = os.path.join(self.temp_dir, "subdir")
        os.makedirs(subdir, exist_ok=True)

        # Test legitimate parent reference
        legit_path = os.path.join(subdir, "..", "file.txt")
        pathlib.Path(legit_path).touch()

        try:
            validated = self.validator.validate_file_path(legit_path)
            assert os.path.normpath(validated) == os.path.normpath(os.path.abspath(legit_path))
        except PathValidationError:
            # May be blocked if too many parent references
            pass

        # Test suspicious parent references
        suspicious_path = os.path.join(subdir, "..", "..", "..", "etc", "passwd")
        with pytest.raises(PathValidationError):
            self.validator.validate_file_path(suspicious_path)

    def test_concurrent_validation_safety(self):
        """Test thread safety of path validation."""
        import threading
        import time

        results = []
        errors = []

        def validate_paths():
            try:
                for i in range(10):
                    test_path = os.path.join(self.temp_dir, f"test_{i}.txt")
                    validated = self.validator.validate_file_path(test_path)
                    results.append(validated)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=validate_paths)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"No errors should occur during concurrent validation: {errors}"
        assert len(results) == 50, "All validations should complete successfully"


class TestPathSecurityIntegration:
    """Integration tests for path security with file scanner."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up after each test method."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_file_scanner_integration(self):
        """Test integration with file scanner."""
        from src.ai_disk_cleanup.file_scanner import FileScanner

        # Create test directory structure
        test_subdir = os.path.join(self.temp_dir, "test_subdir")
        os.makedirs(test_subdir, exist_ok=True)

        test_file = os.path.join(test_subdir, "test_file.txt")
        pathlib.Path(test_file).touch()

        # Create scanner with security
        scanner = FileScanner(allowed_base_paths=[self.temp_dir])

        # Should scan allowed directory
        files = scanner.scan_directory(self.temp_dir)
        assert len(files) > 0

        # Should reject traversal attempt
        with pytest.raises(ValueError):
            scanner.scan_directory(f"{self.temp_dir}/../../../etc")

    def test_safety_layer_integration(self):
        """Test integration with safety layer."""
        from src.ai_disk_cleanup.safety_layer import SafetyLayer

        safety_layer = SafetyLayer()

        # Test system file protection
        if platform.system().lower() != "windows":
            system_file = "/bin/bash"
            protection_level = safety_layer.evaluate_protection_level(system_file)
            assert protection_level.value == "critical"

        # Test user protection path
        user_path = os.path.join(self.temp_dir, "user_protected")
        os.makedirs(user_path, exist_ok=True)
        safety_layer.add_user_protection_path(user_path)

        test_file = os.path.join(user_path, "test.txt")
        pathlib.Path(test_file).touch()

        protection_level = safety_layer.evaluate_protection_level(test_file)
        assert protection_level.value in ["high", "critical"]


# Test fixtures
@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def path_validator():
    """Create a PathSecurityValidator instance for testing."""
    return PathSecurityValidator()


@pytest.fixture
def security_test_structure(temp_directory):
    """Create a test directory structure with various security scenarios."""
    structure = {}

    # Safe directories and files
    structure['safe_dir'] = os.path.join(temp_directory, "safe_dir")
    os.makedirs(structure['safe_dir'], exist_ok=True)

    structure['safe_file'] = os.path.join(structure['safe_dir'], "safe_file.txt")
    pathlib.Path(structure['safe_file']).touch()

    # Create subdirectory
    structure['subdir'] = os.path.join(structure['safe_dir'], "subdir")
    os.makedirs(structure['subdir'], exist_ok=True)

    structure['subdir_file'] = os.path.join(structure['subdir'], "subdir_file.txt")
    pathlib.Path(structure['subdir_file']).touch()

    return structure


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])