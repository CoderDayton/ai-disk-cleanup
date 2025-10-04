"""
Comprehensive input sanitization and validation module for AI disk cleanup system.

This module provides security-focused input validation and sanitization to prevent
injection attacks, ensure data integrity, and validate structured data against
expected schemas.

Security Features:
- Pattern-based validation for file paths, names, and extensions
- API response schema validation with strict type checking
- Configuration value sanitization with type validation
- XSS, SQL injection, and command injection prevention
- Comprehensive security event logging
"""

import json
import logging
import re
import string
from pathlib import Path, PurePath
from typing import Any, Dict, List, Optional, Set, Union, Callable
from dataclasses import dataclass
from enum import Enum

# Configure security logger
security_logger = logging.getLogger('ai_disk_cleanup.security')


class ValidationSeverity(Enum):
    """Validation severity levels for security events."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Result of input validation operation."""
    is_valid: bool
    sanitized_value: Any
    security_events: List[str]
    severity: ValidationSeverity
    original_value: Any


class InputSanitizer:
    """
    Comprehensive input sanitization and validation class.

    Provides multiple layers of validation including pattern matching,
    type checking, and injection prevention for various input types.
    """

    # Security patterns for injection detection
    INJECTION_PATTERNS = [
        # SQL injection patterns
        r"(?i)(union|select|insert|update|delete|drop|create|alter|exec|execute)\s+",
        r"(?i)('|(\\')|('')|(\-\-)|(;))",
        r"(?i)(or|and)\s+\d+\s*=\s*\d+",
        r"(?i)(or|and)\s+['\"]?[^'\"]*['\"]?\s*=\s*['\"]?[^'\"]*['\"]?",

        # Command injection patterns
        r"[;&|`$(){}[\]\\]",
        r"(?i)(\.\./|\.\.\\)",
        r"(?i)(rm|del|format|shutdown|reboot|halt|poweroff)\s+",
        r"(?i)(wget|curl|nc|netcat|telnet)\s+",

        # XSS patterns
        r"(?i)(<script|<iframe|<object|<embed|<link|<meta)",
        r"(?i)(javascript:|vbscript:|onload=|onerror=|onclick=)",
        r"(?i)(alert\(|confirm\(|prompt\(|eval\(|setTimeout\(|setInterval\()",

        # Path traversal patterns
        r"\.\.[\\/]",
        r"[\\/]\.\.[\\/]",
        r"\.\\.\\.\\",
        r"%2e%2e[\\/]",  # URL-encoded ../
        r"%2e%2e%2f",    # URL-encoded ../
        r"%2e%2e%5c",    # URL-encoded ..\

        # File system patterns
        r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)",
        r"(?i)(/dev/null|/dev/zero|/dev/random|/dev/urandom)",
    ]

    # Allowlist for safe characters in different contexts
    SAFE_FILENAME_CHARS = string.ascii_letters + string.digits + "._-"
    SAFE_PATH_CHARS = string.ascii_letters + string.digits + "._-/\\:"
    SAFE_TEXT_CHARS = string.printable.replace("\x00", "")

    # Allowed file extensions (allowlist approach)
    ALLOWED_EXTENSIONS = {
        # Documents
        '.txt', '.md', '.pdf', '.doc', '.docx', '.rtf', '.odt',
        # Images
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg', '.webp',
        # Video
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
        # Audio
        '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma',
        # Archives
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
        # Code
        '.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml',
        '.cpp', '.c', '.h', '.java', '.php', '.rb', '.go', '.rs',
        # System/Config
        '.ini', '.cfg', '.conf', '.log', '.tmp', '.temp', '.bak',
        # Data
        '.csv', '.sql', '.db', '.sqlite', '.mdb'
    }

    # Dangerous extensions (denylist as backup)
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
        '.jar', '.app', '.deb', '.rpm', '.dmg', '.pkg', '.msi', '.msp',
        '.ps1', '.sh', '.bash', '.zsh', '.fish', '.pl', '.rb'
    }

    def __init__(self, strict_mode: bool = True):
        """
        Initialize input sanitizer.

        Args:
            strict_mode: Enable strict validation for high-security contexts
        """
        self.strict_mode = strict_mode
        self.security_events = []

        # Compile regex patterns for performance
        # Note: Remove inline flags and apply at compilation level
        pattern_strings = []
        for pattern in self.INJECTION_PATTERNS:
            # Remove inline flags and add to list
            clean_pattern = pattern.replace('(?i)', '')
            pattern_strings.append(clean_pattern)

        self.injection_regex = re.compile('|'.join(pattern_strings), re.IGNORECASE)
        self.path_traversal_regex = re.compile(r'\.\.[\\/]', re.IGNORECASE)

    def _log_security_event(self, message: str, severity: ValidationSeverity,
                          input_value: Any = None, context: str = "") -> None:
        """Log security events with detailed context."""
        log_message = f"[{severity.value.upper()}] {message}"
        if context:
            log_message += f" (Context: {context})"
        if input_value is not None:
            # Sanitize for logging to prevent log injection
            safe_input = str(input_value)[:100].replace('\n', '\\n').replace('\r', '\\r')
            log_message += f" (Input: {safe_input})"

        self.security_events.append(log_message)

        if severity == ValidationSeverity.CRITICAL:
            security_logger.critical(log_message)
        elif severity == ValidationSeverity.ERROR:
            security_logger.error(log_message)
        elif severity == ValidationSeverity.WARNING:
            security_logger.warning(log_message)
        else:
            security_logger.info(log_message)

    def _check_injection_patterns(self, value: str, context: str = "") -> List[str]:
        """Check for injection patterns in input string."""
        detected_patterns = []

        if not isinstance(value, str):
            return detected_patterns

        # Check against compiled injection patterns
        matches = self.injection_regex.findall(value)
        if matches:
            detected_patterns.extend([f"Injection pattern detected: {match}" for match in matches])

        # Check for path traversal specifically
        if self.path_traversal_regex.search(value):
            detected_patterns.append("Path traversal pattern detected")

        # Log detected patterns
        for pattern in detected_patterns:
            self._log_security_event(pattern, ValidationSeverity.ERROR, value, context)

        return detected_patterns

    def sanitize_filename(self, filename: str, max_length: int = 255) -> ValidationResult:
        """
        Sanitize and validate filename.

        Args:
            filename: Input filename to validate
            max_length: Maximum allowed filename length

        Returns:
            ValidationResult with sanitized filename and security events
        """
        if not isinstance(filename, str):
            return ValidationResult(
                is_valid=False,
                sanitized_value="",
                security_events=["Filename must be a string"],
                severity=ValidationSeverity.ERROR,
                original_value=filename
            )

        original_filename = filename
        security_events = []

        # Check for null bytes and control characters first
        if '\x00' in filename or any(ord(c) < 32 for c in filename):
            security_events.append("Null bytes or control characters detected")
            self._log_security_event(
                "Null bytes or control characters in filename",
                ValidationSeverity.ERROR, original_filename, "filename validation"
            )
            if self.strict_mode:
                return ValidationResult(
                    is_valid=False,
                    sanitized_value="",
                    security_events=security_events,
                    severity=ValidationSeverity.ERROR,
                    original_value=original_filename
                )

        # Check for injection patterns
        injection_patterns = self._check_injection_patterns(filename, "filename validation")
        if injection_patterns:
            security_events.extend(injection_patterns)
            if self.strict_mode:
                return ValidationResult(
                    is_valid=False,
                    sanitized_value="",
                    security_events=security_events,
                    severity=ValidationSeverity.ERROR,
                    original_value=original_filename
                )

        # Remove null bytes and control characters
        filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)

        # Normalize path separators
        filename = filename.replace('/', '_').replace('\\', '_')

        # Remove dangerous characters and replace with safe alternatives
        dangerous_chars = '<>:"|?*;'
        for char in dangerous_chars:
            filename = filename.replace(char, '_')

        # Ensure filename doesn't start or end with dots or spaces
        filename = filename.strip('. ')

        # Check if filename is empty after sanitization
        if not filename:
            return ValidationResult(
                is_valid=False,
                sanitized_value="",
                security_events=security_events + ["Filename became empty after sanitization"],
                severity=ValidationSeverity.ERROR,
                original_value=original_filename
            )

        # Check length
        if len(filename) > max_length:
            filename = filename[:max_length]
            security_events.append(f"Filename truncated to {max_length} characters")
            self._log_security_event(
                f"Filename truncated: {original_filename} -> {filename}",
                ValidationSeverity.WARNING, original_filename, "filename length"
            )

        # Validate extension
        extension = Path(filename).suffix.lower()
        if extension in self.DANGEROUS_EXTENSIONS:
            security_events.append(f"Dangerous file extension detected: {extension}")
            if self.strict_mode:
                return ValidationResult(
                    is_valid=False,
                    sanitized_value="",
                    security_events=security_events,
                    severity=ValidationSeverity.ERROR,
                    original_value=original_filename
                )
            else:
                self._log_security_event(
                    f"Warning: Dangerous file extension detected: {extension}",
                    ValidationSeverity.WARNING, original_filename, "filename validation"
                )

        # Check for Windows reserved names
        windows_reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {f'COM{i}' for i in range(1, 10)} | {f'LPT{i}' for i in range(1, 10)}
        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in windows_reserved:
            security_events.append(f"Windows reserved name detected: {name_without_ext}")
            if self.strict_mode:
                return ValidationResult(
                    is_valid=False,
                    sanitized_value="",
                    security_events=security_events,
                    severity=ValidationSeverity.ERROR,
                    original_value=original_filename
                )

        is_valid = len(injection_patterns) == 0 and len(filename) > 0

        return ValidationResult(
            is_valid=is_valid,
            sanitized_value=filename,
            security_events=security_events,
            severity=ValidationSeverity.WARNING if injection_patterns else ValidationSeverity.INFO,
            original_value=original_filename
        )

    def sanitize_file_path(self, file_path: Union[str, Path],
                          allow_traversal: bool = False) -> ValidationResult:
        """
        Sanitize and validate file path.

        Args:
            file_path: Input file path to validate
            allow_traversal: Allow path traversal (should be False in most cases)

        Returns:
            ValidationResult with sanitized path and security events
        """
        if not isinstance(file_path, (str, Path)):
            return ValidationResult(
                is_valid=False,
                sanitized_value="",
                security_events=["File path must be string or Path object"],
                severity=ValidationSeverity.ERROR,
                original_value=file_path
            )

        original_path = str(file_path)
        security_events = []

        # Convert to string and normalize
        path_str = str(file_path)

        # Check for injection patterns
        injection_patterns = self._check_injection_patterns(path_str, "file path validation")
        security_events.extend(injection_patterns)

        try:
            # Normalize the path
            normalized_path = Path(path_str).resolve()

            # Check for path traversal if not allowed
            if not allow_traversal:
                if '..' in path_str or normalized_path.is_absolute():
                    security_events.append("Path traversal or absolute path detected")
                    self._log_security_event(
                        "Path traversal/absolute path detected",
                        ValidationSeverity.ERROR, path_str, "path validation"
                    )
                    if self.strict_mode:
                        return ValidationResult(
                            is_valid=False,
                            sanitized_value="",
                            security_events=security_events,
                            severity=ValidationSeverity.ERROR,
                            original_value=original_path
                        )

            # Check path length
            if len(str(normalized_path)) > 4096:  # Common filesystem limit
                security_events.append("Path exceeds maximum length")
                return ValidationResult(
                    is_valid=False,
                    sanitized_value="",
                    security_events=security_events,
                    severity=ValidationSeverity.ERROR,
                    original_value=original_path
                )

            # Validate each component of the path
            for component in normalized_path.parts:
                if component:
                    filename_result = self.sanitize_filename(component)
                    if not filename_result.is_valid:
                        security_events.extend(filename_result.security_events)
                        if self.strict_mode:
                            return ValidationResult(
                                is_valid=False,
                                sanitized_value="",
                                security_events=security_events,
                                severity=ValidationSeverity.ERROR,
                                original_value=original_path
                            )

            is_valid = len(injection_patterns) == 0

            return ValidationResult(
                is_valid=is_valid,
                sanitized_value=str(normalized_path),
                security_events=security_events,
                severity=ValidationSeverity.WARNING if injection_patterns else ValidationSeverity.INFO,
                original_value=original_path
            )

        except Exception as e:
            security_events.append(f"Path normalization error: {str(e)}")
            return ValidationResult(
                is_valid=False,
                sanitized_value="",
                security_events=security_events,
                severity=ValidationSeverity.ERROR,
                original_value=original_path
            )

    def sanitize_metadata_field(self, field_name: str, field_value: Any,
                              max_string_length: int = 1000) -> ValidationResult:
        """
        Sanitize and validate metadata field.

        Args:
            field_name: Name of the metadata field
            field_value: Value to validate
            max_string_length: Maximum allowed string length

        Returns:
            ValidationResult with sanitized value and security events
        """
        security_events = []
        original_value = field_value

        # Validate field name
        if not isinstance(field_name, str):
            security_events.append("Field name must be a string")
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                security_events=security_events,
                severity=ValidationSeverity.ERROR,
                original_value=original_value
            )

        # Check field name against injection patterns
        injection_patterns = self._check_injection_patterns(field_name, "metadata field name")
        security_events.extend(injection_patterns)

        # Validate field value based on type
        if isinstance(field_value, str):
            # Check for injection patterns in string values
            value_injection = self._check_injection_patterns(field_value, f"metadata field '{field_name}'")
            security_events.extend(value_injection)

            # Check length
            if len(field_value) > max_string_length:
                security_events.append(f"Field '{field_name}' exceeds maximum length")
                if self.strict_mode:
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value="",
                        security_events=security_events,
                        severity=ValidationSeverity.ERROR,
                        original_value=original_value
                    )
                field_value = field_value[:max_string_length]

            # Sanitize string value
            field_value = field_value.replace('\x00', '')  # Remove null bytes

        elif isinstance(field_value, (int, float, bool)):
            # Numeric and boolean values are generally safe
            pass
        elif isinstance(field_value, list):
            # Validate list elements
            sanitized_list = []
            for i, item in enumerate(field_value):
                item_result = self.sanitize_metadata_field(f"{field_name}[{i}]", item, max_string_length)
                security_events.extend(item_result.security_events)
                if item_result.is_valid:
                    sanitized_list.append(item_result.sanitized_value)
                elif self.strict_mode:
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value=None,
                        security_events=security_events,
                        severity=ValidationSeverity.ERROR,
                        original_value=original_value
                    )
            field_value = sanitized_list

        elif isinstance(field_value, dict):
            # Validate dictionary values recursively
            sanitized_dict = {}
            for key, value in field_value.items():
                item_result = self.sanitize_metadata_field(f"{field_name}.{key}", value, max_string_length)
                security_events.extend(item_result.security_events)
                if item_result.is_valid:
                    sanitized_dict[key] = item_result.sanitized_value
                elif self.strict_mode:
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value=None,
                        security_events=security_events,
                        severity=ValidationSeverity.ERROR,
                        original_value=original_value
                    )
            field_value = sanitized_dict
        else:
            # Unknown type
            security_events.append(f"Unsupported field type in '{field_name}': {type(field_value)}")
            if self.strict_mode:
                return ValidationResult(
                    is_valid=False,
                    sanitized_value=None,
                    security_events=security_events,
                    severity=ValidationSeverity.ERROR,
                    original_value=original_value
                )

        is_valid = len(injection_patterns) == 0

        return ValidationResult(
            is_valid=is_valid,
            sanitized_value=field_value,
            security_events=security_events,
            severity=ValidationSeverity.WARNING if injection_patterns else ValidationSeverity.INFO,
            original_value=original_value
        )

    def validate_api_response_schema(self, response_data: Dict[str, Any],
                                  expected_schema: Dict[str, Any]) -> ValidationResult:
        """
        Validate API response against expected schema.

        Args:
            response_data: API response data to validate
            expected_schema: Expected schema definition

        Returns:
            ValidationResult with validation results and security events
        """
        security_events = []

        if not isinstance(response_data, dict):
            security_events.append("API response must be a dictionary")
            return ValidationResult(
                is_valid=False,
                sanitized_value={},
                security_events=security_events,
                severity=ValidationSeverity.ERROR,
                original_value=response_data
            )

        # Check for unexpected top-level keys
        expected_keys = set(expected_schema.keys())
        actual_keys = set(response_data.keys())
        unexpected_keys = actual_keys - expected_keys

        if unexpected_keys and self.strict_mode:
            security_events.append(f"Unexpected keys in API response: {unexpected_keys}")
            return ValidationResult(
                is_valid=False,
                sanitized_value={},
                security_events=security_events,
                severity=ValidationSeverity.ERROR,
                original_value=response_data
            )

        # Validate each field according to schema
        validated_data = {}
        for key, schema_def in expected_schema.items():
            if key not in response_data:
                if schema_def.get('required', False):
                    security_events.append(f"Required key missing from API response: {key}")
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value={},
                        security_events=security_events,
                        severity=ValidationSeverity.ERROR,
                        original_value=response_data
                    )
                continue

            value = response_data[key]
            expected_type = schema_def.get('type')

            # Type validation
            if expected_type:
                if expected_type == 'string' and not isinstance(value, str):
                    security_events.append(f"Expected string for key '{key}', got {type(value)}")
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value={},
                        security_events=security_events,
                        severity=ValidationSeverity.ERROR,
                        original_value=response_data
                    )
                elif expected_type == 'integer' and not isinstance(value, int):
                    security_events.append(f"Expected integer for key '{key}', got {type(value)}")
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value={},
                        security_events=security_events,
                        severity=ValidationSeverity.ERROR,
                        original_value=response_data
                    )
                elif expected_type == 'float' and not isinstance(value, (int, float)):
                    security_events.append(f"Expected number for key '{key}', got {type(value)}")
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value={},
                        security_events=security_events,
                        severity=ValidationSeverity.ERROR,
                        original_value=response_data
                    )
                elif expected_type == 'boolean' and not isinstance(value, bool):
                    security_events.append(f"Expected boolean for key '{key}', got {type(value)}")
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value={},
                        security_events=security_events,
                        severity=ValidationSeverity.ERROR,
                        original_value=response_data
                    )
                elif expected_type == 'array' and not isinstance(value, list):
                    security_events.append(f"Expected array for key '{key}', got {type(value)}")
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value={},
                        security_events=security_events,
                        severity=ValidationSeverity.ERROR,
                        original_value=response_data
                    )
                elif expected_type == 'object' and not isinstance(value, dict):
                    security_events.append(f"Expected object for key '{key}', got {type(value)}")
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value={},
                        security_events=security_events,
                        severity=ValidationSeverity.ERROR,
                        original_value=response_data
                    )

            # Length/range validation
            if 'max_length' in schema_def and isinstance(value, str):
                if len(value) > schema_def['max_length']:
                    security_events.append(f"Value for key '{key}' exceeds maximum length")
                    if self.strict_mode:
                        return ValidationResult(
                            is_valid=False,
                            sanitized_value={},
                            security_events=security_events,
                            severity=ValidationSeverity.ERROR,
                            original_value=response_data
                        )
                    value = value[:schema_def['max_length']]

            if 'min_value' in schema_def and isinstance(value, (int, float)):
                if value < schema_def['min_value']:
                    security_events.append(f"Value for key '{key}' below minimum")
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value={},
                        security_events=security_events,
                        severity=ValidationSeverity.ERROR,
                        original_value=response_data
                    )

            if 'max_value' in schema_def and isinstance(value, (int, float)):
                if value > schema_def['max_value']:
                    security_events.append(f"Value for key '{key}' exceeds maximum")
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value={},
                        security_events=security_events,
                        severity=ValidationSeverity.ERROR,
                        original_value=response_data
                    )

            # Pattern validation for strings
            if 'pattern' in schema_def and isinstance(value, str):
                pattern = re.compile(schema_def['pattern'])
                if not pattern.match(value):
                    security_events.append(f"Value for key '{key}' doesn't match required pattern")
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value={},
                        security_events=security_events,
                        severity=ValidationSeverity.ERROR,
                        original_value=response_data
                    )

            # Sanitize string values
            if isinstance(value, str):
                injection_patterns = self._check_injection_patterns(value, f"API response field '{key}'")
                security_events.extend(injection_patterns)
                if injection_patterns and self.strict_mode:
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value={},
                        security_events=security_events,
                        severity=ValidationSeverity.ERROR,
                        original_value=response_data
                    )
                # Basic sanitization
                value = value.replace('\x00', '')

            validated_data[key] = value

        is_valid = len([e for e in security_events if 'ERROR' in e or 'CRITICAL' in e]) == 0

        return ValidationResult(
            is_valid=is_valid,
            sanitized_value=validated_data,
            security_events=security_events,
            severity=ValidationSeverity.WARNING if not is_valid else ValidationSeverity.INFO,
            original_value=response_data
        )

    def sanitize_config_value(self, key: str, value: Any,
                            config_schema: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Sanitize and validate configuration value.

        Args:
            key: Configuration key
            value: Configuration value to validate
            config_schema: Optional schema for validation

        Returns:
            ValidationResult with sanitized value and security events
        """
        security_events = []

        # Validate key
        if not isinstance(key, str):
            security_events.append("Configuration key must be a string")
            return ValidationResult(
                is_valid=False,
                sanitized_value=None,
                security_events=security_events,
                severity=ValidationSeverity.ERROR,
                original_value=value
            )

        # Check key for injection patterns
        key_injection = self._check_injection_patterns(key, "configuration key")
        security_events.extend(key_injection)

        if config_schema and key in config_schema:
            schema_def = config_schema[key]
            expected_type = schema_def.get('type')

            # Type validation according to schema
            if expected_type == 'string':
                if not isinstance(value, str):
                    security_events.append(f"Expected string for config key '{key}'")
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value="",
                        security_events=security_events,
                        severity=ValidationSeverity.ERROR,
                        original_value=value
                    )
                # Sanitize string values
                injection_patterns = self._check_injection_patterns(value, f"config value '{key}'")
                security_events.extend(injection_patterns)
                if injection_patterns and self.strict_mode:
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value="",
                        security_events=security_events,
                        severity=ValidationSeverity.ERROR,
                        original_value=value
                    )
                value = value.replace('\x00', '')

            elif expected_type == 'integer':
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    security_events.append(f"Expected integer for config key '{key}'")
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value=0,
                        security_events=security_events,
                        severity=ValidationSeverity.ERROR,
                        original_value=value
                    )

            elif expected_type == 'float':
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    security_events.append(f"Expected float for config key '{key}'")
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value=0.0,
                        security_events=security_events,
                        severity=ValidationSeverity.ERROR,
                        original_value=value
                    )

            elif expected_type == 'boolean':
                if isinstance(value, str):
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif not isinstance(value, bool):
                    value = bool(value)

            # Range validation
            if 'min_value' in schema_def and isinstance(value, (int, float)):
                if value < schema_def['min_value']:
                    security_events.append(f"Config value '{key}' below minimum")
                    value = schema_def['min_value']

            if 'max_value' in schema_def and isinstance(value, (int, float)):
                if value > schema_def['max_value']:
                    security_events.append(f"Config value '{key}' exceeds maximum")
                    value = schema_def['max_value']

        else:
            # Generic sanitization when no schema is provided
            if isinstance(value, str):
                injection_patterns = self._check_injection_patterns(value, f"config value '{key}'")
                security_events.extend(injection_patterns)
                if injection_patterns and self.strict_mode:
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value="",
                        security_events=security_events,
                        severity=ValidationSeverity.ERROR,
                        original_value=value
                    )
                value = value.replace('\x00', '')

        is_valid = len([e for e in security_events if 'ERROR' in e or 'CRITICAL' in e]) == 0

        return ValidationResult(
            is_valid=is_valid,
            sanitized_value=value,
            security_events=security_events,
            severity=ValidationSeverity.WARNING if not is_valid else ValidationSeverity.INFO,
            original_value=value
        )

    def sanitize_user_input(self, user_input: str, max_length: int = 10000) -> ValidationResult:
        """
        Sanitize and validate natural language user input.

        Args:
            user_input: User input string to sanitize
            max_length: Maximum allowed input length

        Returns:
            ValidationResult with sanitized input and security events
        """
        if not isinstance(user_input, str):
            return ValidationResult(
                is_valid=False,
                sanitized_value="",
                security_events=["User input must be a string"],
                severity=ValidationSeverity.ERROR,
                original_value=user_input
            )

        original_input = user_input
        security_events = []

        # Check length
        if len(user_input) > max_length:
            security_events.append(f"User input exceeds maximum length of {max_length}")
            user_input = user_input[:max_length]

        # Check for injection patterns
        injection_patterns = self._check_injection_patterns(user_input, "user input")
        security_events.extend(injection_patterns)

        # Remove dangerous characters while preserving natural language
        # Remove null bytes and control characters except newlines and tabs
        user_input = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', user_input)

        # Normalize whitespace
        user_input = re.sub(r'\s+', ' ', user_input).strip()

        # Check for obviously malicious content
        malicious_patterns = [
            r"(?i)(password|passwd|secret|token|key)\s*[:=]\s*['\"][^'\"]+['\"]",
            r"(?i)(exec|system|eval)\s*\(",
            r"(?i)(drop\s+table|delete\s+from|insert\s+into)",
        ]

        for pattern in malicious_patterns:
            if re.search(pattern, user_input):
                security_events.append(f"Potentially malicious pattern detected: {pattern}")
                if self.strict_mode:
                    return ValidationResult(
                        is_valid=False,
                        sanitized_value="",
                        security_events=security_events,
                        severity=ValidationSeverity.CRITICAL,
                        original_value=original_input
                    )

        is_valid = len(injection_patterns) == 0

        return ValidationResult(
            is_valid=is_valid,
            sanitized_value=user_input,
            security_events=security_events,
            severity=ValidationSeverity.WARNING if injection_patterns else ValidationSeverity.INFO,
            original_value=original_input
        )

    def get_security_summary(self) -> Dict[str, Any]:
        """Get summary of security events from this session."""
        error_count = sum(1 for event in self.security_events if 'ERROR' in event or 'CRITICAL' in event)
        warning_count = sum(1 for event in self.security_events if 'WARNING' in event)

        return {
            'total_events': len(self.security_events),
            'error_events': error_count,
            'warning_events': warning_count,
            'recent_events': self.security_events[-10:] if self.security_events else [],
            'strict_mode': self.strict_mode
        }

    def clear_security_events(self) -> None:
        """Clear security events log."""
        self.security_events.clear()


# Global sanitizer instance
_default_sanitizer = InputSanitizer()

def get_sanitizer(strict_mode: bool = False) -> InputSanitizer:
    """Get a sanitizer instance with specified strict mode."""
    if strict_mode != _default_sanitizer.strict_mode:
        return InputSanitizer(strict_mode=strict_mode)
    return _default_sanitizer