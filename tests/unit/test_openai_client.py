"""Comprehensive test suite for OpenAI API client with metadata-only transmission."""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import pytest

from ai_disk_cleanup.openai_client import (
    OpenAIClient, FileMetadata, FileAnalysisResult
)
from ai_disk_cleanup.core.config_models import AppConfig, ConfidenceLevel


class TestFileMetadata:
    """Test FileMetadata dataclass."""

    def test_file_metadata_creation(self):
        """Test FileMetadata object creation and validation."""
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
        assert metadata.name == "test.txt"
        assert metadata.size_bytes == 1024
        assert metadata.extension == ".txt"
        assert metadata.is_hidden is False

    def test_file_metadata_serialization(self):
        """Test FileMetadata serialization for API transmission."""
        metadata = FileMetadata(
            path="/home/user/.cache/app.log",
            name="app.log",
            size_bytes=5120,
            extension=".log",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-02T00:00:00",
            accessed_date="2024-01-02T00:00:00",
            parent_directory="/home/user/.cache",
            is_hidden=True,
            is_system=False
        )

        # Test dict conversion for JSON serialization
        metadata_dict = metadata.__dict__
        assert "content" not in metadata_dict
        assert "data" not in metadata_dict
        assert metadata_dict["path"] == "/home/user/.cache/app.log"
        assert metadata_dict["size_bytes"] == 5120


class TestFileAnalysisResult:
    """Test FileAnalysisResult dataclass."""

    def test_file_analysis_result_creation(self):
        """Test FileAnalysisResult object creation."""
        result = FileAnalysisResult(
            path="/tmp/test.log",
            deletion_recommendation="delete",
            confidence=ConfidenceLevel.HIGH,
            reason="Temporary log file older than 30 days",
            category="log",
            risk_level="low",
            suggested_action="Safe to delete"
        )

        assert result.path == "/tmp/test.log"
        assert result.deletion_recommendation == "delete"
        assert result.confidence == ConfidenceLevel.HIGH
        assert result.risk_level == "low"

    def test_confidence_level_validation(self):
        """Test confidence level validation."""
        # Test all valid confidence levels
        valid_levels = [ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM,
                       ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH]

        for level in valid_levels:
            result = FileAnalysisResult(
                path="/tmp/test",
                deletion_recommendation="keep",
                confidence=level,
                reason="test",
                category="test",
                risk_level="low",
                suggested_action="test"
            )
            assert result.confidence == level


