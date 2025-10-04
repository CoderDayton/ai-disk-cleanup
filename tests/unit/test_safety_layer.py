"""
Comprehensive test suite for the Safety Layer protection rules and safety mechanisms.

This test suite validates:
- Protection rule enforcement for system files, recent files, and large files
- Safety score calculation accuracy and confidence threshold application
- User-defined protection paths and custom protection rules
- Edge cases and boundary conditions
- Audit trail logging for safety decisions

Safety Requirements:
- Zero data loss incidents
- 99% undo success rate
- Multi-layer protection architecture
- Confidence scoring and threshold validation
"""

import pytest
import os
import tempfile
import shutil
import time
import gc
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import logging

# Import the safety layer components
from src.ai_disk_cleanup.safety_layer import SafetyLayer, ProtectionRule, SafetyScore, ProtectionLevel
from src.ai_disk_cleanup.audit_trail import AuditTrail, SafetyDecision


class TestProtectionRuleEnforcement:
    """Test suite for protection rule enforcement mechanisms."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.safety_layer = SafetyLayer()
        self.audit_trail = AuditTrail()

    def teardown_method(self):
        """Clean up after each test method."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_system_files_protection_windows(self):
        """Test that Windows system files are automatically protected."""
        system_paths = [
            "C:/Windows/System32/kernel32.dll",
            "C:/Windows/System32/drivers/etc/hosts",
            "C:/Program Files/Common Files",
            "C:/Windows/bootmgr"
        ]

        for path in system_paths:
            protection_level = self.safety_layer.evaluate_protection_level(path)
            assert protection_level == ProtectionLevel.CRITICAL, f"System file {path} should have CRITICAL protection"
            assert self.safety_layer.is_protected(path), f"System file {path} should be protected"

    def test_system_files_protection_macos(self):
        """Test that macOS system files are automatically protected."""
        system_paths = [
            "/System/Library/Kernels/kernel",
            "/System/Library/Extensions",
            "/Library/Preferences/SystemConfiguration",
            "/usr/bin/ls"
        ]

        for path in system_paths:
            protection_level = self.safety_layer.evaluate_protection_level(path)
            assert protection_level == ProtectionLevel.CRITICAL, f"System file {path} should have CRITICAL protection"
            assert self.safety_layer.is_protected(path), f"System file {path} should be protected"

    def test_system_files_protection_linux(self):
        """Test that Linux system files are automatically protected."""
        system_paths = [
            "/bin/bash",
            "/usr/bin/python3",
            "/etc/passwd",
            "/lib/x86_64-linux-gnu/libc.so.6",
            "/boot/vmlinuz"
        ]

        for path in system_paths:
            protection_level = self.safety_layer.evaluate_protection_level(path)
            assert protection_level == ProtectionLevel.CRITICAL, f"System file {path} should have CRITICAL protection"
            assert self.safety_layer.is_protected(path), f"System file {path} should be protected"

    def test_recent_files_protection(self):
        """Test that recent files (<30 days) require manual review."""
        # Create test files with different ages
        recent_file = os.path.join(self.temp_dir, "recent_file.txt")
        old_file = os.path.join(self.temp_dir, "old_file.txt")

        # Create recent file (current time)
        Path(recent_file).touch()

        # Create old file (45 days ago)
        old_time = datetime.now() - timedelta(days=45)
        Path(old_file).touch()
        os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))

        # Test recent file protection
        recent_protection = self.safety_layer.evaluate_protection_level(recent_file)
        assert recent_protection == ProtectionLevel.REQUIRES_REVIEW, "Recent files should require manual review"
        assert self.safety_layer.requires_manual_review(recent_file), "Recent files should require manual review"

        # Test old file protection
        old_protection = self.safety_layer.evaluate_protection_level(old_file)
        assert old_protection != ProtectionLevel.REQUIRES_REVIEW, "Old files should not require manual review"

    def test_large_files_protection(self):
        """Test that large files (>1GB) require explicit confirmation."""
        # Mock file sizes for testing
        with patch('os.path.getsize') as mock_getsize:
            # Test large file (>1GB)
            mock_getsize.return_value = 2 * 1024 * 1024 * 1024  # 2GB
            large_file = "/tmp/large_file.iso"

            protection_level = self.safety_layer.evaluate_protection_level(large_file)
            assert protection_level == ProtectionLevel.REQUIRES_CONFIRMATION, "Large files should require explicit confirmation"
            assert self.safety_layer.requires_explicit_confirmation(large_file), "Large files should require explicit confirmation"

            # Test normal file (<1GB)
            mock_getsize.return_value = 500 * 1024 * 1024  # 500MB
            normal_file = "/tmp/normal_file.txt"

            protection_level = self.safety_layer.evaluate_protection_level(normal_file)
            assert protection_level != ProtectionLevel.REQUIRES_CONFIRMATION, "Normal files should not require explicit confirmation"

    def test_user_defined_protection_paths(self):
        """Test user-defined protected directories and files."""
        # Add custom protection paths
        custom_paths = [
            "/home/user/Documents",
            "/home/user/Photos",
            "/var/www/html"
        ]

        for path in custom_paths:
            self.safety_layer.add_user_protection_path(path)

        # Test protection of user-defined paths
        test_file = os.path.join(custom_paths[0], "important_document.txt")
        assert self.safety_layer.is_user_protected(test_file), "User-defined paths should be protected"

        protection_level = self.safety_layer.evaluate_protection_level(test_file)
        assert protection_level in [ProtectionLevel.HIGH, ProtectionLevel.CRITICAL], "User-protected files should have high protection"

    def test_protection_rule_precedence(self):
        """Test that protection rules are applied in correct precedence order."""
        # Create a file that matches multiple protection rules
        # System file should take precedence over other rules
        system_file = "/usr/bin/python3"

        with patch('os.path.getsize') as mock_getsize:
            # Make it a large file too
            mock_getsize.return_value = 2 * 1024 * 1024 * 1024

            protection_level = self.safety_layer.evaluate_protection_level(system_file)
            assert protection_level == ProtectionLevel.CRITICAL, "System file protection should take precedence over large file protection"

    def test_nested_protection_paths(self):
        """Test protection in nested directory structures."""
        parent_dir = "/home/user/Projects"
        child_dir = os.path.join(parent_dir, "ImportantProject")
        grandchild_file = os.path.join(child_dir, "critical_data.txt")

        self.safety_layer.add_user_protection_path(parent_dir)

        assert self.safety_layer.is_user_protected(grandchild_file), "Nested files should inherit parent protection"
        assert self.safety_layer.is_user_protected(child_dir), "Child directories should inherit parent protection"


