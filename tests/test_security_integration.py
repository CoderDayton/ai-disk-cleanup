"""
Integration tests for security components across the system.

Tests how the security sanitization integrates with existing components
and maintains functionality while providing security.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.ai_disk_cleanup.core.config_manager import ConfigManager
from src.ai_disk_cleanup.openai_client import OpenAIClient, FileMetadata, FileAnalysisResult
from src.ai_disk_cleanup.core.config_models import AppConfig, ConfidenceLevel
from src.ai_disk_cleanup.security.input_sanitizer import get_sanitizer


class TestOpenAIClientSecurityIntegration:
    """Test security integration in OpenAI client."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        config = Mock(spec=AppConfig)
        config.api_key = "sk-test1234567890abcdef1234567890abcdef12345678"
        config.model_name = "gpt-4"
        config.max_tokens = 1000
        config.temperature = 0.7
        config.timeout_seconds = 30
        config.security_mode = "strict"
        return config

    @pytest.fixture
    def openai_client(self, mock_config):
        """Create OpenAI client for testing."""
        return OpenAIClient(mock_config)

    def test_metadata_validation_with_sanitizer(self, openai_client):
        """Test that metadata validation uses the sanitizer."""
        # Safe metadata should pass
        safe_metadata = FileMetadata(
            path="/home/user/document.txt",
            name="document.txt",
            size_bytes=1024,
            extension=".txt",
            created_date="2023-01-01T00:00:00Z",
            modified_date="2023-01-01T00:00:00Z",
            accessed_date="2023-01-01T00:00:00Z",
            parent_directory="/home/user",
            is_hidden=False,
            is_system=False
        )

        result = openai_client._validate_metadata_only([safe_metadata])
        assert result, "Safe metadata should pass validation"

        # Dangerous metadata should fail
        dangerous_metadata = FileMetadata(
            path="../../../etc/passwd",
            name="passwd",
            size_bytes=2048,
            extension="",
            created_date="2023-01-01T00:00:00Z",
            modified_date="2023-01-01T00:00:00Z",
            accessed_date="2023-01-01T00:00:00Z",
            parent_directory="/etc",
            is_hidden=False,
            is_system=True
        )

        result = openai_client._validate_metadata_only([dangerous_metadata])
        assert not result, "Dangerous metadata should fail validation"

    @patch('src.ai_disk_cleanup.openai_client.requests.post')
    def test_api_response_parsing_with_validation(self, mock_post, openai_client):
        """Test API response parsing with security validation."""
        # Mock a safe API response
        safe_response = {
            'choices': [
                {
                    'index': 0,
                    'message': {
                        'role': 'assistant',
                        'tool_calls': [
                            {
                                'id': 'call_123abc',
                                'type': 'function',
                                'function': {
                                    'name': 'analyze_files_for_cleanup',
                                    'arguments': json.dumps({
                                        'file_analyses': [
                                            {
                                                'path': '/home/user/safe_file.txt',
                                                'deletion_recommendation': 'keep',
                                                'confidence': 'high',
                                                'reason': 'Important document',
                                                'category': 'document',
                                                'risk_level': 'low',
                                                'suggested_action': 'Keep this file'
                                            }
                                        ]
                                    })
                                }
                            }
                        ]
                    }
                }
            ]
        }

        mock_response = Mock()
        mock_response.json.return_value = safe_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = openai_client._parse_analysis_response(safe_response)
        assert len(result) == 1, "Should parse one analysis result"
        assert result[0].path == '/home/user/safe_file.txt'
        assert result[0].deletion_recommendation == 'keep'

        # Test malicious response
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
                                    'arguments': json.dumps({
                                        'file_analyses': [
                                            {
                                                'path': '../../../etc/passwd',
                                                'deletion_recommendation': 'delete',
                                                'confidence': 'high',
                                                'reason': '<script>alert("xss")</script>',
                                                'category': 'system',
                                                'risk_level': 'low',
                                                'suggested_action': 'Delete system file'
                                            }
                                        ]
                                    })
                                }
                            }
                        ]
                    }
                }
            ]
        }

        result = openai_client._parse_analysis_response(malicious_response)
        assert len(result) == 0, "Malicious response should result in no parsed results"


