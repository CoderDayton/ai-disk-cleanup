"""
Integration tests for secure file operations with audit trail and OpenAI client.

This test suite validates that the security measures work correctly in real-world
scenarios with the actual application components.
"""

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.ai_disk_cleanup.audit_trail import AuditTrail, SafetyDecision
from src.ai_disk_cleanup.openai_client import OpenAIClient, FileMetadata, FileAnalysisResult
from src.ai_disk_cleanup.core.config_models import AppConfig
from src.ai_disk_cleanup.security.secure_file_ops import SecurityLevel


class TestAuditTrailSecurityIntegration(unittest.TestCase):
    """Test secure file operations integration with audit trail."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="audit_security_test_"))
        self.audit_file = self.test_dir / "test_audit.json"
        self.audit_trail = AuditTrail(str(self.audit_file))

    def tearDown(self):
        """Clean up test environment."""
        self.audit_trail.secure_ops.cleanup_temp_files()
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_audit_trail_secure_file_creation(self):
        """Test that audit trail creates files with secure permissions."""
        # Log some test entries
        self.audit_trail.log_safety_decision(
            "/test/file1.txt",
            SafetyDecision.SAFE_TO_DELETE,
            "Test file is safe to delete",
            0.95
        )

        self.audit_trail.log_safety_decision(
            "/test/protected_file.txt",
            SafetyDecision.PROTECTED,
            "Important system file",
            1.0
        )

        # Save logs
        self.audit_trail.save_logs()

        # Verify audit file exists
        self.assertTrue(self.audit_file.exists())

        # Verify file permissions (on Unix systems)
        if hasattr(self.audit_file, 'stat'):
            import os
            if not os.name == 'nt':  # Skip on Windows
                file_stat = self.audit_file.stat()
                permissions = file_stat.st_mode & 0o777
                # Should be 0o600 for sensitive audit logs
                self.assertEqual(permissions, 0o600)

        # Verify file contains expected data structure
        audit_data = self.audit_trail.secure_ops.read_json_secure(self.audit_file)
        self.assertIn("audit_logs", audit_data)
        self.assertIn("metadata", audit_data)
        self.assertEqual(len(audit_data["audit_logs"]), 2)

    def test_audit_trail_loads_legacy_format(self):
        """Test that audit trail can load legacy format files."""
        # Create a legacy format audit file
        legacy_data = [
            {
                "id": "test123",
                "file_path": "/legacy/file.txt",
                "decision": "safe_to_delete",
                "reason": "Legacy test file",
                "confidence": 0.8,
                "timestamp": datetime.now().isoformat()
            }
        ]

        with open(self.audit_file, 'w') as f:
            json.dump(legacy_data, f)

        # Create new audit trail that should load legacy data
        new_audit_trail = AuditTrail(str(self.audit_file))

        # Verify legacy data was loaded
        logs = new_audit_trail.get_all_logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].file_path, "/legacy/file.txt")
        self.assertEqual(logs[0].decision, SafetyDecision.SAFE_TO_DELETE)

    def test_audit_trail_export_security(self):
        """Test secure export functionality."""
        # Add some sensitive audit entries
        self.audit_trail.log_safety_decision(
            "/home/user/sensitive_document.txt",
            SafetyDecision.PROTECTED,
            "Contains personal information",
            1.0
        )

        self.audit_trail.log_user_action(
            "/home/user/another_file.txt",
            "manually_protected",
            "User marked this as important"
        )

        # Test public export (should redact sensitive data)
        public_export = self.test_dir / "public_export.json"
        self.audit_trail.export_logs(
            str(public_export),
            format_type="json",
            security_level=SecurityLevel.PUBLIC
        )

        # Verify export exists and has redacted data
        self.assertTrue(public_export.exists())
        export_data = self.audit_trail.secure_ops.read_json_secure(public_export)

        # Check that sensitive paths are partially redacted
        exported_logs = export_data["exported_logs"]
        for log in exported_logs:
            if "file_path" in log:
                path = log["file_path"]
                # Sensitive paths should be partially redacted in public exports
                if "home/user" in path:
                    self.assertTrue(path.startswith(".../"))

        # Test sensitive export (should keep all data)
        sensitive_export = self.test_dir / "sensitive_export.json"
        self.audit_trail.export_logs(
            str(sensitive_export),
            format_type="json",
            security_level=SecurityLevel.SENSITIVE
        )

        # Verify sensitive export has full data
        sensitive_data = self.audit_trail.secure_ops.read_json_secure(sensitive_export)
        sensitive_logs = sensitive_data["exported_logs"]
        for log in sensitive_logs:
            if "file_path" in log:
                # Should have full paths
                self.assertFalse(log["file_path"].startswith(".../"))

    def test_audit_trail_integrity_verification(self):
        """Test audit trail integrity verification."""
        # Add audit entries
        self.audit_trail.log_safety_decision(
            "/integrity/test.txt",
            SafetyDecision.MANUAL_REVIEW,
            "Requires manual review",
            0.5
        )

        # Save logs
        self.audit_trail.save_logs()

        # Verify integrity
        integrity_check = self.audit_trail.verify_integrity()
        self.assertTrue(integrity_check.is_valid)
        self.assertEqual(integrity_check.entry_count, 1)

        # Corrupt the file
        with open(self.audit_file, 'w') as f:
            f.write('{"corrupted": "data"}')

        # Create new audit trail instance (will try to load corrupted data)
        corrupted_audit = AuditTrail(str(self.audit_file))

        # Should handle corruption gracefully
        logs = corrupted_audit.get_all_logs()
        self.assertEqual(len(logs), 0)  # Should be empty due to corruption

    def test_concurrent_audit_operations(self):
        """Test concurrent audit trail operations."""
        import threading
        import time

        results = []
        errors = []

        def audit_worker(worker_id):
            try:
                # Each worker creates its own audit trail
                audit_file = self.test_dir / f"worker_{worker_id}_audit.json"
                audit_trail = AuditTrail(str(audit_file))

                # Add some entries
                for i in range(5):
                    audit_trail.log_safety_decision(
                        f"/worker_{worker_id}/file_{i}.txt",
                        SafetyDecision.SAFE_TO_DELETE,
                        f"Worker {worker_id} file {i}",
                        0.9
                    )

                # Save logs
                audit_trail.save_logs()

                # Verify logs were saved
                logs = audit_trail.get_all_logs()
                results.append((worker_id, len(logs)))

            except Exception as e:
                errors.append((worker_id, str(e)))

        # Start multiple workers
        threads = []
        for i in range(3):
            thread = threading.Thread(target=audit_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify results
        self.assertEqual(len(errors), 0, f"Errors in concurrent operations: {errors}")
        self.assertEqual(len(results), 3)

        for worker_id, log_count in results:
            self.assertEqual(log_count, 5)


class TestOpenAIClientSecurityIntegration(unittest.TestCase):
    """Test secure file operations integration with OpenAI client."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="openai_security_test_"))

        # Create test config
        self.config = AppConfig()
        self.config.security_mode = 'strict'

        # Mock OpenAI client
        self.mock_openai_response = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "function": {
                            "name": "analyze_files_for_cleanup",
                            "arguments": json.dumps({
                                "file_analyses": [
                                    {
                                        "path": "/test/file1.txt",
                                        "deletion_recommendation": "delete",
                                        "confidence": "high",
                                        "reason": "Test temporary file",
                                        "category": "temp",
                                        "risk_level": "low",
                                        "suggested_action": "Delete file"
                                    },
                                    {
                                        "path": "/test/important.txt",
                                        "deletion_recommendation": "keep",
                                        "confidence": "very_high",
                                        "reason": "Important document",
                                        "category": "document",
                                        "risk_level": "critical",
                                        "suggested_action": "Keep file"
                                    }
                                ]
                            })
                        }
                    }]
                }
            }]
        }

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    @patch('src.ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_openai_client_secure_response_processing(self, mock_openai_class, mock_credential_store):
        """Test that OpenAI client processes responses securely."""
        # Setup mocks
        mock_credential_store.return_value.get_api_key.return_value = "test_key"
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.model_dump.return_value = self.mock_openai_response
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        # Create OpenAI client
        client = OpenAIClient(self.config)

        # Create test file metadata
        file_metadata = [
            FileMetadata(
                path="/test/file1.txt",
                name="file1.txt",
                size_bytes=1024,
                extension=".txt",
                created_date="2024-01-01T00:00:00",
                modified_date="2024-01-01T00:00:00",
                accessed_date="2024-01-01T00:00:00",
                parent_directory="/test",
                is_hidden=False,
                is_system=False
            ),
            FileMetadata(
                path="/test/important.txt",
                name="important.txt",
                size_bytes=2048,
                extension=".txt",
                created_date="2024-01-01T00:00:00",
                modified_date="2024-01-01T00:00:00",
                accessed_date="2024-01-01T00:00:00",
                parent_directory="/test",
                is_hidden=False,
                is_system=False
            )
        ]

        # Analyze files
        results = client.analyze_files(file_metadata)

        # Verify results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].path, "/test/file1.txt")
        self.assertEqual(results[0].deletion_recommendation, "delete")
        self.assertEqual(results[1].path, "/test/important.txt")
        self.assertEqual(results[1].deletion_recommendation, "keep")

        # Verify security status
        security_status = client.get_security_status()
        self.assertIn("client_type", security_status)
        self.assertEqual(security_status["client_type"], "OpenAI API Client")
        self.assertIn("session_security", security_status)

        # Clean up temporary files
        cleaned_count = client.cleanup_temporary_files()
        self.assertGreaterEqual(cleaned_count, 0)

    @patch('src.ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_openai_client_security_event_logging(self, mock_openai_class, mock_credential_store):
        """Test that OpenAI client logs security events properly."""
        # Setup mocks
        mock_credential_store.return_value.get_api_key.return_value = "test_key"
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Create client
        client = OpenAIClient(self.config)

        # Test the _log_security_event method directly
        client._log_security_event("test_event", {
            "test_data": "test_value",
            "timestamp": datetime.now().isoformat()
        })

        # Verify security status shows operations
        security_status = client.get_security_status()
        self.assertTrue(security_status["session_security"]["sanitizer_active"])
        self.assertTrue(security_status["session_security"]["api_key_configured"])

    @patch('src.ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_openai_client_response_validation(self, mock_openai_class, mock_credential_store):
        """Test that OpenAI client validates responses securely."""
        # Setup mocks
        mock_credential_store.return_value.get_api_key.return_value = "test_key"
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Create client
        client = OpenAIClient(self.config)

        # Test with invalid response (missing required fields)
        invalid_response = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "function": {
                            "name": "wrong_function_name",
                            "arguments": "{}"
                        }
                    }]
                }
            }]
        }

        # Parse invalid response
        results = client._parse_analysis_response(invalid_response)

        # Should return empty results due to validation failure
        self.assertEqual(len(results), 0)

        # Test with malformed response
        malformed_response = {"invalid": "structure"}
        results = client._parse_analysis_response(malformed_response)
        self.assertEqual(len(results), 0)

        # Test with valid response
        results = client._parse_analysis_response(self.mock_openai_response)
        self.assertEqual(len(results), 2)

    def test_openai_client_metadata_validation(self):
        """Test that OpenAI client validates metadata properly."""
        # Create client without mocking (for validation testing)
        client = OpenAIClient(self.config)

        # Test valid metadata
        valid_metadata = [
            FileMetadata(
                path="/test/valid.txt",
                name="valid.txt",
                size_bytes=1024,
                extension=".txt",
                created_date="2024-01-01T00:00:00",
                modified_date="2024-01-01T00:00:00",
                accessed_date="2024-01-01T00:00:00",
                parent_directory="/test",
                is_hidden=False,
                is_system=False
            )
        ]

        # Should pass validation
        self.assertTrue(client._validate_metadata_only(valid_metadata))

        # Test metadata with suspicious content (should fail validation)
        class SuspiciousMetadata:
            def __init__(self):
                self.path = "/test/valid.txt"
                self.name = "valid.txt"
                self.size_bytes = 1024
                self.extension = ".txt"
                self.created_date = "2024-01-01T00:00:00"
                self.modified_date = "2024-01-01T00:00:00"
                self.accessed_date = "2024-01-01T00:00:00"
                self.parent_directory = "/test"
                self.is_hidden = False
                self.is_system = False
                self.content = "This should not be here"  # Suspicious field

        suspicious_metadata = [SuspiciousMetadata()]
        self.assertFalse(client._validate_metadata_only(suspicious_metadata))

    def test_openai_client_error_handling(self):
        """Test OpenAI client error handling."""
        client = OpenAIClient(self.config)

        # Test operations without API key
        client.api_key = None
        client.client = None

        with self.assertRaises(RuntimeError):
            client.analyze_files([])

        # Test session statistics
        stats = client.get_session_stats()
        self.assertIn("requests_made", stats)
        self.assertIn("session_cost", stats)
        self.assertIn("rate_limit_status", stats)