class TestSafetyScoreCalculation:
    """Test suite for safety score calculation accuracy."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.safety_layer = SafetyLayer()

    def test_safety_score_critical_file(self):
        """Test safety score calculation for critical system files."""
        system_file = "/bin/bash"
        score = self.safety_layer.calculate_safety_score(system_file)

        assert score.confidence >= 0.95, "Critical files should have confidence >= 95%"
        assert score.protection_level == ProtectionLevel.CRITICAL, "Critical files should be marked as CRITICAL"
        assert score.risk_score <= 0.1, "Critical files should have very low risk score"
        assert not score.can_auto_delete, "Critical files should not be auto-deletable"

    def test_safety_score_recent_file(self):
        """Test safety score calculation for recent files."""
        recent_file = "/tmp/recent_document.txt"

        with patch('os.path.getmtime') as mock_mtime:
            # Set modification time to 5 days ago
            recent_time = datetime.now() - timedelta(days=5)
            mock_mtime.return_value = recent_time.timestamp()

            score = self.safety_layer.calculate_safety_score(recent_file)

            assert 0.3 <= score.confidence <= 0.7, "Recent files should have moderate confidence"
            assert score.protection_level == ProtectionLevel.REQUIRES_REVIEW, "Recent files should require review"
            assert 0.4 <= score.risk_score <= 0.7, "Recent files should have moderate risk"
            assert not score.can_auto_delete, "Recent files should not be auto-deletable"

    def test_safety_score_large_file(self):
        """Test safety score calculation for large files."""
        large_file = "/tmp/large_backup.tar"

        with patch('os.path.getsize') as mock_getsize:
            mock_getsize.return_value = 2 * 1024 * 1024 * 1024  # 2GB

            score = self.safety_layer.calculate_safety_score(large_file)

            assert 0.4 <= score.confidence <= 0.8, "Large files should have moderate-high confidence"
            assert score.protection_level == ProtectionLevel.REQUIRES_CONFIRMATION, "Large files should require confirmation"
            assert 0.3 <= score.risk_score <= 0.6, "Large files should have moderate risk"
            assert not score.can_auto_delete, "Large files should not be auto-deletable"

    def test_safety_score_safe_file(self):
        """Test safety score calculation for safe-to-delete files."""
        safe_file = "/tmp/old_cache_file.tmp"

        with patch('os.path.getmtime') as mock_mtime, \
             patch('os.path.getsize') as mock_getsize:

            # Set file as old and small
            old_time = datetime.now() - timedelta(days=90)
            mock_mtime.return_value = old_time.timestamp()
            mock_getsize.return_value = 1024 * 1024  # 1MB

            score = self.safety_layer.calculate_safety_score(safe_file)

            assert score.confidence >= 0.8, "Safe files should have high confidence"
            assert score.protection_level == ProtectionLevel.SAFE, "Safe files should be marked as SAFE"
            assert score.risk_score <= 0.2, "Safe files should have low risk"
            assert score.can_auto_delete, "Safe files should be auto-deletable"

    def test_safety_score_user_protected_file(self):
        """Test safety score calculation for user-protected files."""
        user_protected_file = "/home/user/Documents/important.txt"

        self.safety_layer.add_user_protection_path("/home/user/Documents")

        score = self.safety_layer.calculate_safety_score(user_protected_file)

        assert score.confidence >= 0.9, "User-protected files should have high confidence"
        assert score.protection_level in [ProtectionLevel.HIGH, ProtectionLevel.CRITICAL], "User-protected files should have high protection"
        assert score.risk_score <= 0.15, "User-protected files should have low risk"
        assert not score.can_auto_delete, "User-protected files should not be auto-deletable"

    def test_safety_score_edge_cases(self):
        """Test safety score calculation for edge cases."""
        # Test non-existent file
        with pytest.raises(FileNotFoundError):
            self.safety_layer.calculate_safety_score("/non/existent/file.txt")

        # Test empty file
        empty_file = "/tmp/empty_file.txt"
        Path(empty_file).touch()

        score = self.safety_layer.calculate_safety_score(empty_file)
        assert isinstance(score, SafetyScore), "Empty files should return valid safety score"

    def test_safety_score_confidence_threshold(self):
        """Test confidence threshold application."""
        # Test with default threshold (0.8)
        self.safety_layer.set_confidence_threshold(0.8)

        safe_file = "/tmp/safe_file.txt"
        with patch('os.path.getmtime') as mock_mtime, \
             patch('os.path.getsize') as mock_getsize:

            # Set file as old and small
            old_time = datetime.now() - timedelta(days=90)
            mock_mtime.return_value = old_time.timestamp()
            mock_getsize.return_value = 1024 * 1024  # 1MB

            score = self.safety_layer.calculate_safety_score(safe_file)

            # Should be above threshold
            assert score.confidence >= 0.8, "Safe file should meet confidence threshold"
            assert self.safety_layer.meets_confidence_threshold(score), "Safe file should meet confidence threshold"

        # Test with high threshold (0.95)
        self.safety_layer.set_confidence_threshold(0.95)

        # Most files should not meet this threshold
        assert not self.safety_layer.meets_confidence_threshold(score), "Most files should not meet 95% threshold"

    def test_safety_score_factors(self):
        """Test individual factors that contribute to safety score."""
        test_file = "/tmp/test_file.txt"

        # Test file age factor
        age_factor = self.safety_layer.calculate_age_factor(test_file)
        assert 0 <= age_factor <= 1, "Age factor should be between 0 and 1"

        # Test file size factor
        with patch('os.path.getsize') as mock_getsize:
            mock_getsize.return_value = 100 * 1024 * 1024  # 100MB
            size_factor = self.safety_layer.calculate_size_factor(test_file)
            assert 0 <= size_factor <= 1, "Size factor should be between 0 and 1"

        # Test file extension factor
        ext_factor = self.safety_layer.calculate_extension_factor(test_file)
        assert 0 <= ext_factor <= 1, "Extension factor should be between 0 and 1"

        # Test location factor
        location_factor = self.safety_layer.calculate_location_factor(test_file)
        assert 0 <= location_factor <= 1, "Location factor should be between 0 and 1"


class TestConfidenceThresholdApplication:
    """Test suite for confidence threshold application and validation."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.safety_layer = SafetyLayer()

    def test_default_confidence_threshold(self):
        """Test default confidence threshold setting."""
        default_threshold = self.safety_layer.get_confidence_threshold()
        assert default_threshold == 0.8, "Default confidence threshold should be 0.8"

    def test_custom_confidence_threshold(self):
        """Test setting custom confidence thresholds."""
        custom_thresholds = [0.5, 0.7, 0.9, 0.95]

        for threshold in custom_thresholds:
            self.safety_layer.set_confidence_threshold(threshold)
            assert self.safety_layer.get_confidence_threshold() == threshold, f"Threshold should be set to {threshold}"

    def test_invalid_confidence_thresholds(self):
        """Test handling of invalid confidence thresholds."""
        # Test threshold below 0
        with pytest.raises(ValueError):
            self.safety_layer.set_confidence_threshold(-0.1)

        # Test threshold above 1
        with pytest.raises(ValueError):
            self.safety_layer.set_confidence_threshold(1.1)

        # Test threshold of exactly 0 (should be invalid)
        with pytest.raises(ValueError):
            self.safety_layer.set_confidence_threshold(0)

        # Test threshold of exactly 1 (should be invalid)
        with pytest.raises(ValueError):
            self.safety_layer.set_confidence_threshold(1)

    def test_threshold_impact_on_deletion_decisions(self):
        """Test how confidence thresholds impact deletion decisions."""
        test_file = "/tmp/test_file.txt"

        # Create a safety score with known confidence
        score = SafetyScore(
            confidence=0.85,
            risk_score=0.2,
            protection_level=ProtectionLevel.SAFE,
            can_auto_delete=True
        )

        # Test with threshold below score confidence
        self.safety_layer.set_confidence_threshold(0.8)
        assert self.safety_layer.can_auto_delete_with_threshold(score), "Should allow auto-deletion when confidence > threshold"

        # Test with threshold above score confidence
        self.safety_layer.set_confidence_threshold(0.9)
        assert not self.safety_layer.can_auto_delete_with_threshold(score), "Should not allow auto-deletion when confidence < threshold"

    def test_adaptive_confidence_threshold(self):
        """Test adaptive confidence threshold based on file characteristics."""
        # Test adaptive threshold for system files
        system_file = "/bin/bash"
        adaptive_threshold = self.safety_layer.get_adaptive_confidence_threshold(system_file)
        assert adaptive_threshold >= 0.95, "System files should have very high adaptive threshold"

        # Test adaptive threshold for temporary files
        temp_file = "/tmp/temp_cache.tmp"
        adaptive_threshold = self.safety_layer.get_adaptive_confidence_threshold(temp_file)
        assert adaptive_threshold <= 0.7, "Temporary files should have lower adaptive threshold"

    def test_threshold_logging(self):
        """Test that threshold applications are properly logged."""
        with patch.object(self.safety_layer.audit_trail, 'log_threshold_application') as mock_log:
            score = SafetyScore(
                confidence=0.85,
                risk_score=0.2,
                protection_level=ProtectionLevel.SAFE,
                can_auto_delete=True
            )

            self.safety_layer.set_confidence_threshold(0.8)
            decision = self.safety_layer.evaluate_deletion_decision("/tmp/test.txt", score)

            mock_log.assert_called_once()
            call_args = mock_log.call_args[1]
            assert call_args['file_path'] == "/tmp/test.txt"
            assert call_args['confidence'] == 0.85
            assert call_args['threshold'] == 0.8
            assert call_args['decision'] == decision


