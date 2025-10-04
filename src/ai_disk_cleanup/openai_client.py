"""OpenAI API client with metadata-only transmission for privacy-first file analysis."""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from .security.secure_file_ops import (
    SecureFileOperations, SecurityLevel, FileOperationError,
    secure_temp_file
)

from .core.config_models import AppConfig, ConfidenceLevel
from .security.credential_store import CredentialStore
from .security.input_sanitizer import get_sanitizer, ValidationResult
from .security.validation_schemas import (
    OPENAI_RESPONSE_SCHEMA, OPENAI_CHOICE_SCHEMA, OPENAI_MESSAGE_SCHEMA,
    OPENAI_TOOL_CALL_SCHEMA, OPENAI_FUNCTION_SCHEMA, FILE_ANALYSIS_RESULT_SCHEMA
)


@dataclass
class FileMetadata:
    """File metadata for AI analysis - contains no file content."""
    path: str
    name: str
    size_bytes: int
    extension: str
    created_date: str
    modified_date: str
    accessed_date: str
    parent_directory: str
    is_hidden: bool
    is_system: bool


@dataclass
class FileAnalysisResult:
    """Result from AI file analysis."""
    path: str
    deletion_recommendation: str
    confidence: ConfidenceLevel
    reason: str
    category: str
    risk_level: str
    suggested_action: str


