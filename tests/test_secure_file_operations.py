"""
Comprehensive security tests for secure file operations module.

This test suite validates the security measures implemented to address:
- MEDIUM (CVSS 6.5): Insecure temporary file creation
- MEDIUM: Temporary file information disclosure
"""

import json
import os
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.ai_disk_cleanup.security.secure_file_ops import (
    SecureFileOperations, SecurityLevel, FileOperationError, FileIntegrityError,
    write_json_secure, read_json_secure, secure_temp_file
)


class TestSecureFileOperations(unittest.TestCase):
    """Test secure file operations for security vulnerabilities."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="secure_file_test_"))
        self.secure_ops = SecureFileOperations()
        self.test_data = {
            "test_field": "test_value",
            "sensitive_field": "secret_data",
            "nested": {
                "password": "hidden_password",
                "public_info": "public_data"
            },
            "array": [
                {"api_key": "secret_key"},
                {"normal_data": "visible"}
            ]
        }

    def tearDown(self):
        """Clean up test environment."""
        # Clean up any remaining temp files
        self.secure_ops.cleanup_temp_files()

        # Remove test directory
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_secure_file_permissions_sensitive_level(self):
        """Test that sensitive files have correct 0o600 permissions."""
        if os.name == 'nt':  # Skip on Windows
            self.skipTest("Permission tests not applicable on Windows")

        test_file = self.test_dir / "sensitive_test.json"

        # Write file with SENSITIVE level
        self.secure_ops.write_json_secure(
            test_file,
            self.test_data,
            security_level=SecurityLevel.SENSITIVE
        )

        # Check file permissions
        file_stat = test_file.stat()
        permissions = file_stat.st_mode & 0o777

        # Should be 0o600 (read/write by owner only)
        self.assertEqual(permissions, 0o600,
                        f"Expected 0o600 permissions, got {oct(permissions)}")

    def test_secure_file_permissions_critical_level(self):
        """Test that critical files have correct 0o400 permissions."""
        if os.name == 'nt':  # Skip on Windows
            self.skipTest("Permission tests not applicable on Windows")

        test_file = self.test_dir / "critical_test.json"

        # Write file with CRITICAL level
        self.secure_ops.write_json_secure(
            test_file,
            self.test_data,
            security_level=SecurityLevel.CRITICAL
        )

        # Check file permissions
        file_stat = test_file.stat()
        permissions = file_stat.st_mode & 0o777

        # Should be 0o400 (read-only by owner)
        self.assertEqual(permissions, 0o400,
                        f"Expected 0o400 permissions, got {oct(permissions)}")

    def test_secure_file_permissions_public_level(self):
        """Test that public files have correct 0o644 permissions."""
        if os.name == 'nt':  # Skip on Windows
            self.skipTest("Permission tests not applicable on Windows")

        test_file = self.test_dir / "public_test.json"

        # Write file with PUBLIC level
        self.secure_ops.write_json_secure(
            test_file,
            self.test_data,
            security_level=SecurityLevel.PUBLIC
        )

        # Check file permissions
        file_stat = test_file.stat()
        permissions = file_stat.st_mode & 0o777

        # Should be 0o644 (read/write by owner, read by others)
        self.assertEqual(permissions, 0o644,
                        f"Expected 0o644 permissions, got {oct(permissions)}")

    def test_atomic_write_operations(self):
        """Test that file writes are atomic to prevent partial writes."""
        test_file = self.test_dir / "atomic_test.json"

        # Write a large amount of data
        large_data = {
            "large_array": list(range(10000)),
            "nested_data": {
                f"key_{i}": f"value_{i}" * 100  # Large strings
                for i in range(100)
            }
        }

        # Write the data
        self.secure_ops.write_json_secure(
            test_file,
            large_data,
            security_level=SecurityLevel.SENSITIVE
        )

        # Verify file exists and is complete
        self.assertTrue(test_file.exists())

        # Read back and verify integrity
        read_data = self.secure_ops.read_json_secure(test_file)
        self.assertEqual(read_data, large_data)

        # Verify checksum file was created
        checksum_file = test_file.with_suffix(test_file.suffix + '.checksum')
        self.assertTrue(checksum_file.exists())

    def test_temporary_file_cleanup(self):
        """Test that temporary files are properly cleaned up."""
        temp_files = []

        # Create multiple temporary files without auto-cleanup
        for i in range(5):
            # Use the lower-level method to create temp files without cleanup
            import tempfile
            fd, temp_path = tempfile.mkstemp(
                prefix=f"test_temp_{i}_",
                dir=str(self.test_dir)
            )
            os.close(fd)
            temp_file = Path(temp_path)

            # Manually register with secure operations for cleanup tracking
            file_id = f"test_{i}"
            with self.secure_ops._lock:
                self.secure_ops._active_temp_files[file_id] = {
                    'path': temp_file,
                    'created_at': datetime.now() - timedelta(seconds=1),  # Make it 1 second old
                    'auto_cleanup': False
                }

            temp_files.append(temp_file)

            # Write some data
            with open(temp_file, 'w') as f:
                f.write(f"test_data_{i}")

        # Verify temp files exist
        for temp_file in temp_files:
            self.assertTrue(temp_file.exists())

        # Manually cleanup files older than 0 seconds
        cleaned_count = self.secure_ops.cleanup_temp_files(max_age=timedelta(seconds=0))

        # Verify cleanup
        self.assertEqual(cleaned_count, len(temp_files))
        for temp_file in temp_files:
            self.assertFalse(temp_file.exists())

    def test_sensitive_data_redaction(self):
        """Test that sensitive data is properly redacted in public exports."""
        test_file = self.test_dir / "redaction_test.json"

        # Write with redaction enabled
        self.secure_ops.write_json_secure(
            test_file,
            self.test_data,
            security_level=SecurityLevel.PUBLIC,
            redact_sensitive_fields=True
        )

        # Read the file
        with open(test_file, 'r') as f:
            content = f.read()

        # Verify sensitive fields are redacted
        self.assertIn('[REDACTED]', content)

        # Parse JSON and check specific fields
        data = json.loads(content)
        self.assertEqual(data['sensitive_field'], '[REDACTED]')
        self.assertEqual(data['nested']['password'], '[REDACTED]')
        self.assertNotEqual(data['nested']['public_info'], '[REDACTED]')

    def test_file_integrity_verification(self):
        """Test file integrity verification using checksums."""
        test_file = self.test_dir / "integrity_test.json"

        # Write original data
        self.secure_ops.write_json_secure(
            test_file,
            self.test_data,
            security_level=SecurityLevel.SENSITIVE
        )

        # Read with integrity verification (should succeed)
        read_data = self.secure_ops.read_json_secure(test_file, verify_integrity=True)
        self.assertEqual(read_data, self.test_data)

        # Corrupt the file by modifying it directly
        with open(test_file, 'w') as f:
            f.write(json.dumps({"corrupted": "data"}))

        # Reading with integrity verification should now fail
        with self.assertRaises(FileIntegrityError):
            self.secure_ops.read_json_secure(test_file, verify_integrity=True)

    def test_secure_temp_file_permissions(self):
        """Test that temporary files have secure permissions."""
        if os.name == 'nt':  # Skip on Windows
            self.skipTest("Permission tests not applicable on Windows")

        with self.secure_ops.secure_temp_file(
            directory=self.test_dir,
            prefix="perm_test_",
            security_level=SecurityLevel.SENSITIVE
        ) as temp_file:
            # Check permissions
            file_stat = temp_file.stat()
            permissions = file_stat.st_mode & 0o777

            # Should be 0o600 for sensitive temp files
            self.assertEqual(permissions, 0o600,
                           f"Expected 0o600 permissions for temp file, got {oct(permissions)}")

    def test_race_condition_protection(self):
        """Test protection against race conditions in file operations."""
        test_file = self.test_dir / "race_test.json"
        results = []
        errors = []

        def writer_thread(thread_id):
            try:
                data = {"thread_id": thread_id, "timestamp": time.time()}
                self.secure_ops.write_json_secure(
                    test_file,
                    data,
                    security_level=SecurityLevel.SENSITIVE
                )
                results.append(thread_id)
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Start multiple threads writing to the same file
        threads = []
        for i in range(10):
            thread = threading.Thread(target=writer_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify that operations completed without errors
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")

        # Verify that final file is valid
        self.assertTrue(test_file.exists())
        read_data = self.secure_ops.read_json_secure(test_file)
        self.assertIn("thread_id", read_data)
        self.assertIn("timestamp", read_data)

    def test_path_traversal_prevention(self):
        """Test that path traversal attacks are prevented."""
        # Use paths that would exist in the filesystem
        if os.name != 'nt':  # Unix/Linux
            malicious_paths = [
                "/etc/passwd",
                "/etc/shadow",
                "../../../etc/passwd",
                "/root/.ssh/id_rsa"
            ]
        else:  # Windows
            malicious_paths = [
                "C:\\Windows\\System32\\config\\SAM",
                "..\\..\\..\\Windows\\System32\\config\\SAM"
            ]

        for malicious_path in malicious_paths:
            with self.assertRaises((FileOperationError, ValueError)):
                self.secure_ops.write_json_secure(
                    malicious_path,
                    self.test_data,
                    security_level=SecurityLevel.SENSITIVE
                )

        # Test empty path
        with self.assertRaises((FileOperationError, ValueError)):
            self.secure_ops.write_json_secure(
                "",
                self.test_data,
                security_level=SecurityLevel.SENSITIVE
            )

    def test_secure_open_context_manager(self):
        """Test secure open context manager handles cleanup properly."""
        test_file = self.test_dir / "context_test.txt"

        # Test normal operation
        with self.secure_ops.secure_open(
            test_file,
            'w',
            SecurityLevel.SENSITIVE
        ) as f:
            f.write("test content")

        # Verify file was created with correct content
        self.assertTrue(test_file.exists())
        with open(test_file, 'r') as f:
            self.assertEqual(f.read(), "test content")

        # Test exception handling
        try:
            with self.secure_ops.secure_open(
                test_file,
                'w',
                SecurityLevel.SENSITIVE
            ) as f:
                f.write("should not persist")
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected

        # Verify original content is preserved (atomic write)
        with open(test_file, 'r') as f:
            self.assertEqual(f.read(), "test content")

    def test_large_file_handling(self):
        """Test secure handling of large files."""
        test_file = self.test_dir / "large_test.json"

        # Create large data structure
        large_data = {
            "large_array": list(range(50000)),
            "large_strings": ["x" * 1000 for _ in range(1000)],
            "nested": {
                f"key_{i}": {"value": i, "data": "y" * 100}
                for i in range(1000)
            }
        }

        # Write large file
        start_time = time.time()
        self.secure_ops.write_json_secure(
            test_file,
            large_data,
            security_level=SecurityLevel.SENSITIVE
        )
        write_time = time.time() - start_time

        # Read large file
        start_time = time.time()
        read_data = self.secure_ops.read_json_secure(test_file, verify_integrity=True)
        read_time = time.time() - start_time

        # Verify data integrity
        self.assertEqual(read_data, large_data)

        # Performance should be reasonable (less than 5 seconds for this size)
        self.assertLess(write_time, 5.0, "Write operation took too long")
        self.assertLess(read_time, 5.0, "Read operation took too long")

    def test_concurrent_temp_file_operations(self):
        """Test concurrent temporary file operations."""
        results = []
        errors = []

        def temp_file_thread(thread_id):
            try:
                with self.secure_ops.secure_temp_file(
                    directory=self.test_dir,
                    prefix=f"concurrent_test_{thread_id}_"
                ) as temp_file:
                    # Write thread-specific data
                    data = {"thread_id": thread_id, "data": f"test_{thread_id}"}
                    self.secure_ops.write_json_secure(
                        temp_file,
                        data,
                        security_level=SecurityLevel.SENSITIVE
                    )

                    # Read it back
                    read_data = self.secure_ops.read_json_secure(temp_file)
                    results.append((thread_id, read_data))
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Start multiple threads
        threads = []
        for i in range(20):
            thread = threading.Thread(target=temp_file_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all operations succeeded
        self.assertEqual(len(errors), 0, f"Errors in concurrent operations: {errors}")
        self.assertEqual(len(results), 20, "Not all operations completed")

        # Verify data integrity
        for thread_id, data in results:
            self.assertEqual(data["thread_id"], thread_id)
            self.assertIn("data", data)

    def test_security_level_validation(self):
        """Test security level validation and enforcement."""
        test_file = self.test_dir / "security_test.json"

        # Test all security levels
        for level in SecurityLevel:
            # Should succeed
            self.secure_ops.write_json_secure(
                test_file,
                {"level": level.name},
                security_level=level
            )

            # Verify file exists
            self.assertTrue(test_file.exists())

            # Clean up for next iteration
            test_file.unlink()

    def test_memory_safety(self):
        """Test that operations don't leak memory or expose sensitive data."""
        test_file = self.test_dir / "memory_test.json"

        # Write sensitive data
        sensitive_data = {
            "secrets": ["password1", "api_key_123", "token_abc"],
            "credentials": {"user": "admin", "pass": "secret123"}
        }

        self.secure_ops.write_json_secure(
            test_file,
            sensitive_data,
            security_level=SecurityLevel.CRITICAL
        )

        # Read data back
        read_data = self.secure_ops.read_json_secure(test_file)

        # Verify data is correct
        self.assertEqual(read_data, sensitive_data)

        # Verify file permissions are restrictive
        if os.name != 'nt':  # Skip on Windows
            file_stat = test_file.stat()
            permissions = file_stat.st_mode & 0o777
            self.assertEqual(permissions, 0o400)  # Read-only by owner

    def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms."""
        test_file = self.test_dir / "error_test.json"

        # Test handling of permission errors (mock)
        with patch('os.chmod', side_effect=OSError("Permission denied")):
            # Should still work, just log warning
            self.secure_ops.write_json_secure(
                test_file,
                self.test_data,
                security_level=SecurityLevel.SENSITIVE
            )
            self.assertTrue(test_file.exists())

        # Test handling of disk full errors (mock)
        with patch('builtins.open', side_effect=OSError("No space left on device")):
            with self.assertRaises(FileOperationError):
                self.secure_ops.write_json_secure(
                    test_file,
                    self.test_data,
                    security_level=SecurityLevel.SENSITIVE
                )

        # Test handling of corrupted JSON files
        corrupted_file = self.test_dir / "corrupted.json"
        with open(corrupted_file, 'w') as f:
            f.write("{ invalid json content")

        with self.assertRaises(FileOperationError):
            self.secure_ops.read_json_secure(corrupted_file)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions for secure file operations."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="convenience_test_"))
        self.test_data = {"test": "data", "number": 42}

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_write_json_secure_convenience(self):
        """Test write_json_secure convenience function."""
        test_file = self.test_dir / "convenience_write.json"

        write_json_secure(test_file, self.test_data)

        self.assertTrue(test_file.exists())

        with open(test_file, 'r') as f:
            data = json.load(f)

        self.assertEqual(data, self.test_data)

    def test_read_json_secure_convenience(self):
        """Test read_json_secure convenience function."""
        test_file = self.test_dir / "convenience_read.json"

        # First write the file
        write_json_secure(test_file, self.test_data)

        # Then read it back
        read_data = read_json_secure(test_file)

        self.assertEqual(read_data, self.test_data)

    def test_secure_temp_file_convenience(self):
        """Test secure_temp_file convenience context manager."""
        with secure_temp_file(directory=self.test_dir, prefix="convenience_") as temp_file:
            self.assertTrue(temp_file.exists())
            self.assertTrue(temp_file.parent == self.test_dir)

            # Write some data
            with open(temp_file, 'w') as f:
                f.write("test content")

        # File should be cleaned up
        self.assertFalse(temp_file.exists())


if __name__ == '__main__':
    unittest.main()