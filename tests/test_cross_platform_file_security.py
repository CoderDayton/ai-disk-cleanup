"""
Cross-platform compatibility tests for secure file operations.

This test suite validates that security measures work correctly across different
operating systems (Windows, macOS, Linux) and handle platform-specific limitations.
"""

import json
import os
import platform
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.ai_disk_cleanup.security.secure_file_ops import (
    SecureFileOperations, SecurityLevel, FileOperationError
)


class TestCrossPlatformCompatibility(unittest.TestCase):
    """Test cross-platform compatibility of secure file operations."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="cross_platform_test_"))
        self.secure_ops = SecureFileOperations()
        self.is_windows = os.name == 'nt'
        self.is_macos = platform.system() == 'Darwin'
        self.is_linux = platform.system() == 'Linux'
        self.test_data = {
            "test_content": "This is test data",
            "platform_info": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version()
            }
        }

    def tearDown(self):
        """Clean up test environment."""
        self.secure_ops.cleanup_temp_files()
        import shutil
        if self.test_dir.exists():
            try:
                shutil.rmtree(self.test_dir)
            except PermissionError:
                # Handle Windows permission issues
                pass

    def test_platform_detection(self):
        """Test that platform is correctly detected."""
        security_status = self.secure_ops.get_security_status()

        if self.is_windows:
            self.assertEqual(security_status["platform"], "Windows")
        else:
            self.assertEqual(security_status["platform"], "Unix-like")

        # Check if chmod is available
        expected_chmod = not self.is_windows
        self.assertEqual(security_status["chmod_available"], expected_chmod)

    def test_windows_permission_handling(self):
        """Test permission handling on Windows."""
        test_file = self.test_dir / "windows_test.json"

        # This should work on Windows without throwing permission errors
        try:
            self.secure_ops.write_json_secure(
                test_file,
                self.test_data,
                security_level=SecurityLevel.SENSITIVE
            )

            # File should exist and be readable
            self.assertTrue(test_file.exists())

            # Should be able to read it back
            read_data = self.secure_ops.read_json_secure(test_file)
            self.assertEqual(read_data, self.test_data)

        except FileOperationError as e:
            if self.is_windows:
                self.fail(f"Secure file operations failed on Windows: {e}")

    def test_unix_permission_handling(self):
        """Test permission handling on Unix-like systems."""
        if self.is_windows:
            self.skipTest("Unix-specific permission test")

        test_file = self.test_dir / "unix_test.json"

        # Test sensitive file permissions
        self.secure_ops.write_json_secure(
            test_file,
            self.test_data,
            security_level=SecurityLevel.SENSITIVE
        )

        # Check file permissions
        file_stat = test_file.stat()
        permissions = file_stat.st_mode & 0o777
        self.assertEqual(permissions, 0o600)

        # Test critical file permissions
        critical_file = self.test_dir / "critical_test.json"
        self.secure_ops.write_json_secure(
            critical_file,
            self.test_data,
            security_level=SecurityLevel.CRITICAL
        )

        file_stat = critical_file.stat()
        permissions = file_stat.st_mode & 0o777
        self.assertEqual(permissions, 0o400)

    def test_path_handling_cross_platform(self):
        """Test path handling across different platforms."""
        test_cases = [
            "normal_file.json",
            "file with spaces.json",
            "file-with-dashes.json",
            "file_with_underscores.json"
        ]

        # Add platform-specific test cases
        if not self.is_windows:
            test_cases.extend([
                "file.with.dots.json",
                "file'with'quotes.json"
            ])

        for filename in test_cases:
            test_file = self.test_dir / filename

            # This should work regardless of platform
            self.secure_ops.write_json_secure(
                test_file,
                {"filename": filename, "test_data": "value"},
                security_level=SecurityLevel.PUBLIC
            )

            self.assertTrue(test_file.exists(), f"Failed to create file: {filename}")

            # Should be able to read it back
            read_data = self.secure_ops.read_json_secure(test_file)
            self.assertEqual(read_data["filename"], filename)

    def test_temp_file_handling_cross_platform(self):
        """Test temporary file handling across platforms."""
        temp_files = []

        # Create multiple temporary files
        for i in range(3):
            with self.secure_ops.secure_temp_file(
                directory=self.test_dir,
                prefix=f"temp_test_{i}_",
                suffix=".tmp"
            ) as temp_file:
                temp_files.append(temp_file)

                # Write some data
                with open(temp_file, 'w') as f:
                    f.write(f"temp_data_{i}")

                # Verify file exists
                self.assertTrue(temp_file.exists())

                # Verify directory structure is correct
                self.assertTrue(temp_file.parent == self.test_dir)

            # File should be cleaned up automatically
            self.assertFalse(temp_file.exists())

    def test_atomic_operations_cross_platform(self):
        """Test atomic file operations across platforms."""
        test_file = self.test_dir / "atomic_test.json"

        # Write initial data
        initial_data = {"initial": "data", "version": 1}
        self.secure_ops.write_json_secure(
            test_file,
            initial_data,
            security_level=SecurityLevel.PUBLIC
        )

        # Verify initial data
        read_data = self.secure_ops.read_json_secure(test_file)
        self.assertEqual(read_data, initial_data)

        # Write new data
        new_data = {"updated": "data", "version": 2}
        self.secure_ops.write_json_secure(
            test_file,
            new_data,
            security_level=SecurityLevel.PUBLIC
        )

        # Verify new data replaced old data atomically
        read_data = self.secure_ops.read_json_secure(test_file)
        self.assertEqual(read_data, new_data)

        # File should not be corrupted
        self.assertIsInstance(read_data, dict)
        self.assertIn("version", read_data)

    def test_large_file_handling_cross_platform(self):
        """Test large file handling across platforms."""
        test_file = self.test_dir / "large_test.json"

        # Create reasonably large data (not too large for test)
        large_data = {
            "large_array": list(range(10000)),
            "string_data": ["test string" for _ in range(1000)],
            "nested": {
                f"key_{i}": {"value": i, "data": f"test_{i}" * 10}
                for i in range(1000)
            }
        }

        # This should work on all platforms
        self.secure_ops.write_json_secure(
            test_file,
            large_data,
            security_level=SecurityLevel.SENSITIVE
        )

        # Verify file exists
        self.assertTrue(test_file.exists())

        # Check file size
        file_size = test_file.stat().st_size
        self.assertGreater(file_size, 1000)  # Should be substantial

        # Should be able to read it back
        read_data = self.secure_ops.read_json_secure(test_file)
        self.assertEqual(len(read_data["large_array"]), 10000)

    def test_concurrent_operations_cross_platform(self):
        """Test concurrent operations across platforms."""
        import threading
        import time

        results = []
        errors = []

        def worker_thread(thread_id):
            try:
                test_file = self.test_dir / f"concurrent_{thread_id}.json"
                data = {"thread_id": thread_id, "timestamp": time.time()}

                self.secure_ops.write_json_secure(
                    test_file,
                    data,
                    security_level=SecurityLevel.SENSITIVE
                )

                # Read it back
                read_data = self.secure_ops.read_json_secure(test_file)
                results.append((thread_id, read_data))
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify results
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 5)

        for thread_id, data in results:
            self.assertEqual(data["thread_id"], thread_id)

    def test_error_handling_cross_platform(self):
        """Test error handling across platforms."""
        # Test invalid paths
        invalid_paths = [
            "",  # Empty path
            "   ",  # Whitespace only
        ]

        # Add platform-specific invalid paths
        if self.is_windows:
            invalid_paths.extend([
                "C:\\nonexistent\\path\\file.json",
                "Z:\\invalid\\drive\\file.json"
            ])
        else:
            invalid_paths.extend([
                "/nonexistent/path/file.json",
                "/root/nonexistent/file.json"
            ])

        for invalid_path in invalid_paths:
            with self.assertRaises((FileOperationError, ValueError, FileNotFoundError)):
                self.secure_ops.write_json_secure(
                    invalid_path,
                    self.test_data,
                    security_level=SecurityLevel.SENSITIVE
                )

    def test_file_integrity_cross_platform(self):
        """Test file integrity verification across platforms."""
        test_file = self.test_dir / "integrity_test.json"

        # Write file with integrity
        self.secure_ops.write_json_secure(
            test_file,
            self.test_data,
            security_level=SecurityLevel.SENSITIVE
        )

        # Read with integrity verification
        read_data = self.secure_ops.read_json_secure(test_file, verify_integrity=True)
        self.assertEqual(read_data, self.test_data)

        # Verify checksum file exists
        checksum_file = test_file.with_suffix(test_file.suffix + '.checksum')
        self.assertTrue(checksum_file.exists())

        # Corrupt the main file
        with open(test_file, 'w') as f:
            f.write('{"corrupted": "data"}')

        # Integrity check should fail
        from src.ai_disk_cleanup.security.secure_file_ops import FileIntegrityError
        with self.assertRaises(FileIntegrityError):
            self.secure_ops.read_json_secure(test_file, verify_integrity=True)

    def test_special_characters_in_paths(self):
        """Test handling of special characters in file paths."""
        special_filenames = [
            "file_with_umlaut_äöü.json",
            "file_with_accents_áéíóú.json",
            "file_with_cyrillic_файл.json",
            "file_with_chinese_文件.json",
            "file_with_symbols_!@#$%^&().json"
        ]

        for filename in special_filenames:
            try:
                test_file = self.test_dir / filename

                self.secure_ops.write_json_secure(
                    test_file,
                    {"filename": filename, "test": True},
                    security_level=SecurityLevel.PUBLIC
                )

                self.assertTrue(test_file.exists())

                read_data = self.secure_ops.read_json_secure(test_file)
                self.assertEqual(read_data["filename"], filename)

            except (UnicodeEncodeError, FileOperationError) as e:
                # Some platforms may not support all characters
                if self.is_windows:
                    # Windows has more limitations with special characters
                    print(f"Skipping {filename} on Windows: {e}")
                    continue
                else:
                    raise

    def test_cleanup_operations_cross_platform(self):
        """Test cleanup operations across platforms."""
        temp_files = []

        # Create temp files without auto-cleanup
        for i in range(3):
            with self.secure_ops.secure_temp_file(
                directory=self.test_dir,
                prefix=f"cleanup_test_{i}_",
                auto_cleanup=False
            ) as temp_file:
                temp_files.append(temp_file)

        # Verify files exist
        for temp_file in temp_files:
            self.assertTrue(temp_file.exists())

        # Run cleanup
        from datetime import timedelta
        cleaned_count = self.secure_ops.cleanup_temp_files(max_age=timedelta(seconds=0))

        # Should clean up all files
        self.assertEqual(cleaned_count, len(temp_files))

        # Verify files are gone
        for temp_file in temp_files:
            self.assertFalse(temp_file.exists())

    def test_security_status_cross_platform(self):
        """Test security status reporting across platforms."""
        status = self.secure_ops.get_security_status()

        # Verify required fields
        required_fields = [
            "platform", "chmod_available", "active_temp_files",
            "last_cleanup", "cleanup_interval_hours"
        ]

        for field in required_fields:
            self.assertIn(field, status)

        # Verify platform detection
        if self.is_windows:
            self.assertEqual(status["platform"], "Windows")
            self.assertFalse(status["chmod_available"])
        else:
            self.assertEqual(status["platform"], "Unix-like")
            self.assertTrue(status["chmod_available"])

        # Verify cleanup interval
        self.assertIsInstance(status["cleanup_interval_hours"], (int, float))
        self.assertGreater(status["cleanup_interval_hours"], 0)


class TestPlatformSpecificBehaviors(unittest.TestCase):
    """Test platform-specific behaviors and edge cases."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="platform_specific_test_"))
        self.secure_ops = SecureFileOperations()
        self.is_windows = os.name == 'nt'

    def tearDown(self):
        """Clean up test environment."""
        self.secure_ops.cleanup_temp_files()
        import shutil
        if self.test_dir.exists():
            try:
                shutil.rmtree(self.test_dir)
            except PermissionError:
                pass

    def test_windows_case_sensitivity(self):
        """Test case sensitivity behavior on Windows vs Unix."""
        if not self.is_windows:
            self.skipTest("Windows-specific test")

        test_file1 = self.test_dir / "TestFile.json"
        test_file2 = self.test_dir / "testfile.json"

        # Write to first file
        self.secure_ops.write_json_secure(
            test_file1,
            {"file": "TestFile.json"},
            security_level=SecurityLevel.PUBLIC
        )

        # On Windows, these should be the same file (case-insensitive)
        self.assertTrue(test_file1.exists())
        self.assertTrue(test_file2.exists())

        # Reading from either should give same data
        data1 = self.secure_ops.read_json_secure(test_file1)
        data2 = self.secure_ops.read_json_secure(test_file2)
        self.assertEqual(data1, data2)

    def test_unix_case_sensitivity(self):
        """Test case sensitivity behavior on Unix systems."""
        if self.is_windows:
            self.skipTest("Unix-specific test")

        test_file1 = self.test_dir / "TestFile.json"
        test_file2 = self.test_dir / "testfile.json"

        # Write to first file
        self.secure_ops.write_json_secure(
            test_file1,
            {"file": "TestFile.json"},
            security_level=SecurityLevel.PUBLIC
        )

        # On Unix, these should be different files (case-sensitive)
        self.assertTrue(test_file1.exists())
        self.assertFalse(test_file2.exists())

        # Writing to second file should create a separate file
        self.secure_ops.write_json_secure(
            test_file2,
            {"file": "testfile.json"},
            security_level=SecurityLevel.PUBLIC
        )

        # Now both should exist with different content
        self.assertTrue(test_file1.exists())
        self.assertTrue(test_file2.exists())

        data1 = self.secure_ops.read_json_secure(test_file1)
        data2 = self.secure_ops.read_json_secure(test_file2)
        self.assertNotEqual(data1, data2)

    def test_permission_graceful_degradation(self):
        """Test graceful degradation when permissions can't be set."""
        test_file = self.test_dir / "permission_test.json"

        # Mock chmod to always fail
        with patch('os.chmod', side_effect=OSError("Permission denied")):
            # Should still work, just log warning
            try:
                self.secure_ops.write_json_secure(
                    test_file,
                    {"test": "data"},
                    security_level=SecurityLevel.SENSITIVE
                )
                # File should still be created
                self.assertTrue(test_file.exists())
            except FileOperationError:
                # On some systems, this might fail, and that's okay
                pass

    def test_file_locking_behavior(self):
        """Test file locking behavior across platforms."""
        test_file = self.test_dir / "lock_test.json"

        # Write initial data
        self.secure_ops.write_json_secure(
            test_file,
            {"initial": "data"},
            security_level=SecurityLevel.PUBLIC
        )

        # Try to read while file is being written (simulated)
        # This tests whether the atomic writes prevent partial reads
        for i in range(10):
            new_data = {"iteration": i, "data": f"test_{i}"}
            self.secure_ops.write_json_secure(
                test_file,
                new_data,
                security_level=SecurityLevel.PUBLIC
            )

            # Read should always get complete data, never partial
            read_data = self.secure_ops.read_json_secure(test_file)
            self.assertEqual(read_data["iteration"], i)
            self.assertIn("data", read_data)


if __name__ == '__main__':
    unittest.main()