class TestOpenAIClient:
    """Test OpenAI client functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        return AppConfig(
            ai_model={
                "provider": "openai",
                "model_name": "gpt-4",
                "temperature": 0.1,
                "max_tokens": 4096,
                "timeout_seconds": 30
            }
        )

    @pytest.fixture
    def sample_file_metadata(self):
        """Create sample file metadata for testing."""
        return [
            FileMetadata(
                path="/tmp/temp_file1.tmp",
                name="temp_file1.tmp",
                size_bytes=1024,
                extension=".tmp",
                created_date="2024-01-01T00:00:00",
                modified_date="2024-01-01T00:00:00",
                accessed_date="2024-01-01T00:00:00",
                parent_directory="/tmp",
                is_hidden=False,
                is_system=False
            ),
            FileMetadata(
                path="/home/user/.cache/cache_file.cache",
                name="cache_file.cache",
                size_bytes=5120,
                extension=".cache",
                created_date="2024-01-01T00:00:00",
                modified_date="2024-01-01T00:00:00",
                accessed_date="2024-01-01T00:00:00",
                parent_directory="/home/user/.cache",
                is_hidden=True,
                is_system=False
            ),
            FileMetadata(
                path="/var/log/system.log",
                name="system.log",
                size_bytes=2048,
                extension=".log",
                created_date="2024-01-01T00:00:00",
                modified_date="2024-01-01T00:00:00",
                accessed_date="2024-01-01T00:00:00",
                parent_directory="/var/log",
                is_hidden=False,
                is_system=True
            )
        ]

    @pytest.fixture
    def mock_openai_response(self):
        """Create a mock OpenAI API response."""
        return {
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
                                                "path": "/tmp/temp_file1.tmp",
                                                "deletion_recommendation": "delete",
                                                "confidence": "high",
                                                "reason": "Temporary file in /tmp directory",
                                                "category": "temporary",
                                                "risk_level": "low",
                                                "suggested_action": "Safe to delete"
                                            },
                                            {
                                                "path": "/home/user/.cache/cache_file.cache",
                                                "deletion_recommendation": "delete",
                                                "confidence": "medium",
                                                "reason": "Cache file that can be regenerated",
                                                "category": "cache",
                                                "risk_level": "low",
                                                "suggested_action": "Safe to delete"
                                            },
                                            {
                                                "path": "/var/log/system.log",
                                                "deletion_recommendation": "manual_review",
                                                "confidence": "medium",
                                                "reason": "System log file - requires manual review",
                                                "category": "system_log",
                                                "risk_level": "medium",
                                                "suggested_action": "Review contents before deletion"
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

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    def test_client_initialization_success(self, mock_credential_store_class, mock_config):
        """Test successful client initialization."""
        # Mock credential store
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = "sk-test-api-key-12345"
        mock_credential_store_class.return_value = mock_credential_store

        # Mock OpenAI client
        with patch('openai.OpenAI') as mock_openai_class:
            mock_openai_instance = Mock()
            mock_openai_class.return_value = mock_openai_instance

            # Initialize client
            client = OpenAIClient(mock_config)

            # Verify initialization
            assert client.api_key == "sk-test-api-key-12345"
            assert client.client == mock_openai_instance
        assert client.max_requests_per_minute == 60
        assert client.max_session_cost == 0.10
        assert client.min_batch_size == 50
        assert client.max_batch_size == 100

        # Verify credential store was called
        mock_credential_store.get_api_key.assert_called_once_with("openai")

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    def test_client_initialization_no_api_key(self, mock_credential_store_class, mock_config):
        """Test client initialization with missing API key."""
        # Mock credential store with no key
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = None
        mock_credential_store_class.return_value = mock_credential_store

        # Initialize client should not raise but client should be None
        client = OpenAIClient(mock_config)

        assert client.client is None
        assert client.api_key is None

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_metadata_only_validation_success(self, mock_openai_class, mock_credential_store_class, mock_config, sample_file_metadata):
        """Test metadata-only validation with valid data."""
        # Setup client
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = "sk-test-key"
        mock_credential_store_class.return_value = mock_credential_store
        mock_openai_class.return_value = Mock()

        client = OpenAIClient(mock_config)

        # Test validation with valid metadata
        assert client._validate_metadata_only(sample_file_metadata) is True

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_metadata_only_validation_failure_with_content(self, mock_openai_class, mock_credential_store_class, mock_config):
        """Test metadata-only validation failure when content is detected."""
        # Setup client
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = "sk-test-key"
        mock_credential_store_class.return_value = mock_credential_store
        mock_openai_class.return_value = Mock()

        client = OpenAIClient(mock_config)

        # Create metadata with content (violates privacy)
        metadata_with_content = FileMetadata(
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
        metadata_with_content.content = "This is file content"

        # Test validation should fail
        assert client._validate_metadata_only([metadata_with_content]) is False

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_rate_limiting(self, mock_openai_class, mock_credential_store_class, mock_config):
        """Test rate limiting functionality."""
        # Setup client
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = "sk-test-key"
        mock_credential_store_class.return_value = mock_credential_store
        mock_openai_class.return_value = Mock()

        client = OpenAIClient(mock_config)

        # Initially should be within limits
        assert client._check_rate_limit() is True

        # Add requests up to limit
        now = datetime.now()
        for i in range(client.max_requests_per_minute):
            client.request_times.append(now)

        # Should now be at limit
        assert client._check_rate_limit() is False

        # Add old request (should be removed)
        old_time = now - timedelta(minutes=2)
        client.request_times.append(old_time)

        # Should still be at limit (old request removed)
        assert client._check_rate_limit() is False

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_cost_limiting(self, mock_openai_class, mock_credential_store_class, mock_config):
        """Test cost limiting functionality."""
        # Setup client
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = "sk-test-key"
        mock_credential_store_class.return_value = mock_credential_store
        mock_openai_class.return_value = Mock()

        client = OpenAIClient(mock_config)

        # Initially should be within limits
        assert client._check_cost_limit() is True

        # Add costs up to limit
        client.session_cost = client.max_session_cost - 0.01
        assert client._check_cost_limit() is True

        # Exceed limit
        client.session_cost = client.max_session_cost + 0.01
        assert client._check_cost_limit() is False

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_function_calling_setup(self, mock_openai_class, mock_credential_store_class, mock_config):
        """Test function calling configuration."""
        # Setup client
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = "sk-test-key"
        mock_credential_store_class.return_value = mock_credential_store
        mock_openai_class.return_value = Mock()

        client = OpenAIClient(mock_config)

        # Test function creation
        functions = client._create_file_analysis_functions()
        assert len(functions) == 1
        assert functions[0]["name"] == "analyze_files_for_cleanup"

        # Verify function schema
        func_schema = functions[0]
        assert "parameters" in func_schema
        assert "properties" in func_schema["parameters"]
        assert "file_analyses" in func_schema["parameters"]["properties"]

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_analyze_files_success(self, mock_openai_class, mock_credential_store_class, mock_config, sample_file_metadata, mock_openai_response):
        """Test successful file analysis."""
        # Setup client
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = "sk-test-key"
        mock_credential_store_class.return_value = mock_credential_store

        # Mock OpenAI client
        mock_client_instance = Mock()
        mock_openai_class.return_value = mock_client_instance

        # Mock API response
        mock_response = Mock()
        mock_response.model_dump.return_value = mock_openai_response
        mock_client_instance.chat.completions.create.return_value = mock_response

        client = OpenAIClient(mock_config)

        # Temporarily reduce minimum batch size for testing
        client.min_batch_size = 1

        # Test file analysis
        results = client.analyze_files(sample_file_metadata)

        # Verify results
        assert len(results) == 3
        assert results[0].path == "/tmp/temp_file1.tmp"
        assert results[0].deletion_recommendation == "delete"
        assert results[0].confidence == ConfidenceLevel.HIGH
        assert results[0].risk_level == "low"

        assert results[1].path == "/home/user/.cache/cache_file.cache"
        assert results[1].category == "cache"

        assert results[2].path == "/var/log/system.log"
        assert results[2].deletion_recommendation == "manual_review"

        # Verify API was called correctly
        mock_client_instance.chat.completions.create.assert_called_once()
        call_args = mock_client_instance.chat.completions.create.call_args

        # Check parameters
        assert call_args[1]["model"] == "gpt-4"
        assert call_args[1]["temperature"] == 0.1
        assert "tools" in call_args[1]
        assert "tool_choice" in call_args[1]

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_batch_processing_large_dataset(self, mock_openai_class, mock_credential_store_class, mock_config, mock_openai_response):
        """Test processing of large datasets with automatic batching."""
        # Setup client
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = "sk-test-key"
        mock_credential_store_class.return_value = mock_credential_store

        # Mock OpenAI client
        mock_client_instance = Mock()
        mock_openai_class.return_value = mock_client_instance

        # Mock API response
        mock_response = Mock()
        mock_response.model_dump.return_value = mock_openai_response
        mock_client_instance.chat.completions.create.return_value = mock_response

        client = OpenAIClient(mock_config)
        client.min_batch_size = 1  # Allow small batches for testing
        client.max_batch_size = 2  # Small batch size for testing

        # Create large dataset (5 files, batch size 2 = 3 batches)
        large_metadata = []
        for i in range(5):
            metadata = FileMetadata(
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
            )
            large_metadata.append(metadata)

        # Test analysis
        results = client.analyze_files(large_metadata)

        # Verify batching - should make 3 API calls (2+2+1)
        assert mock_client_instance.chat.completions.create.call_count == 3

        # Should have results for all files
        assert len(results) > 0

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_api_error_handling(self, mock_openai_class, mock_credential_store_class, mock_config, sample_file_metadata):
        """Test API error handling."""
        # Setup client
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = "sk-test-key"
        mock_credential_store_class.return_value = mock_credential_store

        # Mock OpenAI client that raises exception
        mock_client_instance = Mock()
        mock_client_instance.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client_instance

        client = OpenAIClient(mock_config)

        # Test error handling - should return empty results
        results = client.analyze_files(sample_file_metadata)
        assert results == []

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_connection_test_success(self, mock_openai_class, mock_credential_store_class, mock_config):
        """Test successful connection test."""
        # Setup client
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = "sk-test-key"
        mock_credential_store_class.return_value = mock_credential_store

        # Mock successful API response
        mock_client_instance = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "OK"
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client_instance

        client = OpenAIClient(mock_config)

        # Test connection
        result = client.test_connection()

        assert result["success"] is True
        assert result["response"] == "OK"
        assert result["api_key_status"] == "valid"

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    def test_connection_test_no_client(self, mock_credential_store_class, mock_config):
        """Test connection test with no client."""
        # Setup client with no API key
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = None
        mock_credential_store_class.return_value = mock_credential_store

        client = OpenAIClient(mock_config)

        # Test connection
        result = client.test_connection()

        assert result["success"] is False
        assert "Client not initialized" in result["error"]

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_session_statistics(self, mock_openai_class, mock_credential_store_class, mock_config):
        """Test session statistics tracking."""
        # Setup client
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = "sk-test-key"
        mock_credential_store_class.return_value = mock_credential_store
        mock_openai_class.return_value = Mock()

        client = OpenAIClient(mock_config)

        # Test initial stats
        stats = client.get_session_stats()
        assert stats["requests_made"] == 0
        assert stats["session_cost"] == 0.0
        assert stats["max_session_cost"] == 0.10
        assert stats["cost_remaining"] == 0.10
        assert stats["rate_limit_status"] == "OK"

        # Add some activity
        client.request_times.append(datetime.now())
        client.session_cost = 0.05

        # Test updated stats
        stats = client.get_session_stats()
        assert stats["requests_made"] == 1
        assert stats["session_cost"] == 0.05
        assert stats["cost_remaining"] == 0.05

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_privacy_compliance_enforcement(self, mock_openai_class, mock_credential_store_class, mock_config):
        """Test that privacy compliance is strictly enforced."""
        # Setup client
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = "sk-test-key"
        mock_credential_store_class.return_value = mock_credential_store
        mock_openai_class.return_value = Mock()

        client = OpenAIClient(mock_config)

        # Test with suspicious metadata
        suspicious_metadata = FileMetadata(
            path="/tmp/normal.txt",
            name="normal.txt",
            size_bytes=1024,
            extension=".txt",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-01T00:00:00",
            accessed_date="2024-01-01T00:00:00",
            parent_directory="/tmp",
            is_hidden=False,
            is_system=False
        )
        # Add suspiciously long field that might contain embedded content
        suspicious_metadata.parent_directory = "A" * 2000  # Very long string

        # Should fail validation
        assert client._validate_metadata_only([suspicious_metadata]) is False

        # Test with unexpected field
        metadata_with_extra_field = FileMetadata(
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
        metadata_with_extra_field.unexpected_field = "suspicious data"

        # Should fail validation
        assert client._validate_metadata_only([metadata_with_extra_field]) is False

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_rate_limit_wait_functionality(self, mock_openai_class, mock_credential_store_class, mock_config):
        """Test rate limit waiting functionality."""
        # Setup client
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = "sk-test-key"
        mock_credential_store_class.return_value = mock_credential_store
        mock_openai_class.return_value = Mock()

        client = OpenAIClient(mock_config)

        # Fill up rate limit
        now = datetime.now()
        for i in range(client.max_requests_per_minute):
            client.request_times.append(now)

        # Should be at limit
        assert client._check_rate_limit() is False

        # Test wait functionality (with mocked sleep to avoid actual delay)
        with patch('time.sleep') as mock_sleep:
            # Add old request to make space
            old_time = now - timedelta(minutes=2)
            client.request_times.append(old_time)

            # Should wait and then proceed
            client._wait_for_rate_limit()

            # Should have called sleep (rate limit enforcement)
            mock_sleep.assert_called()

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_cost_limit_enforcement(self, mock_openai_class, mock_credential_store_class, mock_config, sample_file_metadata):
        """Test cost limit enforcement."""
        # Setup client
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = "sk-test-key"
        mock_credential_store_class.return_value = mock_credential_store
        mock_openai_class.return_value = Mock()

        client = OpenAIClient(mock_config)

        # Exceed cost limit
        client.session_cost = client.max_session_cost + 0.01

        # Should raise exception when trying to analyze
        with pytest.raises(RuntimeError, match="Cost limit exceeded"):
            client.analyze_files(sample_file_metadata)

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_analysis_prompt_creation(self, mock_openai_class, mock_credential_store_class, mock_config, sample_file_metadata):
        """Test analysis prompt creation with privacy warnings."""
        # Setup client
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = "sk-test-key"
        mock_credential_store_class.return_value = mock_credential_store
        mock_openai_class.return_value = Mock()

        client = OpenAIClient(mock_config)

        # Test prompt creation
        prompt = client._create_analysis_prompt(sample_file_metadata)

        # Verify prompt contains privacy warnings
        assert "IMPORTANT: You are ONLY receiving metadata" in prompt
        assert "This is a privacy requirement" in prompt
        assert "File metadata to analyze:" in prompt

        # Verify metadata is properly serialized
        assert "/tmp/temp_file1.tmp" in prompt
        assert "1024" in prompt  # size_bytes
        assert ".tmp" in prompt  # extension

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_response_parsing_edge_cases(self, mock_openai_class, mock_credential_store_class, mock_config):
        """Test response parsing with various edge cases."""
        # Setup client
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = "sk-test-key"
        mock_credential_store_class.return_value = mock_credential_store
        mock_openai_class.return_value = Mock()

        client = OpenAIClient(mock_config)

        # Test empty response
        empty_response = {"choices": []}
        results = client._parse_analysis_response(empty_response)
        assert results == []

        # Test response with no tool calls
        no_tools_response = {"choices": [{"message": {}}]}
        results = client._parse_analysis_response(no_tools_response)
        assert results == []

        # Test response with wrong function name
        wrong_function_response = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "wrong_function",
                                    "arguments": "{}"
                                }
                            }
                        ]
                    }
                }
            ]
        }
        results = client._parse_analysis_response(wrong_function_response)
        assert results == []

        # Test response with malformed JSON
        malformed_response = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "analyze_files_for_cleanup",
                                    "arguments": "invalid json {"
                                }
                            }
                        ]
                    }
                }
            ]
        }
        results = client._parse_analysis_response(malformed_response)
        assert results == []


class TestPrivacyComplianceIntegration:
    """Integration tests focused on privacy compliance."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        return AppConfig(
            ai_model={
                "provider": "openai",
                "model_name": "gpt-4",
                "temperature": 0.1,
                "max_tokens": 4096,
                "timeout_seconds": 30
            }
        )

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_zero_file_content_transmission(self, mock_openai_class, mock_credential_store_class, mock_config):
        """Test that absolutely no file content is transmitted to API."""
        # Setup client
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = "sk-test-key"
        mock_credential_store_class.return_value = mock_credential_store

        # Mock OpenAI client to capture actual API calls
        mock_client_instance = Mock()
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
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client_instance

        client = OpenAIClient(mock_config)

        # Create file metadata
        metadata = FileMetadata(
            path="/tmp/secret_file.txt",
            name="secret_file.txt",
            size_bytes=1024,
            extension=".txt",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-01T00:00:00",
            accessed_date="2024-01-01T00:00:00",
            parent_directory="/tmp",
            is_hidden=False,
            is_system=False
        )

        # Analyze files
        client.analyze_files([metadata])

        # Verify API call parameters
        call_args = mock_client_instance.chat.completions.create.call_args
        messages = call_args[1]["messages"]

        # Extract message content
        message_content = messages[0]["content"]

        # Verify no file content is present
        assert "secret_file.txt" in message_content  # Name should be present
        assert "1024" in message_content  # Size should be present
        assert "/tmp/secret_file.txt" in message_content  # Path should be present

        # Verify no actual file content (check for specific content patterns, not the word "content" itself)
        assert "file content:" not in message_content.lower()
        assert "file data:" not in message_content.lower()
        assert "binary data" not in message_content.lower()
        assert "encrypted content" not in message_content.lower()
        assert len(message_content) < 5000  # Reasonable size limit

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_privacy_violation_detection(self, mock_openai_class, mock_credential_store_class, mock_config):
        """Test detection and prevention of privacy violations."""
        # Setup client
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = "sk-test-key"
        mock_credential_store_class.return_value = mock_credential_store
        mock_openai_class.return_value = Mock()

        client = OpenAIClient(mock_config)

        # Create metadata with hidden content attribute
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

        # Add content attribute dynamically (simulating attempt to bypass privacy)
        setattr(metadata, 'content', 'This is secret file content')
        setattr(metadata, 'file_data', 'More secret data')

        # Should raise privacy violation exception
        with pytest.raises(ValueError, match="Privacy validation failed"):
            client.analyze_files([metadata])


