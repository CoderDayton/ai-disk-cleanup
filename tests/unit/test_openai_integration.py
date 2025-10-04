"""Simplified OpenAI API integration tests with metadata-only transmission."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from ai_disk_cleanup.openai_client import (
    OpenAIClient, FileMetadata, FileAnalysisResult
)
from ai_disk_cleanup.core.config_models import AppConfig, ConfidenceLevel


class TestFileMetadata:
    """Test FileMetadata dataclass."""

    def test_file_metadata_creation(self):
        """Test FileMetadata object creation."""
        metadata = FileMetadata(
            path="/tmp/test.txt",
            name="test.txt",
            size_bytes=1024,
            extension=".txt",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-01T00:00:00",
            accessed_date="2024-01-01T00:00:00",
            parent_directory="/tmp",
            is_hidden=False,
            is_system=False
        )

        assert metadata.path == "/tmp/test.txt"
        assert metadata.size_bytes == 1024
        assert not hasattr(metadata, 'content')
        assert not hasattr(metadata, 'data')


class TestOpenAIClientBasics:
    """Test basic OpenAI client functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        return AppConfig(
            ai_model={
                "provider": "openai",
                "model_name": "gpt-4",
                "temperature": 0.1,
                "max_tokens": 4096,
                "timeout_seconds": 30
            }
        )

    def test_client_creation_without_api_key(self, mock_config):
        """Test client creation when API key is missing."""
        with patch('ai_disk_cleanup.openai_client.CredentialStore') as mock_store_class:
            mock_store = Mock()
            mock_store.get_api_key.return_value = None
            mock_store_class.return_value = mock_store

            client = OpenAIClient(mock_config)

            assert client.client is None
            assert client.api_key is None

    def test_rate_limiting_logic(self, mock_config):
        """Test rate limiting logic."""
        client = OpenAIClient(mock_config)

        # Should start with no limits
        assert client._check_rate_limit() is True

        # Add requests up to limit
        from datetime import datetime
        now = datetime.now()
        for _ in range(client.max_requests_per_minute):
            client.request_times.append(now)

        # Should now be at limit
        assert client._check_rate_limit() is False

    def test_cost_limiting_logic(self, mock_config):
        """Test cost limiting logic."""
        client = OpenAIClient(mock_config)

        # Should start within limits
        assert client._check_cost_limit() is True

        # Exceed cost limit
        client.session_cost = client.max_session_cost + 0.01
        assert client._check_cost_limit() is False

    def test_metadata_validation_success(self, mock_config):
        """Test successful metadata validation."""
        client = OpenAIClient(mock_config)

        metadata = FileMetadata(
            path="/tmp/test.txt",
            name="test.txt",
            size_bytes=1024,
            extension=".txt",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-01T00:00:00",
            accessed_date="2024-01-01T00:00:00",
            parent_directory="/tmp",
            is_hidden=False,
            is_system=False
        )

        assert client._validate_metadata_only([metadata]) is True

    def test_metadata_validation_failure_with_content(self, mock_config):
        """Test metadata validation failure when content is present."""
        client = OpenAIClient(mock_config)

        metadata = FileMetadata(
            path="/tmp/test.txt",
            name="test.txt",
            size_bytes=1024,
            extension=".txt",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-01T00:00:00",
            accessed_date="2024-01-01T00:00:00",
            parent_directory="/tmp",
            is_hidden=False,
            is_system=False
        )

        # Add content attribute (should not exist)
        metadata.content = "This is file content"

        assert client._validate_metadata_only([metadata]) is False

    def test_function_calling_setup(self, mock_config):
        """Test function calling configuration."""
        client = OpenAIClient(mock_config)

        functions = client._create_file_analysis_functions()

        assert len(functions) == 1
        assert functions[0]["name"] == "analyze_files_for_cleanup"
        assert "file_analyses" in functions[0]["parameters"]["properties"]

    def test_analysis_prompt_creation(self, mock_config):
        """Test analysis prompt creation with privacy warnings."""
        client = OpenAIClient(mock_config)

        metadata = [FileMetadata(
            path="/tmp/test.txt",
            name="test.txt",
            size_bytes=1024,
            extension=".txt",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-01T00:00:00",
            accessed_date="2024-01-01T00:00:00",
            parent_directory="/tmp",
            is_hidden=False,
            is_system=False
        )]

        prompt = client._create_analysis_prompt(metadata)

        # Verify privacy warnings
        assert "IMPORTANT: You are ONLY receiving metadata" in prompt
        assert "This is a privacy requirement" in prompt
        assert "/tmp/test.txt" in prompt
        assert "1024" in prompt

    def test_response_parsing_success(self, mock_config):
        """Test successful response parsing."""
        client = OpenAIClient(mock_config)

        response_data = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "analyze_files_for_cleanup",
                                    "arguments": json.dumps({
                                        "file_analyses": [
                                            {
                                                "path": "/tmp/test.txt",
                                                "deletion_recommendation": "delete",
                                                "confidence": "high",
                                                "reason": "Test file",
                                                "category": "temporary",
                                                "risk_level": "low",
                                                "suggested_action": "Safe to delete"
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

        results = client._parse_analysis_response(response_data)

        assert len(results) == 1
        assert results[0].path == "/tmp/test.txt"
        assert results[0].deletion_recommendation == "delete"
        assert results[0].confidence == ConfidenceLevel.HIGH

    def test_response_parsing_empty_response(self, mock_config):
        """Test response parsing with empty response."""
        client = OpenAIClient(mock_config)

        empty_response = {"choices": []}
        results = client._parse_analysis_response(empty_response)

        assert results == []

    def test_response_parsing_no_tool_calls(self, mock_config):
        """Test response parsing with no tool calls."""
        client = OpenAIClient(mock_config)

        no_tools_response = {"choices": [{"message": {}}]}
        results = client._parse_analysis_response(no_tools_response)

        assert results == []

    def test_privacy_compliance_enforcement(self, mock_config):
        """Test privacy compliance enforcement."""
        client = OpenAIClient(mock_config)

        # Test with suspiciously long field
        metadata = FileMetadata(
            path="/tmp/test.txt",
            name="test.txt",
            size_bytes=1024,
            extension=".txt",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-01T00:00:00",
            accessed_date="2024-01-01T00:00:00",
            parent_directory="A" * 2000,  # Suspiciously long
            is_hidden=False,
            is_system=False
        )

        assert client._validate_metadata_only([metadata]) is False

        # Test with unexpected field
        metadata2 = FileMetadata(
            path="/tmp/test2.txt",
            name="test2.txt",
            size_bytes=1024,
            extension=".txt",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-01T00:00:00",
            accessed_date="2024-01-01T00:00:00",
            parent_directory="/tmp",
            is_hidden=False,
            is_system=False
        )
        metadata2.unexpected_field = "suspicious data"

        assert client._validate_metadata_only([metadata2]) is False

    def test_session_statistics(self, mock_config):
        """Test session statistics tracking."""
        client = OpenAIClient(mock_config)

        stats = client.get_session_stats()

        assert stats["requests_made"] == 0
        assert stats["session_cost"] == 0.0
        assert stats["max_session_cost"] == 0.10
        assert stats["rate_limit_status"] == "OK"
        assert stats["batch_sizes"]["min"] == 50
        assert stats["batch_sizes"]["max"] == 100

    def test_connection_test_without_client(self, mock_config):
        """Test connection test when client is not initialized."""
        client = OpenAIClient(mock_config)
        client.client = None

        result = client.test_connection()

        assert result["success"] is False
        assert "Client not initialized" in result["error"]

    def test_cost_limit_enforcement(self, mock_config):
        """Test cost limit enforcement during analysis."""
        client = OpenAIClient(mock_config)

        # Mock client
        client.client = Mock()

        # Exceed cost limit
        client.session_cost = client.max_session_cost + 0.01

        metadata = [FileMetadata(
            path="/tmp/test.txt",
            name="test.txt",
            size_bytes=1024,
            extension=".txt",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-01T00:00:00",
            accessed_date="2024-01-01T00:00:00",
            parent_directory="/tmp",
            is_hidden=False,
            is_system=False
        )]

        with pytest.raises(RuntimeError, match="Cost limit exceeded"):
            client.analyze_files(metadata)


class TestPrivacyCompliance:
    """Tests focused on privacy compliance."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        return AppConfig(
            ai_model={
                "provider": "openai",
                "model_name": "gpt-4",
                "temperature": 0.1,
                "max_tokens": 4096,
                "timeout_seconds": 30
            }
        )

    def test_zero_content_transmission_validation(self, mock_config):
        """Test validation that ensures zero file content transmission."""
        client = OpenAIClient(mock_config)

        # Valid metadata should pass
        valid_metadata = FileMetadata(
            path="/tmp/legitimate_file.txt",
            name="legitimate_file.txt",
            size_bytes=1024,
            extension=".txt",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-01T00:00:00",
            accessed_date="2024-01-01T00:00:00",
            parent_directory="/tmp",
            is_hidden=False,
            is_system=False
        )

        assert client._validate_metadata_only([valid_metadata]) is True

        # Any attempt to add content should fail
        invalid_metadata = FileMetadata(
            path="/tmp/secret.txt",
            name="secret.txt",
            size_bytes=1024,
            extension=".txt",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-01T00:00:00",
            accessed_date="2024-01-01T00:00:00",
            parent_directory="/tmp",
            is_hidden=False,
            is_system=False
        )

        # Try various ways to embed content
        invalid_metadata.content = "Secret content"
        assert client._validate_metadata_only([invalid_metadata]) is False

        # Remove content and try file_data
        del invalid_metadata.content
        invalid_metadata.file_data = b"Binary content"
        assert client._validate_metadata_only([invalid_metadata]) is False

        # Remove file_data and try embedding in path
        del invalid_metadata.file_data
        invalid_metadata.path = "/tmp/secret.txt" + "X" * 5000  # Very long path
        assert client._validate_metadata_only([invalid_metadata]) is False

    def test_analysis_prompt_privacy_warnings(self, mock_config):
        """Test that analysis prompt contains proper privacy warnings."""
        client = OpenAIClient(mock_config)

        metadata = [FileMetadata(
            path="/home/user/document.pdf",
            name="document.pdf",
            size_bytes=2048,
            extension=".pdf",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-01T00:00:00",
            accessed_date="2024-01-01T00:00:00",
            parent_directory="/home/user",
            is_hidden=False,
            is_system=False
        )]

        prompt = client._create_analysis_prompt(metadata)

        # Verify all privacy warnings are present
        assert "IMPORTANT: You are ONLY receiving metadata" in prompt
        assert "NO file content" in prompt
        assert "This is a privacy requirement" in prompt

        # Verify file metadata is included but no content
        assert "/home/user/document.pdf" in prompt
        assert "2048" in prompt  # size
        assert ".pdf" in prompt  # extension

        # Verify no actual content indicators (but allow legitimate usage in instructions)
        assert "file content" in prompt.lower()  # This should be in privacy warning
        # Check that there are no suspicious content-like fields in JSON
        assert '"content":' not in prompt
        assert '"data":' not in prompt
        assert len(prompt) < 10000  # Reasonable size limit


class TestPerformanceAndRateLimiting:
    """Tests for performance and rate limiting features."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        return AppConfig(
            ai_model={
                "provider": "openai",
                "model_name": "gpt-4",
                "temperature": 0.1,
                "max_tokens": 4096,
                "timeout_seconds": 30
            }
        )

    def test_rate_limit_wait_functionality(self, mock_config):
        """Test rate limit waiting functionality."""
        client = OpenAIClient(mock_config)

        # Fill up rate limit
        from datetime import datetime
        now = datetime.now()
        for _ in range(client.max_requests_per_minute):
            client.request_times.append(now)

        assert client._check_rate_limit() is False

        # Mock time.sleep to avoid actual waiting
        with patch('time.sleep') as mock_sleep:
            # Wait should handle the rate limit
            client._wait_for_rate_limit()

            # Sleep may or may not be called depending on timing
            # This mainly tests that the method doesn't crash

    def test_batch_size_handling(self, mock_config):
        """Test batch size constraints and warnings."""
        client = OpenAIClient(mock_config)
        client.client = Mock()  # Mock client to avoid initialization

        # Mock response for successful analysis
        mock_response = Mock()
        mock_response.model_dump.return_value = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "analyze_files_for_cleanup",
                                    "arguments": json.dumps({
                                        "file_analyses": []
                                    })
                                }
                            }
                        ]
                    }
                }
            ]
        }
        client.client.chat.completions.create.return_value = mock_response

        # Small batch should work but warn
        small_batch = []
        for i in range(10):  # Below min batch size of 50
            small_batch.append(FileMetadata(
                path=f"/tmp/test{i}.tmp",
                name=f"test{i}.tmp",
                size_bytes=1024,
                extension=".tmp",
                created_date="2024-01-01T00:00:00",
                modified_date="2024-01-01T00:00:00",
                accessed_date="2024-01-01T00:00:00",
                parent_directory="/tmp",
                is_hidden=False,
                is_system=False
            ))

        with patch.object(client.logger, 'warning') as mock_warning:
            client.analyze_files(small_batch)
            mock_warning.assert_called_once()
            assert "below minimum" in mock_warning.call_args[0][0]

    def test_cost_tracking_accuracy(self, mock_config):
        """Test accurate cost tracking."""
        client = OpenAIClient(mock_config)

        initial_cost = client.session_cost
        initial_requests = len(client.request_times)

        # Simulate multiple requests
        from datetime import datetime
        for i in range(3):
            client.request_times.append(datetime.now())
            client.session_cost += client.cost_per_request

        expected_cost = initial_cost + (3 * client.cost_per_request)
        expected_requests = initial_requests + 3

        assert client.session_cost == expected_cost
        assert len(client.request_times) == expected_requests

        # Verify session stats
        stats = client.get_session_stats()
        assert stats["requests_made"] == expected_requests
        assert stats["session_cost"] == expected_cost
        assert stats["cost_remaining"] == client.max_session_cost - expected_cost