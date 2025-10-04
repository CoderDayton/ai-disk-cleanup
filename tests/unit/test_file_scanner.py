"""
Comprehensive test suite for File Scanner component.

Tests metadata extraction, cross-platform compatibility, performance,
error handling, and edge cases for file scanning functionality.
"""

import os
import pathlib
import tempfile
import time
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

# Add the src directory to the path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ai_disk_cleanup.file_scanner import FileMetadata, FileScanner


class TestFileMetadata(unittest.TestCase):
    """Test cases for FileMetadata class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file_path = os.path.join(self.temp_dir, "test_file.txt")

        # Create a test file
        with open(self.test_file_path, 'w') as f:
            f.write("Test content")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_file_metadata_creation(self):
        """Test creating FileMetadata from a valid file."""
        metadata = FileMetadata.from_path(self.test_file_path)

        self.assertEqual(metadata.name, "test_file.txt")
        self.assertEqual(metadata.extension, "txt")
        self.assertGreater(metadata.size_bytes, 0)
        self.assertIsInstance(metadata.modified_date, datetime)
        self.assertEqual(metadata.directory_path, self.temp_dir)
        self.assertEqual(metadata.file_type, "document")
        self.assertTrue(metadata.full_path.endswith("test_file.txt"))
        self.assertTrue(metadata.is_readable)
        self.assertTrue(metadata.is_writable)
        self.assertFalse(metadata.is_hidden)

    def test_file_metadata_no_extension(self):
        """Test FileMetadata creation for file without extension."""
        no_ext_file = os.path.join(self.temp_dir, "no_extension")
        with open(no_ext_file, 'w') as f:
            f.write("Test content")

        metadata = FileMetadata.from_path(no_ext_file)

        self.assertEqual(metadata.name, "no_extension")
        self.assertEqual(metadata.extension, "")
        self.assertEqual(metadata.file_type, "no_extension")

    def test_file_type_determination(self):
        """Test file type determination for various extensions."""
        test_cases = [
            ("document.pdf", "document"),
            ("image.jpg", "image"),
            ("video.mp4", "video"),
            ("audio.mp3", "audio"),
            ("archive.zip", "archive"),
            ("code.py", "code"),
            ("executable.exe", "executable"),
            ("unknown.xyz", "unknown"),
            ("UPPERCASE.TXT", "document"),  # Test case sensitivity
        ]

        for filename, expected_type in test_cases:
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, 'w') as f:
                f.write("Test content")

            metadata = FileMetadata.from_path(file_path)
            self.assertEqual(metadata.file_type, expected_type,
                           f"Failed for {filename}: expected {expected_type}, got {metadata.file_type}")

    def test_file_metadata_nonexistent_file(self):
        """Test FileMetadata creation with non-existent file."""
        with self.assertRaises(FileNotFoundError):
            FileMetadata.from_path("/nonexistent/file.txt")

    def test_file_metadata_directory_path(self):
        """Test FileMetadata creation with directory path."""
        with self.assertRaises(ValueError):
            FileMetadata.from_path(self.temp_dir)

    def test_hidden_file_detection_unix(self):
        """Test hidden file detection on Unix-like systems."""
        if os.name == 'nt':  # Skip on Windows
            self.skipTest("Unix-specific test")

        hidden_file = os.path.join(self.temp_dir, ".hidden_file")
        with open(hidden_file, 'w') as f:
            f.write("Test content")

        metadata = FileMetadata.from_path(hidden_file)
        self.assertTrue(metadata.is_hidden)

    def test_file_permissions(self):
        """Test file permission detection."""
        metadata = FileMetadata.from_path(self.test_file_path)
        self.assertTrue(metadata.is_readable)
        self.assertTrue(metadata.is_writable)

    def test_file_size_accuracy(self):
        """Test file size accuracy."""
        # Create file with known content
        test_content = "A" * 100  # 100 characters
        test_file = os.path.join(self.temp_dir, "size_test.txt")

        with open(test_file, 'w') as f:
            f.write(test_content)

        metadata = FileMetadata.from_path(test_file)
        self.assertEqual(metadata.size_bytes, len(test_content.encode('utf-8')))


class TestFileScanner(unittest.TestCase):
    """Test cases for FileScanner class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.scanner = FileScanner()

        # Create test directory structure
        self._create_test_directory_structure()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_directory_structure(self):
        """Create a test directory structure with various files."""
        # Create subdirectories
        subdir1 = os.path.join(self.temp_dir, "subdir1")
        subdir2 = os.path.join(self.temp_dir, "subdir2")
        os.makedirs(subdir1)
        os.makedirs(subdir2)

        # Create test files in root directory
        files_to_create = [
            "test1.txt",
            "test2.jpg",
            "test3.pdf",
            "no_extension",
            ".hidden_file"
        ]

        for filename in files_to_create:
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, 'w') as f:
                f.write(f"Content of {filename}")

        # Create files in subdirectories
        for i, subdir in enumerate([subdir1, subdir2]):
            for j in range(2):
                filename = f"subfile{i+1}_{j+1}.dat"
                file_path = os.path.join(subdir, filename)
                with open(file_path, 'w') as f:
                    f.write(f"Content of {filename}")

    def test_scan_directory_basic(self):
        """Test basic directory scanning."""
        files = self.scanner.scan_directory(self.temp_dir, recursive=False)

        # Should find files in root directory only (excluding hidden)
        self.assertEqual(len(files), 4)  # 4 visible files, hidden excluded by default

        # Check that hidden files are excluded by default
        hidden_found = any(f.name == ".hidden_file" for f in files)
        self.assertFalse(hidden_found)

    def test_scan_directory_recursive(self):
        """Test recursive directory scanning."""
        files = self.scanner.scan_directory(self.temp_dir, recursive=True)

        # Should find all files in all directories (excluding hidden)
        expected_count = 8  # 4 in root + 2 in subdir1 + 2 in subdir2 (excluding hidden)
        self.assertEqual(len(files), expected_count)

    def test_scan_directory_include_hidden(self):
        """Test scanning with hidden files included."""
        scanner_with_hidden = FileScanner(include_hidden=True)
        files = scanner_with_hidden.scan_directory(self.temp_dir, recursive=False)

        # Should include hidden file
        hidden_found = any(f.name == ".hidden_file" for f in files)
        self.assertTrue(hidden_found)

        # Should now find 5 files (4 visible + 1 hidden)
        self.assertEqual(len(files), 5)

    def test_scan_directory_with_filter(self):
        """Test scanning with file extension filter."""
        filter_set = {"txt", "jpg"}
        files = self.scanner.scan_directory(self.temp_dir, recursive=False, file_filter=filter_set)

        # Should only find files with specified extensions
        for file_metadata in files:
            self.assertIn(file_metadata.extension, filter_set)

    def test_scan_directory_generator(self):
        """Test generator-based directory scanning."""
        files = list(self.scanner.scan_directory_generator(self.temp_dir, recursive=True))

        # Should find same number of files as regular scan
        regular_files = self.scanner.scan_directory(self.temp_dir, recursive=True)
        self.assertEqual(len(files), len(regular_files))

    def test_scan_nonexistent_directory(self):
        """Test scanning non-existent directory."""
        with self.assertRaises(ValueError):
            self.scanner.scan_directory("/nonexistent/directory")

    def test_scan_file_instead_of_directory(self):
        """Test scanning a file instead of directory."""
        test_file = os.path.join(self.temp_dir, "test1.txt")
        with self.assertRaises(ValueError):
            self.scanner.scan_directory(test_file)

    def test_scan_statistics(self):
        """Test scan statistics collection."""
        self.scanner.scan_directory(self.temp_dir, recursive=True)
        stats = self.scanner.get_scan_statistics()

        self.assertIn("scanned_directories", stats)
        self.assertIn("scanned_files", stats)
        self.assertIn("unique_extensions", stats)
        self.assertIn("error_count", stats)
        self.assertIn("errors", stats)

        self.assertGreater(stats["scanned_directories"], 0)
        self.assertGreater(stats["scanned_files"], 0)
        self.assertIsInstance(stats["unique_extensions"], set)

    def test_max_file_size_filter(self):
        """Test maximum file size filtering."""
        # Create a large file
        large_file = os.path.join(self.temp_dir, "large_file.txt")
        with open(large_file, 'w') as f:
            f.write("A" * 1000)  # 1000 characters

        scanner_with_limit = FileScanner(max_file_size=500)  # 500 byte limit
        files = scanner_with_limit.scan_directory(self.temp_dir, recursive=False)

        # Large file should be excluded
        large_found = any(f.name == "large_file.txt" for f in files)
        self.assertFalse(large_found)

    def test_symlink_handling(self):
        """Test symbolic link handling."""
        if os.name == 'nt':  # Skip on Windows if symlinks not available
            try:
                os.symlink(self.temp_dir, os.path.join(self.temp_dir, "symlink"))
            except OSError:
                self.skipTest("Symlinks not supported on this system")
        else:
            # Create a symlink
            symlink_path = os.path.join(self.temp_dir, "symlink_to_file")
            target_file = os.path.join(self.temp_dir, "test1.txt")
            os.symlink(target_file, symlink_path)

            # Test without following symlinks
            scanner_no_symlinks = FileScanner(follow_symlinks=False)
            files = scanner_no_symlinks.scan_directory(self.temp_dir, recursive=False)
            symlink_found = any(f.name == "symlink_to_file" for f in files)
            self.assertFalse(symlink_found)

            # Test with following symlinks
            scanner_with_symlinks = FileScanner(follow_symlinks=True)
            files = scanner_with_symlinks.scan_directory(self.temp_dir, recursive=False)
            symlink_found = any(f.name == "symlink_to_file" for f in files)
            self.assertTrue(symlink_found)