class TestConfigManagerSecurityIntegration:
    """Test security integration in configuration manager."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary directory for config files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create config manager with temporary directory."""
        config_file = temp_config_dir / "config.json"
        prefs_file = temp_config_dir / "prefs.json"
        return ConfigManager(config_file=config_file, user_prefs_file=prefs_file, auto_load=False)

    def test_safe_config_import(self, config_manager, temp_config_dir):
        """Test importing safe configuration."""
        safe_config = {
            'config': {
                'api_key': 'sk-1234567890abcdef1234567890abcdef12345678',
                'model_name': 'gpt-4',
                'max_tokens': 1000,
                'temperature': 0.7,
                'timeout_seconds': 30,
                'cache_enabled': True,
                'log_level': 'INFO'
            },
            'user_preferences': {
                'default_action': 'review',
                'confidence_threshold': 0.8,
                'show_system_files': False,
                'backup_before_delete': True
            }
        }

        config_file = temp_config_dir / "safe_config.json"
        with open(config_file, 'w') as f:
            json.dump(safe_config, f)

        result = config_manager.import_config(config_file)
        assert result, "Safe config import should succeed"
        assert config_manager.config is not None
        assert config_manager.config.model_name == 'gpt-4'

    def test_malicious_config_import_rejection(self, config_manager, temp_config_dir):
        """Test that malicious configuration is rejected."""
        malicious_config = {
            'config': {
                'api_key': 'sk-1234567890abcdef1234567890abcdef12345678',
                'model_name': 'gpt-4; rm -rf /',
                'max_tokens': -1,  # Invalid
                'temperature': 10.0,  # Out of range
                'timeout_seconds': 'not_integer',
                'cache_enabled': True,
                'log_level': 'DEBUG; DROP TABLE users; --'
            },
            'user_preferences': {
                'default_action': '<script>alert("xss")</script>',
                'confidence_threshold': 2.0,  # Out of range
                'show_system_files': False,
                'backup_before_delete': True
            }
        }

        config_file = temp_config_dir / "malicious_config.json"
        with open(config_file, 'w') as f:
            json.dump(malicious_config, f)

        result = config_manager.import_config(config_file)
        assert not result, "Malicious config import should fail"

    def test_config_sanitization_in_normal_mode(self, temp_config_dir):
        """Test config sanitization in normal (non-strict) mode."""
        config_manager = ConfigManager(
            config_file=temp_config_dir / "config.json",
            user_prefs_file=temp_config_dir / "prefs.json",
            auto_load=False
        )
        config_manager.sanitizer = get_sanitizer(strict_mode=False)

        # Config with some issues but not malicious
        questionable_config = {
            'config': {
                'api_key': 'sk-1234567890abcdef1234567890abcdef12345678',
                'model_name': 'gpt-4-model',
                'max_tokens': 1500,  # Above normal but not malicious
                'temperature': 0.9,
                'timeout_seconds': 60,
                'cache_enabled': True,
                'log_level': 'DEBUG'
            }
        }

        config_file = temp_config_dir / "questionable_config.json"
        with open(config_file, 'w') as f:
            json.dump(questionable_config, f)

        result = config_manager.import_config(config_file)
        assert result, "Questionable config should be sanitized and accepted in normal mode"