class TestEndToEndSecurityIntegration(unittest.TestCase):
    """Test end-to-end security integration."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="e2e_security_test_"))

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_audit_trail_openai_integration(self):
        """Test integration between audit trail and OpenAI client security."""
        # Create audit trail
        audit_file = self.test_dir / "integration_audit.json"
        audit_trail = AuditTrail(str(audit_file))

        # Simulate OpenAI client operations
        from src.ai_disk_cleanup.openai_client import OpenAIClient
        config = AppConfig()
        config.security_mode = 'strict'
        client = OpenAIClient(config)

        # Simulate some security events
        client._log_security_event("test_integration", {
            "audit_trail_file": str(audit_file),
            "operation": "integration_test"
        })

        # Log audit entries
        audit_trail.log_safety_decision(
            "/integration/test.txt",
            SafetyDecision.SAFE_TO_DELETE,
            "Integration test file",
            0.85
        )

        audit_trail.log_error(
            "/integration/error.txt",
            "test_error",
            "This is a test error for integration"
        )

        # Save audit trail
        audit_trail.save_logs()

        # Verify both components have secure files
        self.assertTrue(audit_file.exists())

        # Verify audit trail integrity
        integrity_check = audit_trail.verify_integrity()
        self.assertTrue(integrity_check.is_valid)
        self.assertEqual(integrity_check.entry_count, 2)

        # Verify client security status
        security_status = client.get_security_status()
        self.assertIn("platform", security_status)
        self.assertIn("session_security", security_status)

        # Clean up
        client.cleanup_temporary_files()

    def test_security_performance_impact(self):
        """Test that security measures don't significantly impact performance."""
        import time

        # Create audit trail
        audit_file = self.test_dir / "performance_audit.json"
        audit_trail = AuditTrail(str(audit_file))

        # Measure time for secure operations
        start_time = time.time()

        # Add many entries
        for i in range(100):
            audit_trail.log_safety_decision(
                f"/performance/test_{i}.txt",
                SafetyDecision.SAFE_TO_DELETE,
                f"Performance test file {i}",
                0.9
            )

        # Save logs
        audit_trail.save_logs()

        end_time = time.time()
        duration = end_time - start_time

        # Should complete in reasonable time (less than 5 seconds for 100 entries)
        self.assertLess(duration, 5.0, f"Security operations took too long: {duration:.2f}s")

        # Verify all entries were saved
        logs = audit_trail.get_all_logs()
        self.assertEqual(len(logs), 100)

        # Verify read performance
        start_time = time.time()
        loaded_audit = AuditTrail(str(audit_file))
        loaded_logs = loaded_audit.get_all_logs()
        end_time = time.time()

        read_duration = end_time - start_time
        self.assertLess(read_duration, 2.0, f"Secure read took too long: {read_duration:.2f}s")
        self.assertEqual(len(loaded_logs), 100)


if __name__ == '__main__':
    unittest.main()