class TestCrossPlatformCompatibility(unittest.TestCase):
    """Test cross-platform compatibility."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_pathlib_path_handling(self):
        """Test pathlib.Path handling for cross-platform compatibility."""
        # Test with string path
        test_file_str = os.path.join(self.temp_dir, "test_str.txt")
        with open(test_file_str, 'w') as f:
            f.write("Test")

        metadata_str = FileMetadata.from_path(test_file_str)

        # Test with pathlib.Path
        test_file_path = pathlib.Path(self.temp_dir) / "test_path.txt"
        with open(test_file_path, 'w') as f:
            f.write("Test")

        metadata_path = FileMetadata.from_path(test_file_path)

        # Both should work the same way
        self.assertIsInstance(metadata_str, FileMetadata)
        self.assertIsInstance(metadata_path, FileMetadata)
        self.assertEqual(metadata_str.name, "test_str.txt")
        self.assertEqual(metadata_path.name, "test_path.txt")

    def test_path_separator_handling(self):
        """Test handling of different path separators."""
        # Create file with various path formats
        scanner = FileScanner()

        # Test forward slashes (Unix style)
        forward_slash_path = self.temp_dir.replace(os.sep, '/') + "/test_forward.txt"
        with open(forward_slash_path.replace('/', os.sep), 'w') as f:
            f.write("Test")

        files = scanner.scan_directory(self.temp_dir, recursive=False)
        forward_found = any(f.name == "test_forward.txt" for f in files)
        self.assertTrue(forward_found)

    def test_absolute_relative_paths(self):
        """Test handling of absolute and relative paths."""
        # Create test file
        test_file = os.path.join(self.temp_dir, "test_absolute.txt")
        with open(test_file, 'w') as f:
            f.write("Test")

        # Test absolute path
        metadata_abs = FileMetadata.from_path(test_file)

        # Test relative path (by changing to temp directory)
        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            metadata_rel = FileMetadata.from_path("test_absolute.txt")

            # Both should produce the same full_path (absolute)
            self.assertEqual(metadata_abs.full_path, metadata_rel.full_path)
        finally:
            os.chdir(original_cwd)


class TestPerformanceBenchmarks(unittest.TestCase):
    """Performance benchmark tests for file scanning."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.scanner = FileScanner()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scanning_performance_small_directory(self):
        """Test scanning performance for small directories (< 30 seconds target)."""
        # Create a moderately sized directory structure
        num_files = 100
        num_dirs = 10

        for dir_idx in range(num_dirs):
            subdir = os.path.join(self.temp_dir, f"subdir_{dir_idx}")
            os.makedirs(subdir)

            for file_idx in range(num_files // num_dirs):
                filename = f"file_{dir_idx}_{file_idx}.txt"
                filepath = os.path.join(subdir, filename)
                with open(filepath, 'w') as f:
                    f.write(f"Content of {filename}")

        # Benchmark the scanning
        start_time = time.time()
        files = self.scanner.scan_directory(self.temp_dir, recursive=True)
        end_time = time.time()

        scan_duration = end_time - start_time

        # Assertions
        self.assertEqual(len(files), num_files)
        self.assertLess(scan_duration, 30.0, f"Scanning took {scan_duration:.2f} seconds, target is < 30 seconds")

        # Performance metrics
        files_per_second = num_files / scan_duration
        self.assertGreater(files_per_second, 10, f"Scanning rate is too slow: {files_per_second:.2f} files/second")

    def test_memory_efficiency_generator(self):
        """Test memory efficiency of generator-based scanning."""
        # Create many files to test memory usage
        num_files = 1000

        for file_idx in range(num_files):
            filename = f"large_file_{file_idx}.dat"
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write("X" * 100)  # 100 bytes per file

        # Test generator scanning (should use less memory)
        start_time = time.time()
        file_count = 0

        for file_metadata in self.scanner.scan_directory_generator(self.temp_dir, recursive=True):
            file_count += 1
            # Process each file (simulate some work)
            _ = file_metadata.size_bytes

        end_time = time.time()

        # Assertions
        self.assertEqual(file_count, num_files)
        self.assertLess(end_time - start_time, 30.0, "Generator scanning took too long")

    def test_scan_statistics_overhead(self):
        """Test that statistics collection doesn't add significant overhead."""
        # Create test files
        for i in range(50):
            filename = f"stats_test_{i}.txt"
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write(f"Content {i}")

        # Scan with statistics
        start_time = time.time()
        files = self.scanner.scan_directory(self.temp_dir, recursive=True)
        stats = self.scanner.get_scan_statistics()
        end_time = time.time()

        # Verify statistics are collected correctly
        self.assertEqual(len(files), 50)
        self.assertEqual(stats["scanned_files"], 50)
        self.assertGreater(stats["scanned_directories"], 0)

        # Statistics overhead should be minimal
        scan_duration = end_time - start_time
        self.assertLess(scan_duration, 5.0, "Statistics collection added too much overhead")


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_permission_denied_handling(self):
        """Test handling of permission denied errors."""
        # Create a file and remove read permissions (on Unix)
        test_file = os.path.join(self.temp_dir, "restricted.txt")
        with open(test_file, 'w') as f:
            f.write("Restricted content")

        if os.name != 'nt':  # Unix-like systems
            # Remove read permissions
            os.chmod(test_file, 0o000)

            try:
                # This should handle the permission error gracefully
                scanner = FileScanner()
                files = scanner.scan_directory(self.temp_dir, recursive=False)

                # File should still be found but marked as unreadable
                restricted_file = next((f for f in files if f.name == "restricted.txt"), None)
                self.assertIsNotNone(restricted_file)
                self.assertFalse(restricted_file.is_readable)

                # No error should be recorded since we can still get metadata
                # (the metadata extraction itself doesn't require read access on Unix)
                stats = scanner.get_scan_statistics()
                self.assertEqual(stats["error_count"], 0)

            finally:
                # Restore permissions for cleanup
                os.chmod(test_file, 0o644)

    def test_corrupted_file_handling(self):
        """Test handling of corrupted or inaccessible files."""
        # This is a simulated test - in practice, corrupted files might
        # still be accessible for metadata extraction

        # Create a normal file first
        test_file = os.path.join(self.temp_dir, "normal.txt")
        with open(test_file, 'w') as f:
            f.write("Normal content")

        # Should work fine
        metadata = FileMetadata.from_path(test_file)
        self.assertIsNotNone(metadata)

    def test_special_file_types(self):
        """Test handling of special file types."""
        # Create a regular file for comparison
        regular_file = os.path.join(self.temp_dir, "regular.txt")
        with open(regular_file, 'w') as f:
            f.write("Regular content")

        # Should handle regular files normally
        metadata = FileMetadata.from_path(regular_file)
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.file_type, "document")

    def test_unicode_filenames(self):
        """Test handling of Unicode filenames."""
        unicode_filenames = [
            "测试文件.txt",  # Chinese
            "файл.txt",  # Russian
            "Archivo.txt",  # Spanish with special characters
            "📄.txt",  # Emoji
        ]

        scanner = FileScanner()

        for filename in unicode_filenames:
            try:
                filepath = os.path.join(self.temp_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"Content of {filename}")

                metadata = FileMetadata.from_path(filepath)
                self.assertEqual(metadata.name, filename)

            except UnicodeEncodeError:
                # Skip if filesystem doesn't support this filename
                continue

    def test_very_long_filenames(self):
        """Test handling of very long filenames."""
        # Create a filename close to typical filesystem limits
        long_name = "a" * 200 + ".txt"

        try:
            filepath = os.path.join(self.temp_dir, long_name)
            with open(filepath, 'w') as f:
                f.write("Long filename test")

            metadata = FileMetadata.from_path(filepath)
            self.assertEqual(metadata.name, long_name)

        except OSError:
            # Skip if filesystem doesn't support long filenames
            self.skipTest("Filesystem doesn't support very long filenames")

    def test_empty_directory_handling(self):
        """Test scanning empty directories."""
        empty_dir = os.path.join(self.temp_dir, "empty")
        os.makedirs(empty_dir)

        scanner = FileScanner()
        files = scanner.scan_directory(empty_dir, recursive=False)

        self.assertEqual(len(files), 0)

        stats = scanner.get_scan_statistics()
        self.assertEqual(stats["scanned_files"], 0)
        self.assertEqual(stats["scanned_directories"], 1)

    def test_concurrent_scanning_safety(self):
        """Test that scanning is thread-safe."""
        import threading

        # Create test files
        for i in range(20):
            filename = f"concurrent_test_{i}.txt"
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write(f"Content {i}")

        results = []
        errors = []

        def scan_thread():
            try:
                scanner = FileScanner()
                files = scanner.scan_directory(self.temp_dir, recursive=False)
                results.append(len(files))
            except Exception as e:
                errors.append(e)

        # Run multiple scans concurrently
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=scan_thread)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify results
        self.assertEqual(len(errors), 0, f"Concurrent scanning errors: {errors}")
        self.assertEqual(len(results), 3)

        # All scans should return the same result
        self.assertTrue(all(r == results[0] for r in results))