class OpenAIClient:
    """OpenAI API client with privacy-first metadata-only transmission."""

    def __init__(self, config: AppConfig):
        """Initialize OpenAI client with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.credential_store = CredentialStore()

        # Initialize security components
        self.sanitizer = get_sanitizer(strict_mode=config.security_mode == 'strict')
        self.secure_ops = SecureFileOperations(self.logger)

        # Rate limiting: 60 requests per minute maximum
        self.max_requests_per_minute = 60
        self.request_times: List[datetime] = []

        # Cost tracking: target <$0.10 per session
        self.session_cost = 0.0
        self.max_session_cost = 0.10
        self.cost_per_request = 0.002  # Estimated cost per request

        # Batching settings
        self.min_batch_size = 50
        self.max_batch_size = 100

        # API configuration
        self.api_key: Optional[str] = None
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize OpenAI client with API key."""
        try:
            # Get API key from secure credential store
            self.api_key = self.credential_store.get_api_key("openai")

            if not self.api_key:
                self.logger.warning("OpenAI API key not found in credential store")
                self.client = None
                return

            # Import here to avoid dependency if not available
            try:
                import openai
                from openai import OpenAI as OpenAIClient
                self.client = OpenAIClient(api_key=self.api_key)
            except ImportError:
                self.logger.error("OpenAI library not installed. Install with: pip install openai")
                self.client = None

        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
            self.client = None
            self.api_key = None

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = datetime.now()

        # Remove requests older than 1 minute
        self.request_times = [req_time for req_time in self.request_times
                            if now - req_time < timedelta(minutes=1)]

        # Check if we can make a request
        if len(self.request_times) >= self.max_requests_per_minute:
            return False

        return True

    def _check_cost_limit(self) -> bool:
        """Check if we're within cost limits."""
        return self.session_cost < self.max_session_cost

    def _wait_for_rate_limit(self):
        """Wait if we're at rate limit."""
        while not self._check_rate_limit():
            time.sleep(1)

    def _create_file_analysis_functions(self) -> List[Dict[str, Any]]:
        """Create function definitions for file analysis."""
        return [
            {
                "name": "analyze_files_for_cleanup",
                "description": "Analyze file metadata to determine if files can be safely deleted",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_analyses": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string", "description": "Full file path"},
                                    "deletion_recommendation": {
                                        "type": "string",
                                        "enum": ["delete", "keep", "manual_review"],
                                        "description": "Recommendation for file deletion"
                                    },
                                    "confidence": {
                                        "type": "string",
                                        "enum": ["low", "medium", "high", "very_high"],
                                        "description": "Confidence level in recommendation"
                                    },
                                    "reason": {"type": "string", "description": "Reason for recommendation"},
                                    "category": {
                                        "type": "string",
                                        "description": "File category (temp, cache, log, document, etc.)"
                                    },
                                    "risk_level": {
                                        "type": "string",
                                        "enum": ["low", "medium", "high", "critical"],
                                        "description": "Risk level if deleted"
                                    },
                                    "suggested_action": {
                                        "type": "string",
                                        "description": "Suggested action to take"
                                    }
                                },
                                "required": ["path", "deletion_recommendation", "confidence", "reason", "category", "risk_level", "suggested_action"]
                            }
                        }
                    },
                    "required": ["file_analyses"]
                }
            }
        ]

    def _validate_metadata_only(self, file_metadata_list: List[FileMetadata]) -> bool:
        """Validate that only metadata is being transmitted, not file content."""
        for metadata in file_metadata_list:
            # Ensure no file content is included - check for common content field names
            content_fields = ['content', 'data', 'file_data', 'file_content', 'text', 'body']
            for field in content_fields:
                if hasattr(metadata, field):
                    self.logger.error(f"File content detected in metadata for {metadata.path} (field: {field})")
                    return False

            # Verify only metadata fields are present
            allowed_fields = {
                'path', 'name', 'size_bytes', 'extension', 'created_date',
                'modified_date', 'accessed_date', 'parent_directory',
                'is_hidden', 'is_system'
            }

            actual_fields = set(metadata.__dict__.keys())
            if not actual_fields.issubset(allowed_fields):
                self.logger.error(f"Unexpected fields in metadata for {metadata.path}: {actual_fields - allowed_fields}")
                return False

            # Enhanced validation using the security sanitizer
            for field in allowed_fields:
                field_value = getattr(metadata, field, '')

                # Use the sanitizer for comprehensive validation
                validation_result = self.sanitizer.sanitize_metadata_field(field, field_value, max_string_length=1000)

                if not validation_result.is_valid:
                    self.logger.error(f"Security validation failed for field '{field}' in {metadata.path}: {validation_result.security_events}")
                    return False

                # Log any security warnings
                for event in validation_result.security_events:
                    if 'WARNING' in event or 'ERROR' in event:
                        self.logger.warning(f"Security event in metadata validation: {event}")

            # Additional path validation
            path_result = self.sanitizer.sanitize_file_path(metadata.path)
            if not path_result.is_valid:
                self.logger.error(f"Path validation failed for {metadata.path}: {path_result.security_events}")
                return False

        return True

    def _create_analysis_prompt(self, file_metadata_list: List[FileMetadata]) -> str:
        """Create analysis prompt for file metadata."""
        return f"""Analyze the following file metadata and determine which files can be safely deleted for disk cleanup.

IMPORTANT: You are ONLY receiving metadata (file paths, sizes, dates, extensions) - NO file content. This is a privacy requirement.

Your task:
1. Analyze file metadata to determine safe deletion candidates
2. Consider file age, size, location, and type
3. Identify temporary files, cache files, logs, and other cleanup candidates
4. Assess risk levels for each file
5. Provide clear reasoning for recommendations

File metadata to analyze:
{json.dumps([metadata.__dict__ for metadata in file_metadata_list], indent=2)}

Use the analyze_files_for_cleanup function to provide your analysis for each file."""

    def _parse_analysis_response(self, response_data: Dict[str, Any]) -> List[FileAnalysisResult]:
        """Parse OpenAI function calling response into FileAnalysisResult objects with secure temporary file handling."""
        # Use secure temporary file to process sensitive API response data
        with secure_temp_file(prefix="openai_response_", logger=self.logger) as temp_file:
            try:
                # Store response data securely during processing
                self.secure_ops.write_json_secure(
                    temp_file,
                    {
                        "response_data": response_data,
                        "timestamp": datetime.now().isoformat(),
                        "processing_stage": "initial_parsing"
                    },
                    security_level=SecurityLevel.SENSITIVE,
                    redact_sensitive_fields=False  # Keep full data for analysis
                )

                # Enhanced validation of the API response structure
                response_validation = self.sanitizer.validate_api_response_schema(response_data, OPENAI_RESPONSE_SCHEMA)
                if not response_validation.is_valid:
                    self.logger.error(f"API response validation failed: {response_validation.security_events}")
                    # Log validation failure securely
                    self._log_security_event("api_response_validation_failed", {
                        "security_events": response_validation.security_events,
                        "response_size": len(str(response_data))
                    })
                    return []

                # Use validated response data
                validated_response = response_validation.sanitized_value

                # Store validated response for audit trail
                self.secure_ops.write_json_secure(
                    temp_file,
                    {
                        "validated_response": validated_response,
                        "timestamp": datetime.now().isoformat(),
                        "processing_stage": "validated_response"
                    },
                    security_level=SecurityLevel.SENSITIVE
                )

                # Extract function call data with validation
                if not validated_response.get('choices'):
                    self.logger.warning("No choices found in validated response")
                    return []

                # Validate choice structure
                choice = validated_response['choices'][0]
                choice_validation = self.sanitizer.validate_api_response_schema(choice, OPENAI_CHOICE_SCHEMA)
                if not choice_validation.is_valid:
                    self.logger.error(f"Choice validation failed: {choice_validation.security_events}")
                    self._log_security_event("choice_validation_failed", {
                        "security_events": choice_validation.security_events
                    })
                    return []

                validated_choice = choice_validation.sanitized_value
                message = validated_choice.get('message')
                if not message or not message.get('tool_calls'):
                    self.logger.warning("No message or tool_calls found in validated choice")
                    return []

                # Validate message structure
                message_validation = self.sanitizer.validate_api_response_schema(message, OPENAI_MESSAGE_SCHEMA)
                if not message_validation.is_valid:
                    self.logger.error(f"Message validation failed: {message_validation.security_events}")
                    self._log_security_event("message_validation_failed", {
                        "security_events": message_validation.security_events
                    })
                    return []

                validated_message = message_validation.sanitized_value
                tool_call = validated_message['tool_calls'][0]

                # Validate tool call structure
                tool_call_validation = self.sanitizer.validate_api_response_schema(tool_call, OPENAI_TOOL_CALL_SCHEMA)
                if not tool_call_validation.is_valid:
                    self.logger.error(f"Tool call validation failed: {tool_call_validation.security_events}")
                    self._log_security_event("tool_call_validation_failed", {
                        "security_events": tool_call_validation.security_events
                    })
                    return []

                validated_tool_call = tool_call_validation.sanitized_value
                function = validated_tool_call.get('function')

                # Validate function structure
                function_validation = self.sanitizer.validate_api_response_schema(function, OPENAI_FUNCTION_SCHEMA)
                if not function_validation.is_valid:
                    self.logger.error(f"Function validation failed: {function_validation.security_events}")
                    self._log_security_event("function_validation_failed", {
                        "security_events": function_validation.security_events
                    })
                    return []

                validated_function = function_validation.sanitized_value
                if validated_function['name'] != 'analyze_files_for_cleanup':
                    self.logger.warning(f"Unexpected function name: {validated_function['name']}")
                    return []

                # Parse and validate arguments with secure temporary storage
                try:
                    arguments = json.loads(validated_function['arguments'])
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse function arguments: {e}")
                    # Store parsing error securely
                    self._log_security_event("argument_parsing_failed", {
                        "error": str(e),
                        "arguments": validated_function['arguments'][:100] + "..." if len(validated_function['arguments']) > 100 else validated_function['arguments']
                    })
                    return []

                file_analyses = arguments.get('file_analyses', [])
                if not isinstance(file_analyses, list):
                    self.logger.error("file_analyses is not a list")
                    return []

                # Store parsed arguments securely
                self.secure_ops.write_json_secure(
                    temp_file,
                    {
                        "parsed_arguments": arguments,
                        "file_count": len(file_analyses),
                        "timestamp": datetime.now().isoformat(),
                        "processing_stage": "arguments_parsed"
                    },
                    security_level=SecurityLevel.SENSITIVE
                )

                results = []
                security_violations = []

                for i, analysis in enumerate(file_analyses):
                    # Validate each analysis result
                    analysis_validation = self.sanitizer.validate_api_response_schema(analysis, FILE_ANALYSIS_RESULT_SCHEMA)
                    if not analysis_validation.is_valid:
                        self.logger.warning(f"Analysis validation failed for item {i}: {analysis_validation.security_events}")
                        security_violations.append({
                            "item_index": i,
                            "violations": analysis_validation.security_events
                        })
                        continue  # Skip invalid analysis but continue with others

                    validated_analysis = analysis_validation.sanitized_value

                    # Additional path validation for security
                    path_validation = self.sanitizer.sanitize_file_path(validated_analysis['path'])
                    if not path_validation.is_valid:
                        self.logger.warning(f"Invalid path in analysis result {i}: {validated_analysis['path']}")
                        security_violations.append({
                            "item_index": i,
                            "path_violations": path_validation.security_events
                        })
                        continue

                    try:
                        result = FileAnalysisResult(
                            path=path_validation.sanitized_value,
                            deletion_recommendation=validated_analysis['deletion_recommendation'],
                            confidence=ConfidenceLevel(validated_analysis['confidence']),
                            reason=validated_analysis['reason'],
                            category=validated_analysis['category'],
                            risk_level=validated_analysis['risk_level'],
                            suggested_action=validated_analysis['suggested_action']
                        )
                        results.append(result)
                    except (ValueError, KeyError) as e:
                        self.logger.warning(f"Failed to create FileAnalysisResult for item {i}: {e}")
                        security_violations.append({
                            "item_index": i,
                            "creation_error": str(e)
                        })
                        continue

                # Store final results and any security violations
                self.secure_ops.write_json_secure(
                    temp_file,
                    {
                        "final_results": [result.__dict__ for result in results],
                        "security_violations": security_violations,
                        "successful_count": len(results),
                        "total_count": len(file_analyses),
                        "timestamp": datetime.now().isoformat(),
                        "processing_stage": "completed"
                    },
                    security_level=SecurityLevel.SENSITIVE
                )

                # Log security summary if there were violations
                if security_violations:
                    self._log_security_event("response_processing_completed_with_violations", {
                        "total_items": len(file_analyses),
                        "successful_items": len(results),
                        "violation_count": len(security_violations)
                    })

                self.logger.info(f"Successfully processed {len(results)}/{len(file_analyses)} file analyses")
                return results

            except FileOperationError as e:
                self.logger.error(f"Secure file operation failed during response parsing: {e}")
                return []
            except Exception as e:
                self.logger.error(f"Failed to parse analysis response: {e}")
                self._log_security_event("response_parsing_error", {
                    "error": str(e),
                    "response_size": len(str(response_data))
                })
                return []

    def _log_security_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Log security events with secure temporary file storage."""
        try:
            with secure_temp_file(prefix="security_event_", logger=self.logger) as temp_file:
                self.secure_ops.write_json_secure(
                    temp_file,
                    {
                        "event_type": event_type,
                        "timestamp": datetime.now().isoformat(),
                        "data": event_data,
                        "client_info": {
                            "session_cost": self.session_cost,
                            "requests_made": len(self.request_times)
                        }
                    },
                    security_level=SecurityLevel.CRITICAL,  # Security events are critical
                    redact_sensitive_fields=False
                )
        except FileOperationError as e:
            # Fallback to regular logging if secure operations fail
            self.logger.error(f"Failed to log security event {event_type}: {e}")
            self.logger.warning(f"Security event data: {event_data}")

    def analyze_files(self, file_metadata_list: List[FileMetadata]) -> List[FileAnalysisResult]:
        """
        Analyze files using OpenAI API with metadata-only transmission.

        Args:
            file_metadata_list: List of file metadata to analyze

        Returns:
            List of file analysis results
        """
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")

        # Validate privacy compliance - metadata only
        if not self._validate_metadata_only(file_metadata_list):
            raise ValueError("Privacy validation failed: file content detected or invalid metadata")

        # Check rate and cost limits
        self._wait_for_rate_limit()
        if not self._check_cost_limit():
            raise RuntimeError(f"Cost limit exceeded: ${self.session_cost:.3f} >= ${self.max_session_cost}")

        # Batch files appropriately
        if len(file_metadata_list) < self.min_batch_size:
            self.logger.warning(f"Batch size ({len(file_metadata_list)}) below minimum ({self.min_batch_size})")

        if len(file_metadata_list) > self.max_batch_size:
            # Split into multiple batches
            results = []
            for i in range(0, len(file_metadata_list), self.max_batch_size):
                batch = file_metadata_list[i:i + self.max_batch_size]
                batch_results = self._analyze_batch(batch)
                results.extend(batch_results)
            return results
        else:
            return self._analyze_batch(file_metadata_list)

    def _analyze_batch(self, file_metadata_batch: List[FileMetadata]) -> List[FileAnalysisResult]:
        """Analyze a single batch of files."""
        try:
            # Record request time for rate limiting
            self.request_times.append(datetime.now())

            # Create analysis request
            prompt = self._create_analysis_prompt(file_metadata_batch)
            functions = self._create_file_analysis_functions()

            # Make API call
            response = self.client.chat.completions.create(
                model=self.config.ai_model.model_name,
                messages=[{"role": "user", "content": prompt}],
                tools=functions,
                tool_choice={"type": "function", "function": {"name": "analyze_files_for_cleanup"}},
                temperature=self.config.ai_model.temperature,
                max_tokens=self.config.ai_model.max_tokens,
                timeout=self.config.ai_model.timeout_seconds
            )

            # Update cost tracking
            self.session_cost += self.cost_per_request

            # Convert response to dict for parsing
            response_dict = response.model_dump()

            # Parse results
            results = self._parse_analysis_response(response_dict)

            self.logger.info(f"Successfully analyzed {len(file_metadata_batch)} files, got {len(results)} results")
            return results

        except Exception as e:
            self.logger.error(f"Failed to analyze batch: {e}")
            # Return empty results for failed batch
            return []

    def test_connection(self) -> Dict[str, Any]:
        """Test OpenAI API connection and credentials."""
        try:
            if not self.client:
                return {
                    "success": False,
                    "error": "Client not initialized",
                    "details": "API key not found or invalid"
                }

            # Make a minimal test request
            response = self.client.chat.completions.create(
                model=self.config.ai_model.model_name,
                messages=[{"role": "user", "content": "Respond with 'OK' for connection test"}],
                max_tokens=10,
                timeout=10
            )

            return {
                "success": True,
                "response": response.choices[0].message.content,
                "model": self.config.ai_model.model_name,
                "api_key_status": "valid"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "api_key_status": "invalid_or_error"
            }

    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics."""
        return {
            "requests_made": len(self.request_times),
            "session_cost": round(self.session_cost, 4),
            "max_session_cost": self.max_session_cost,
            "cost_remaining": round(self.max_session_cost - self.session_cost, 4),
            "rate_limit_status": "OK" if self._check_rate_limit() else "LIMITED",
            "batch_sizes": {
                "min": self.min_batch_size,
                "max": self.max_batch_size
            }
        }

    def cleanup_temporary_files(self) -> int:
        """Clean up temporary files created during API response processing."""
        try:
            cleaned_count = self.secure_ops.cleanup_temp_files()
            if cleaned_count > 0:
                self.logger.info(f"Cleaned up {cleaned_count} temporary files from OpenAI client operations")
            return cleaned_count
        except Exception as e:
            self.logger.error(f"Failed to cleanup temporary files: {e}")
            return 0

    def get_security_status(self) -> Dict[str, Any]:
        """Get security status information for the OpenAI client."""
        base_status = self.secure_ops.get_security_status()
        base_status.update({
            "client_type": "OpenAI API Client",
            "session_security": {
                "api_key_configured": bool(self.api_key),
                "strict_security_mode": self.config.security_mode == 'strict',
                "sanitizer_active": self.sanitizer is not None,
                "session_cost": self.session_cost,
                "max_session_cost": self.max_session_cost
            }
        })
        return base_status