class TestEndToEndSecurityScenarios:
    """Test end-to-end security scenarios."""

    def test_complete_file_analysis_pipeline_with_security(self):
        """Test complete file analysis pipeline with security validation."""
        # Create configuration
        config = Mock(spec=AppConfig)
        config.api_key = "sk-test1234567890abcdef1234567890abcdef12345678"
        config.model_name = "gpt-4"
        config.security_mode = "strict"

        # Create client
        client = OpenAIClient(config)

        # Test metadata with mixed safety
        safe_metadata = FileMetadata(
            path="/home/user/document.txt",
            name="document.txt",
            size_bytes=1024,
            extension=".txt",
            created_date="2023-01-01T00:00:00Z",
            modified_date="2023-01-01T00:00:00Z",
            accessed_date="2023-01-01T00:00:00Z",
            parent_directory="/home/user",
            is_hidden=False,
            is_system=False
        )

        dangerous_metadata = FileMetadata(
            path="../../../etc/passwd",
            name="passwd",
            size_bytes=2048,
            extension="",
            created_date="2023-01-01T00:00:00Z",
            modified_date="2023-01-01T00:00:00Z",
            accessed_date="2023-01-01T00:00:00Z",
            parent_directory="/etc",
            is_hidden=False,
            is_system=True
        )

        # Safe metadata should pass validation
        assert client._validate_metadata_only([safe_metadata])

        # Dangerous metadata should fail validation
        assert not client._validate_metadata_only([dangerous_metadata])

        # Mixed batch should fail validation entirely
        assert not client._validate_metadata_only([safe_metadata, dangerous_metadata])

    def test_security_event_accumulation(self):
        """Test that security events are properly accumulated."""
        sanitizer = get_sanitizer(strict_mode=True)

        # Generate various security events
        sanitizer.sanitize_filename("../../../etc/passwd")
        sanitizer.sanitize_user_input("<script>alert('xss')</script>")
        sanitizer.sanitize_config_value("api_key", "invalid", {})

        summary = sanitizer.get_security_summary()
        assert summary['total_events'] >= 3
        assert summary['error_events'] >= 2

        # Clear and verify
        sanitizer.clear_security_events()
        summary = sanitizer.get_security_summary()
        assert summary['total_events'] == 0

    @patch('src.ai_disk_cleanup.openai_client.requests.post')
    def test_api_response_with_nested_injection_attempts(self, mock_post):
        """Test API response validation with nested injection attempts."""
        config = Mock(spec=AppConfig)
        config.api_key = "sk-test1234567890abcdef1234567890abcdef12345678"
        config.security_mode = "strict"
        client = OpenAIClient(config)

        # Response with injection attempts at multiple levels
        malicious_nested_response = {
            'choices': [
                {
                    'index': 0,
                    'message': {
                        'role': 'assistant<script>alert("xss")</script>',
                        'tool_calls': [
                            {
                                'id': 'call_$(whoami)',
                                'type': 'function',
                                'function': {
                                    'name': 'analyze_files_for_cleanup; cat /etc/passwd',
                                    'arguments': '{"file_analyses":[{"path":"../../../root/.ssh/id_rsa","deletion_recommendation":"delete","reason":"rm -rf /"}]}'
                                }
                            }
                        ]
                    }
                }
            ]
        }

        result = client._parse_analysis_response(malicious_nested_response)
        assert len(result) == 0, "Nested malicious response should be completely rejected"

    def test_performance_with_security_validation(self):
        """Test that security validation doesn't significantly impact performance."""
        import time

        sanitizer = get_sanitizer(strict_mode=False)  # Use normal mode for performance

        # Large batch of safe data
        safe_filenames = [f"document_{i}.txt" for i in range(1000)]
        safe_paths = [f"/home/user/documents/{filename}" for filename in safe_filenames]

        start_time = time.time()

        # Validate all filenames
        for filename in safe_filenames:
            result = sanitizer.sanitize_filename(filename)
            assert result.is_valid

        # Validate all paths
        for path in safe_paths:
            result = sanitizer.sanitize_file_path(path)
            assert result.is_valid

        end_time = time.time()
        processing_time = end_time - start_time

        # Should complete 2000 validations in reasonable time
        assert processing_time < 2.0, f"Performance test failed: {processing_time:.3f}s for 2000 validations"

    def test_backward_compatibility(self):
        """Test that security enhancements maintain backward compatibility."""
        # Test with existing configuration structure
        config_data = {
            'api_key': 'sk-1234567890abcdef1234567890abcdef12345678',
            'model_name': 'gpt-4',
            'max_tokens': 1000,
            'temperature': 0.7,
            'timeout_seconds': 30,
            'cache_enabled': True,
            'log_level': 'INFO',
            'security_mode': 'normal'  # New field
        }

        sanitizer = get_sanitizer(strict_mode=False)

        # Should handle new field gracefully
        for key, value in config_data.items():
            result = sanitizer.sanitize_config_value(key, value, {})
            assert result.is_valid, f"Backward compatibility issue with field: {key}"

        # Should work with missing security_mode (defaults to normal)
        config_without_security = {k: v for k, v in config_data.items() if k != 'security_mode'}

        for key, value in config_without_security.items():
            result = sanitizer.sanitize_config_value(key, value, {})
            assert result.is_valid, f"Missing security_mode should not break validation"


if __name__ == '__main__':
    pytest.main([__file__])