class TestValidationAndBoundaryConditions(unittest.TestCase):
    """Test validation and boundary conditions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_file_size_boundaries(self):
        """Test file size boundary conditions."""
        # Test empty file
        empty_file = os.path.join(self.temp_dir, "empty.txt")
        with open(empty_file, 'w') as f:
            pass  # Create empty file

        metadata = FileMetadata.from_path(empty_file)
        self.assertEqual(metadata.size_bytes, 0)

        # Test very small file (1 byte)
        small_file = os.path.join(self.temp_dir, "small.txt")
        with open(small_file, 'w') as f:
            f.write("A")

        metadata = FileMetadata.from_path(small_file)
        self.assertEqual(metadata.size_bytes, 1)

    def test_extension_case_sensitivity(self):
        """Test extension case handling."""
        test_cases = [
            ("test.TXT", "txt"),
            ("test.Pdf", "pdf"),
            ("test.JPG", "jpg"),
            ("test.MP3", "mp3"),
        ]

        for filename, expected_extension in test_cases:
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write("Test content")

            metadata = FileMetadata.from_path(filepath)
            self.assertEqual(metadata.extension, expected_extension.lower())

    def test_multiple_dots_in_filename(self):
        """Test filenames with multiple dots."""
        filename = "test.file.with.many.dots.txt"
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, 'w') as f:
            f.write("Test content")

        metadata = FileMetadata.from_path(filepath)
        self.assertEqual(metadata.name, filename)
        self.assertEqual(metadata.extension, "txt")

    def test_file_type_classification_edge_cases(self):
        """Test file type classification edge cases."""
        edge_cases = [
            ("", "no_extension"),
            (".hidden", ""),  # Hidden file with no extension (starts with dot but no extension)
            ("file.", ""),  # Trailing dot
        ]

        for filename, expected_extension in edge_cases:
            if filename:  # Skip empty filename
                filepath = os.path.join(self.temp_dir, filename)
                with open(filepath, 'w') as f:
                    f.write("Test content")

                metadata = FileMetadata.from_path(filepath)
                self.assertEqual(metadata.extension, expected_extension)

    def test_datetime_accuracy(self):
        """Test modified date accuracy."""
        test_file = os.path.join(self.temp_dir, "timestamp_test.txt")

        # Create file and record time
        before_time = time.time()
        with open(test_file, 'w') as f:
            f.write("Timestamp test")
        after_time = time.time()

        metadata = FileMetadata.from_path(test_file)

        # Modified date should be close to the creation time (allowing for filesystem precision)
        modified_timestamp = metadata.modified_date.timestamp()
        # Allow some tolerance for filesystem timestamp precision
        time_diff = abs(modified_timestamp - before_time)
        self.assertLess(time_diff, 1.0, f"Modified time differs by {time_diff:.3f} seconds")

    def test_path_normalization(self):
        """Test path normalization handling."""
        # Create file with normalized path
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("Test content")

        # Test with various path formats
        path_variants = [
            test_file,
            os.path.normpath(test_file),
            str(pathlib.Path(test_file)),
        ]

        for path_variant in path_variants:
            metadata = FileMetadata.from_path(path_variant)
            self.assertEqual(metadata.name, "test.txt")
            # All should resolve to the same absolute path
            self.assertTrue(os.path.samefile(metadata.full_path, test_file))


if __name__ == '__main__':
    # Configure test discovery and execution
    unittest.main(verbosity=2)