class TestUserDefinedProtectionPaths:
    """Test suite for user-defined protection paths functionality."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.safety_layer = SafetyLayer()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up after each test method."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_add_single_protection_path(self):
        """Test adding a single protection path."""
        protection_path = "/home/user/Documents"

        self.safety_layer.add_user_protection_path(protection_path)

        assert self.safety_layer.is_user_protected(protection_path), "Added path should be protected"
        assert protection_path in self.safety_layer.get_user_protection_paths(), "Path should be in protection list"

    def test_add_multiple_protection_paths(self):
        """Test adding multiple protection paths."""
        protection_paths = [
            "/home/user/Documents",
            "/home/user/Photos",
            "/var/www/html"
        ]

        for path in protection_paths:
            self.safety_layer.add_user_protection_path(path)

        for path in protection_paths:
            assert self.safety_layer.is_user_protected(path), f"Path {path} should be protected"

        assert len(self.safety_layer.get_user_protection_paths()) == len(protection_paths), "All paths should be added"

    def test_remove_protection_path(self):
        """Test removing protection paths."""
        protection_path = "/home/user/Documents"

        # Add path
        self.safety_layer.add_user_protection_path(protection_path)
        assert self.safety_layer.is_user_protected(protection_path), "Path should initially be protected"

        # Remove path
        self.safety_layer.remove_user_protection_path(protection_path)
        assert not self.safety_layer.is_user_protected(protection_path), "Path should not be protected after removal"
        assert protection_path not in self.safety_layer.get_user_protection_paths(), "Path should be removed from protection list"

    def test_nested_path_protection(self):
        """Test protection of nested paths within parent protection."""
        parent_path = "/home/user/Projects"

        # Create nested test structure
        child_path = os.path.join(parent_path, "ImportantProject")
        grandchild_file = os.path.join(child_path, "data.txt")

        self.safety_layer.add_user_protection_path(parent_path)

        # Test that nested paths are protected
        assert self.safety_layer.is_user_protected(child_path), "Child path should be protected"
        assert self.safety_layer.is_user_protected(grandchild_file), "Grandchild file should be protected"

    def test_overlap_protection_paths(self):
        """Test handling of overlapping protection paths."""
        parent_path = "/home/user/Projects"
        child_path = "/home/user/Projects/Important"

        # Add both parent and child paths
        self.safety_layer.add_user_protection_path(parent_path)
        self.safety_layer.add_user_protection_path(child_path)

        # Both should be protected
        assert self.safety_layer.is_user_protected(parent_path), "Parent path should be protected"
        assert self.safety_layer.is_user_protected(child_path), "Child path should be protected"

        # Should not duplicate in protection list
        protection_paths = self.safety_layer.get_user_protection_paths()
        assert len(protection_paths) == 2, "Should not duplicate overlapping paths"

    def test_invalid_protection_paths(self):
        """Test handling of invalid protection paths."""
        # Test empty path
        with pytest.raises(ValueError):
            self.safety_layer.add_user_protection_path("")

        # Test None path
        with pytest.raises(ValueError):
            self.safety_layer.add_user_protection_path(None)

        # Test relative path (should be converted to absolute)
        relative_path = "Documents"
        self.safety_layer.add_user_protection_path(relative_path)

        # Should be converted to absolute path
        protection_paths = self.safety_layer.get_user_protection_paths()
        assert any(path.endswith(relative_path) for path in protection_paths), "Relative path should be converted to absolute"

    def test_persistent_protection_paths(self):
        """Test that protection paths are persisted across sessions."""
        protection_path = "/home/user/ImportantData"

        # Add protection path
        self.safety_layer.add_user_protection_path(protection_path)

        # Save configuration
        self.safety_layer.save_protection_config()

        # Create new safety layer instance
        new_safety_layer = SafetyLayer()
        new_safety_layer.load_protection_config()

        assert new_safety_layer.is_user_protected(protection_path), "Protection paths should persist across sessions"

    def test_protection_path_validation(self):
        """Test validation of protection paths."""
        # Test non-existent path (should still be allowed for future protection)
        non_existent_path = "/tmp/future_project"
        self.safety_layer.add_user_protection_path(non_existent_path)
        assert self.safety_layer.is_user_protected(non_existent_path), "Non-existent paths should be allowed"

        # Test path with special characters
        special_path = "/home/user/My Project (2023)"
        self.safety_layer.add_user_protection_path(special_path)
        assert self.safety_layer.is_user_protected(special_path), "Paths with special characters should be allowed"


class TestEdgeCasesAndBoundaryConditions:
    """Test suite for edge cases and boundary conditions."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.safety_layer = SafetyLayer()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up after each test method."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_file_age_boundary_conditions(self):
        """Test boundary conditions for file age protection."""
        # Create test files at different ages
        boundary_file = os.path.join(self.temp_dir, "boundary_file.txt")
        Path(boundary_file).touch()

        # Test exactly 30 days old (boundary)
        boundary_time = datetime.now() - timedelta(days=30)
        os.utime(boundary_file, (boundary_time.timestamp(), boundary_time.timestamp()))

        protection_level = self.safety_layer.evaluate_protection_level(boundary_file)
        assert protection_level == ProtectionLevel.REQUIRES_REVIEW, "Files exactly 30 days old should require review"

        # Test 31 days old (just over boundary)
        old_boundary_file = os.path.join(self.temp_dir, "old_boundary_file.txt")
        Path(old_boundary_file).touch()

        old_boundary_time = datetime.now() - timedelta(days=31)
        os.utime(old_boundary_file, (old_boundary_time.timestamp(), old_boundary_time.timestamp()))

        protection_level = self.safety_layer.evaluate_protection_level(old_boundary_file)
        assert protection_level != ProtectionLevel.REQUIRES_REVIEW, "Files 31+ days old should not require review"

    def test_file_size_boundary_conditions(self):
        """Test boundary conditions for file size protection."""
        # Test exactly 1GB file (boundary)
        with patch('os.path.getsize') as mock_getsize:
            exact_boundary_file = "/tmp/exactly_1gb_file.iso"
            mock_getsize.return_value = 1024 * 1024 * 1024  # Exactly 1GB

            protection_level = self.safety_layer.evaluate_protection_level(exact_boundary_file)
            assert protection_level == ProtectionLevel.REQUIRES_CONFIRMATION, "Files exactly 1GB should require confirmation"

            # Test just under 1GB
            just_under_file = "/tmp/just_under_1gb_file.iso"
            mock_getsize.return_value = (1024 * 1024 * 1024) - 1  # 1GB - 1 byte

            protection_level = self.safety_layer.evaluate_protection_level(just_under_file)
            assert protection_level != ProtectionLevel.REQUIRES_CONFIRMATION, "Files just under 1GB should not require confirmation"

    def test_zero_size_file(self):
        """Test handling of zero-size files."""
        zero_size_file = os.path.join(self.temp_dir, "empty_file.txt")
        Path(zero_size_file).touch()

        # Should not raise exception
        score = self.safety_layer.calculate_safety_score(zero_size_file)
        assert isinstance(score, SafetyScore), "Zero-size files should return valid safety score"

        protection_level = self.safety_layer.evaluate_protection_level(zero_size_file)
        assert isinstance(protection_level, ProtectionLevel), "Zero-size files should have valid protection level"

    def test_very_large_file(self):
        """Test handling of very large files."""
        huge_file = "/tmp/huge_file.img"

        with patch('os.path.getsize') as mock_getsize:
            # Test 100GB file
            mock_getsize.return_value = 100 * 1024 * 1024 * 1024  # 100GB

            score = self.safety_layer.calculate_safety_score(huge_file)
            assert isinstance(score, SafetyScore), "Very large files should return valid safety score"
            assert score.protection_level == ProtectionLevel.REQUIRES_CONFIRMATION, "Very large files should require confirmation"
            assert not score.can_auto_delete, "Very large files should not be auto-deletable"

    def test_file_with_special_characters(self):
        """Test files with special characters in names."""
        special_files = [
            "/tmp/file with spaces.txt",
            "/tmp/file-with-dashes.txt",
            "/tmp/file_with_underscores.txt",
            "/tmp/file.with.dots.txt",
            "/tmp/file(with)parentheses.txt",
            "/tmp/file[with]brackets.txt",
            "/tmp/file'with'quotes.txt",
            "/tmp/file\"with\"doublequotes.txt",
            "/tmp/文件名中文.txt",
            "/tmp/файлрусский.txt"
        ]

        for file_path in special_files:
            with patch('os.path.exists', return_value=True):
                try:
                    score = self.safety_layer.calculate_safety_score(file_path)
                    assert isinstance(score, SafetyScore), f"File {file_path} should return valid safety score"
                except Exception as e:
                    pytest.fail(f"Failed to process file {file_path}: {e}")

    def test_symlink_handling(self):
        """Test handling of symbolic links."""
        # Create target file
        target_file = os.path.join(self.temp_dir, "target.txt")
        Path(target_file).touch()

        # Create symlink
        symlink_file = os.path.join(self.temp_dir, "symlink.txt")
        os.symlink(target_file, symlink_file)

        # Test that symlinks are handled properly
        score = self.safety_layer.calculate_safety_score(symlink_file)
        assert isinstance(score, SafetyScore), "Symlinks should return valid safety score"

        # Test broken symlink
        broken_symlink = os.path.join(self.temp_dir, "broken_symlink.txt")
        os.symlink("/non/existent/file", broken_symlink)

        # Should handle broken symlink gracefully
        with pytest.raises(FileNotFoundError):
            self.safety_layer.calculate_safety_score(broken_symlink)

    def test_permission_denied_files(self):
        """Test handling of files with permission denied."""
        restricted_file = "/root/.ssh/private_key"

        with patch('os.path.getsize', side_effect=PermissionError("Permission denied")):
            # The safety layer should handle permission errors gracefully
            # and return a safety score rather than raising an exception
            score = self.safety_layer.calculate_safety_score(restricted_file)
            assert score is not None, "Should return a safety score even for permission denied files"
            # System files like /root/.ssh/private_key get the highest protection level
            assert score.protection_level == ProtectionLevel.CRITICAL, "System files should be critical even with permission errors"
            assert score.confidence >= 0.95, "System files should have very high confidence"
            assert not score.can_auto_delete, "System files should never be auto-deletable"

    def test_concurrent_access_safety(self):
        """Test safety layer behavior under concurrent access."""
        import threading
        import time

        results = []
        errors = []

        def test_safety_calculation(file_path):
            try:
                for _ in range(10):
                    score = self.safety_layer.calculate_safety_score(file_path)
                    results.append(score)
                    time.sleep(0.001)  # Small delay
            except Exception as e:
                errors.append(e)

        # Test file
        test_file = os.path.join(self.temp_dir, "concurrent_test.txt")
        Path(test_file).touch()

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=test_safety_calculation, args=(test_file,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"No errors should occur during concurrent access: {errors}"
        assert len(results) == 50, "All calculations should complete successfully"

    def test_memory_efficiency_large_directory(self):
        """Test memory efficiency when processing large directories."""
        # Mock large directory with many files
        large_dir = "/tmp/large_directory"

        with patch('os.listdir') as mock_listdir, \
             patch('os.path.join') as mock_join, \
             patch('os.path.exists', return_value=True):

            # Simulate 10,000 files
            mock_files = [f"file_{i}.txt" for i in range(10000)]
            mock_listdir.return_value = mock_files

            # Test that processing doesn't consume excessive memory
            import psutil
            import gc

            process = psutil.Process()
            memory_before = process.memory_info().rss

            # Process all files
            scores = []
            for file_name in mock_files:
                file_path = f"{large_dir}/{file_name}"
                with patch('os.path.getsize', return_value=1024), \
                     patch('os.path.getmtime', return_value=time.time() - 86400 * 30):  # 30 days old
                    score = self.safety_layer.calculate_safety_score(file_path)
                    scores.append(score)

            # Force garbage collection
            gc.collect()

            memory_after = process.memory_info().rss
            memory_increase = memory_after - memory_before

            # Memory increase should be reasonable (less than 100MB)
            assert memory_increase < 100 * 1024 * 1024, f"Memory increase should be reasonable: {memory_increase / 1024 / 1024:.2f}MB"
            assert len(scores) == 10000, "All files should be processed"


class TestAuditTrailLogging:
    """Test suite for audit trail logging of safety decisions."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.audit_trail = AuditTrail()
        # Clear any existing logs to ensure test isolation
        self.audit_trail.clear_logs()
        self.safety_layer = SafetyLayer(audit_trail=self.audit_trail)
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up after each test method."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_safety_decision_logging(self):
        """Test that safety decisions are properly logged."""
        file_path = "/tmp/test_file.txt"
        decision = SafetyDecision.PROTECTED
        reason = "System file protection"
        confidence = 0.95

        # Log safety decision
        self.audit_trail.log_safety_decision(
            file_path=file_path,
            decision=decision,
            reason=reason,
            confidence=confidence
        )

        # Verify log entry
        logs = self.audit_trail.get_recent_logs(limit=1)
        assert len(logs) == 1, "Should have one log entry"

        log_entry = logs[0]
        assert log_entry.file_path == file_path, "Log entry should contain correct file path"
        assert log_entry.decision == decision, "Log entry should contain correct decision"
        assert log_entry.reason == reason, "Log entry should contain correct reason"
        assert log_entry.confidence == confidence, "Log entry should contain correct confidence"
        assert log_entry.timestamp is not None, "Log entry should contain timestamp"

    def test_protection_rule_enforcement_logging(self):
        """Test logging of protection rule enforcement."""
        system_file = "/bin/bash"

        # Evaluate protection level (should trigger logging)
        protection_level = self.safety_layer.evaluate_protection_level(system_file)

        # Verify audit log entry
        recent_logs = self.audit_trail.get_recent_logs(limit=10)
        protection_logs = [log for log in recent_logs if log.file_path == system_file]

        assert len(protection_logs) > 0, "Protection evaluation should be logged"

        protection_log = protection_logs[0]
        assert protection_log.decision == SafetyDecision.PROTECTED, "System file should be logged as protected"
        assert "system file" in protection_log.reason.lower(), "Reason should mention system file protection"

    def test_confidence_threshold_logging(self):
        """Test logging of confidence threshold applications."""
        test_file = "/tmp/test_file.txt"
        score = SafetyScore(
            confidence=0.85,
            risk_score=0.2,
            protection_level=ProtectionLevel.SAFE,
            can_auto_delete=True
        )

        self.safety_layer.set_confidence_threshold(0.8)
        decision = self.safety_layer.evaluate_deletion_decision(test_file, score)

        # Verify threshold application was logged
        recent_logs = self.audit_trail.get_recent_logs(limit=10)
        threshold_logs = [log for log in recent_logs if "threshold" in log.reason.lower()]

        assert len(threshold_logs) > 0, "Threshold application should be logged"

    def test_user_action_logging(self):
        """Test logging of user actions and decisions."""
        file_path = "/tmp/user_selected_file.txt"
        user_action = "MANUAL_REVIEW_APPROVED"
        user_comment = "User confirmed safe to delete"

        # Log user action
        self.audit_trail.log_user_action(
            file_path=file_path,
            action=user_action,
            comment=user_comment
        )

        # Verify log entry
        logs = self.audit_trail.get_recent_logs(limit=1)
        assert len(logs) == 1, "Should have one log entry"

        log_entry = logs[0]
        assert log_entry.file_path == file_path, "Log entry should contain correct file path"
        assert log_entry.user_action == user_action, "Log entry should contain user action"
        assert log_entry.user_comment == user_comment, "Log entry should contain user comment"

    def test_error_logging(self):
        """Test logging of errors and exceptions."""
        file_path = "/tmp/problematic_file.txt"
        error_message = "Permission denied accessing file"
        error_type = "PermissionError"

        # Log error
        self.audit_trail.log_error(
            file_path=file_path,
            error_type=error_type,
            error_message=error_message
        )

        # Verify log entry
        logs = self.audit_trail.get_recent_logs(limit=1)
        assert len(logs) == 1, "Should have one log entry"

        log_entry = logs[0]
        assert log_entry.file_path == file_path, "Log entry should contain correct file path"
        assert log_entry.error_type == error_type, "Log entry should contain error type"
        assert log_entry.error_message == error_message, "Log entry should contain error message"

    def test_audit_log_persistence(self):
        """Test that audit logs are persisted to disk."""
        # Create multiple log entries
        for i in range(10):
            self.audit_trail.log_safety_decision(
                file_path=f"/tmp/test_file_{i}.txt",
                decision=SafetyDecision.PROTECTED,
                reason=f"Test protection {i}",
                confidence=0.9
            )

        # Save logs
        self.audit_trail.save_logs()

        # Create new audit trail instance
        new_audit_trail = AuditTrail()
        new_audit_trail.load_logs()

        # Verify logs were persisted
        all_logs = new_audit_trail.get_all_logs()
        assert len(all_logs) >= 10, "Logs should be persisted across sessions"

    def test_log_filtering_and_search(self):
        """Test filtering and searching of audit logs."""
        # Create various log entries
        test_files = [
            ("/tmp/system_file.txt", SafetyDecision.PROTECTED, "System file"),
            ("/tmp/user_file.txt", SafetyDecision.MANUAL_REVIEW, "User file"),
            ("/tmp/large_file.txt", SafetyDecision.REQUIRES_CONFIRMATION, "Large file"),
            ("/tmp/safe_file.txt", SafetyDecision.SAFE_TO_DELETE, "Safe file")
        ]

        for file_path, decision, reason in test_files:
            self.audit_trail.log_safety_decision(
                file_path=file_path,
                decision=decision,
                reason=reason,
                confidence=0.8
            )

        # Test filtering by decision
        protected_logs = self.audit_trail.filter_logs_by_decision(SafetyDecision.PROTECTED)
        assert len(protected_logs) == 1, "Should find one protected file"
        assert protected_logs[0].file_path == "/tmp/system_file.txt", "Should find correct protected file"

        # Test filtering by file pattern
        tmp_logs = self.audit_trail.filter_logs_by_file_pattern("/tmp/*")
        assert len(tmp_logs) == 4, "Should find all /tmp files"

        # Test filtering by time range
        recent_logs = self.audit_trail.filter_logs_by_time_range(
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now()
        )
        assert len(recent_logs) == 4, "Should find all recent logs"

    def test_log_integrity_verification(self):
        """Test audit log integrity verification."""
        # Create log entries
        for i in range(5):
            self.audit_trail.log_safety_decision(
                file_path=f"/tmp/integrity_test_{i}.txt",
                decision=SafetyDecision.PROTECTED,
                reason=f"Integrity test {i}",
                confidence=0.9
            )

        # Verify log integrity
        integrity_check = self.audit_trail.verify_integrity()
        assert integrity_check.is_valid, "Log integrity should be valid"
        assert integrity_check.entry_count == 5, "Should have correct number of entries"
        assert integrity_check.checksum is not None, "Should have valid checksum"

        # Simulate log tampering
        self.audit_trail.logs[0].file_path = "/tmp/tampered_file.txt"

        # Verify integrity check detects tampering
        integrity_check = self.audit_trail.verify_integrity()
        assert not integrity_check.is_valid, "Should detect log tampering"

    def test_performance_logging(self):
        """Test logging performance metrics."""
        import time

        # Log performance metrics
        start_time = time.time()

        # Simulate safety assessment
        score = self.safety_layer.calculate_safety_score("/tmp/performance_test.txt")

        end_time = time.time()
        processing_time = end_time - start_time

        # Log performance metrics
        self.audit_trail.log_performance_metrics(
            operation="safety_assessment",
            processing_time=processing_time,
            file_count=1,
            memory_usage="10MB"
        )

        # Verify performance log
        recent_logs = self.audit_trail.get_recent_logs(limit=1)
        assert len(recent_logs) == 1, "Should have one performance log"

        log_entry = recent_logs[0]
        assert log_entry.operation == "safety_assessment", "Should log correct operation"
        assert log_entry.processing_time == processing_time, "Should log correct processing time"
        assert log_entry.file_count == 1, "Should log correct file count"


class TestSafetyLayerIntegration:
    """Integration tests for the complete safety layer system."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.safety_layer = SafetyLayer()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up after each test method."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_end_to_end_safety_assessment(self):
        """Test complete safety assessment workflow."""
        # Create test file with known characteristics
        test_file = os.path.join(self.temp_dir, "integration_test.txt")
        Path(test_file).touch()

        # Set file properties
        old_time = datetime.now() - timedelta(days=60)
        os.utime(test_file, (old_time.timestamp(), old_time.timestamp()))

        # Perform complete safety assessment
        safety_assessment = self.safety_layer.perform_complete_safety_assessment(test_file)

        # Verify assessment results
        assert safety_assessment.file_path == test_file, "Assessment should include file path"
        assert isinstance(safety_assessment.safety_score, SafetyScore), "Should include safety score"
        assert isinstance(safety_assessment.protection_level, ProtectionLevel), "Should include protection level"
        assert safety_assessment.can_auto_delete is not None, "Should indicate auto-deletion eligibility"
        assert safety_assessment.audit_trail_entry is not None, "Should include audit trail entry"

    def test_batch_safety_assessment(self):
        """Test safety assessment for multiple files."""
        # Create multiple test files
        test_files = []
        for i in range(10):
            file_path = os.path.join(self.temp_dir, f"batch_test_{i}.txt")
            Path(file_path).touch()
            test_files.append(file_path)

        # Perform batch assessment
        batch_results = self.safety_layer.batch_safety_assessment(test_files)

        # Verify batch results
        assert len(batch_results) == len(test_files), "Should assess all files"

        for result in batch_results:
            assert isinstance(result.safety_score, SafetyScore), "Each result should have safety score"
            assert isinstance(result.protection_level, ProtectionLevel), "Each result should have protection level"
            assert result.file_path in test_files, "Each result should correspond to input file"

    def test_safety_layer_configuration(self):
        """Test safety layer configuration management."""
        # Configure safety layer
        config = {
            "confidence_threshold": 0.85,
            "protection_paths": ["/home/user/Documents", "/home/user/Photos"],
            "enable_audit_logging": True,
            "max_file_size_for_auto_delete": "100MB"
        }

        self.safety_layer.configure(config)

        # Verify configuration
        assert self.safety_layer.get_confidence_threshold() == 0.85, "Should set confidence threshold"
        assert len(self.safety_layer.get_user_protection_paths()) == 2, "Should set protection paths"
        assert self.safety_layer.is_audit_logging_enabled(), "Should enable audit logging"

        # Save and load configuration
        self.safety_layer.save_configuration()

        new_safety_layer = SafetyLayer()
        new_safety_layer.load_configuration()

        assert new_safety_layer.get_confidence_threshold() == 0.85, "Configuration should persist"
        assert len(new_safety_layer.get_user_protection_paths()) == 2, "Protection paths should persist"

    def test_safety_layer_error_recovery(self):
        """Test safety layer error recovery mechanisms."""
        # Test recovery from file system errors - safety layer should handle them gracefully
        problematic_file = "/root/inaccessible_file.txt"

        with patch('os.path.exists', side_effect=OSError("File system error")):
            # The safety layer should handle OSError gracefully and still return an assessment
            assessment = self.safety_layer.perform_complete_safety_assessment(problematic_file)
            assert assessment is not None, "Safety layer should handle file system errors gracefully"

        # Verify safety layer remains functional
        normal_file = os.path.join(self.temp_dir, "normal_file.txt")
        Path(normal_file).touch()

        assessment = self.safety_layer.perform_complete_safety_assessment(normal_file)
        assert assessment is not None, "Safety layer should recover and remain functional"

    def test_safety_layer_performance_under_load(self):
        """Test safety layer performance under heavy load."""
        import concurrent.futures
        import time

        # Create many test files
        test_files = []
        for i in range(100):
            file_path = os.path.join(self.temp_dir, f"load_test_{i}.txt")
            Path(file_path).touch()
            test_files.append(file_path)

        # Test concurrent assessment
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self.safety_layer.perform_complete_safety_assessment, file_path)
                      for file_path in test_files]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        end_time = time.time()
        processing_time = end_time - start_time

        # Verify performance
        assert len(results) == len(test_files), "Should process all files"
        assert processing_time < 10.0, f"Should complete processing in reasonable time: {processing_time:.2f}s"

        # Verify all results are valid
        for result in results:
            assert isinstance(result.safety_score, SafetyScore), "All results should have valid safety scores"

    def test_safety_layer_memory_management(self):
        """Test safety layer memory management."""
        import psutil
        import gc

        process = psutil.Process()
        memory_before = process.memory_info().rss

        # Process many files
        for i in range(1000):
            test_file = f"/tmp/memory_test_{i}.txt"
            with patch('os.path.exists', return_value=True):
                assessment = self.safety_layer.perform_complete_safety_assessment(test_file)

        # Force garbage collection
        gc.collect()

        memory_after = process.memory_info().rss
        memory_increase = memory_after - memory_before

        # Memory increase should be reasonable
        assert memory_increase < 50 * 1024 * 1024, f"Memory increase should be reasonable: {memory_increase / 1024 / 1024:.2f}MB"


# Test fixtures and utilities
@pytest.fixture
def safety_layer():
    """Create a SafetyLayer instance for testing."""
    return SafetyLayer()


@pytest.fixture
def audit_trail():
    """Create an AuditTrail instance for testing."""
    return AuditTrail()


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_files(temp_directory):
    """Create sample files for testing."""
    files = {}

    # Create files with different characteristics
    files['recent'] = os.path.join(temp_directory, "recent.txt")
    Path(files['recent']).touch()

    files['old'] = os.path.join(temp_directory, "old.txt")
    Path(files['old']).touch()
    old_time = datetime.now() - timedelta(days=60)
    os.utime(files['old'], (old_time.timestamp(), old_time.timestamp()))

    files['empty'] = os.path.join(temp_directory, "empty.txt")
    Path(files['empty']).touch()

    return files


# Pytest configuration and markers
pytest_plugins = []

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "safety_layer: Tests for safety layer functionality"
    )
    config.addinivalue_line(
        "markers", "protection_rules: Tests for protection rule enforcement"
    )
    config.addinivalue_line(
        "markers", "safety_score: Tests for safety score calculation"
    )
    config.addinivalue_line(
        "markers", "audit_trail: Tests for audit trail logging"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests for safety layer"
    )


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])