class TestPerformanceAndOptimization:
    """Tests for performance and optimization features."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        return AppConfig(
            ai_model={
                "provider": "openai",
                "model_name": "gpt-4",
                "temperature": 0.1,
                "max_tokens": 4096,
                "timeout_seconds": 30
            }
        )

    @pytest.fixture
    def mock_openai_response(self):
        """Create a mock OpenAI API response."""
        return {
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
                                                "path": "/tmp/test.tmp",
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

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_batch_size_optimization(self, mock_openai_class, mock_credential_store_class, mock_config, mock_openai_response):
        """Test batch size optimization for API efficiency."""
        # Setup client
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = "sk-test-key"
        mock_credential_store_class.return_value = mock_credential_store

        # Mock OpenAI client
        mock_client_instance = Mock()
        mock_response = Mock()
        mock_response.model_dump.return_value = mock_openai_response
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client_instance

        client = OpenAIClient(mock_config)

        # Test minimum batch size warning
        small_batch = [FileMetadata(
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
        ) for i in range(10)]  # 10 files (below min batch size of 50)

        # Should still work but log warning
        with patch.object(client.logger, 'warning') as mock_warning:
            results = client.analyze_files(small_batch)
            mock_warning.assert_called_once()
            assert "below minimum" in mock_warning.call_args[0][0]

    @patch('ai_disk_cleanup.openai_client.CredentialStore')
    @patch('openai.OpenAI')
    def test_cost_tracking_accuracy(self, mock_openai_class, mock_credential_store_class, mock_config, mock_openai_response):
        """Test accurate cost tracking across multiple requests."""
        # Setup client
        mock_credential_store = Mock()
        mock_credential_store.get_api_key.return_value = "sk-test-key"
        mock_credential_store_class.return_value = mock_credential_store

        # Mock OpenAI client
        mock_client_instance = Mock()
        mock_response = Mock()
        mock_response.model_dump.return_value = mock_openai_response
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client_instance

        client = OpenAIClient(mock_config)
        initial_cost = client.session_cost

        # Make multiple requests
        for i in range(3):
            metadata = [FileMetadata(
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
            )]
            client.analyze_files(metadata)

        # Verify cost tracking
        expected_cost = initial_cost + (3 * client.cost_per_request)
        assert client.session_cost == expected_cost

        # Verify session stats
        stats = client.get_session_stats()
        assert stats["requests_made"] == 3
        assert stats["session_cost"] == expected_cost