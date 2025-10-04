"""
Validation schemas for structured data validation.

This module defines schemas for validating API responses, configuration data,
and other structured inputs to ensure data integrity and security.
"""

from typing import Dict, Any, List


# OpenAI API response schema
OPENAI_RESPONSE_SCHEMA = {
    'choices': {
        'type': 'array',
        'required': True,
        'min_length': 1,
        'max_length': 10,
    },
    'usage': {
        'type': 'object',
        'required': False,
    },
    'id': {
        'type': 'string',
        'required': False,
        'max_length': 100,
    },
    'object': {
        'type': 'string',
        'required': False,
        'max_length': 50,
    },
    'created': {
        'type': 'integer',
        'required': False,
        'min_value': 0,
    },
    'model': {
        'type': 'string',
        'required': False,
        'max_length': 100,
    }
}

# OpenAI choice schema (nested in choices array)
OPENAI_CHOICE_SCHEMA = {
    'index': {
        'type': 'integer',
        'required': True,
        'min_value': 0,
    },
    'message': {
        'type': 'object',
        'required': True,
    },
    'finish_reason': {
        'type': 'string',
        'required': False,
        'max_length': 50,
    }
}

# OpenAI message schema (nested in choice)
OPENAI_MESSAGE_SCHEMA = {
    'role': {
        'type': 'string',
        'required': True,
        'max_length': 20,
        'pattern': r'^(system|user|assistant|tool)$'
    },
    'content': {
        'type': 'string',
        'required': False,
        'max_length': 100000,
    },
    'tool_calls': {
        'type': 'array',
        'required': False,
        'max_length': 10,
    }
}

# OpenAI tool call schema (nested in tool_calls array)
OPENAI_TOOL_CALL_SCHEMA = {
    'id': {
        'type': 'string',
        'required': True,
        'max_length': 100,
        'pattern': r'^call_[a-zA-Z0-9]+$'
    },
    'type': {
        'type': 'string',
        'required': True,
        'max_length': 20,
        'pattern': r'^function$'
    },
    'function': {
        'type': 'object',
        'required': True,
    }
}

# OpenAI function schema (nested in tool call)
OPENAI_FUNCTION_SCHEMA = {
    'name': {
        'type': 'string',
        'required': True,
        'max_length': 100,
        'pattern': r'^[a-zA-Z_][a-zA-Z0-9_]*$'
    },
    'arguments': {
        'type': 'string',
        'required': True,
        'max_length': 50000,
    }
}

# File analysis result schema
FILE_ANALYSIS_RESULT_SCHEMA = {
    'path': {
        'type': 'string',
        'required': True,
        'max_length': 4096,
    },
    'deletion_recommendation': {
        'type': 'string',
        'required': True,
        'max_length': 20,
        'pattern': r'^(delete|keep|review)$'
    },
    'confidence': {
        'type': 'string',
        'required': True,
        'max_length': 20,
        'pattern': r'^(low|medium|high)$'
    },
    'reason': {
        'type': 'string',
        'required': True,
        'max_length': 1000,
    },
    'category': {
        'type': 'string',
        'required': True,
        'max_length': 100,
    },
    'risk_level': {
        'type': 'string',
        'required': True,
        'max_length': 20,
        'pattern': r'^(low|medium|high)$'
    },
    'suggested_action': {
        'type': 'string',
        'required': True,
        'max_length': 500,
    }
}

# Configuration schemas
CONFIG_SCHEMA = {
    'api_key': {
        'type': 'string',
        'max_length': 200,
        'pattern': r'^sk-[a-zA-Z0-9]{48}$'
    },
    'model_name': {
        'type': 'string',
        'max_length': 100,
        'pattern': r'^[a-zA-Z0-9._-]+$'
    },
    'max_tokens': {
        'type': 'integer',
        'min_value': 1,
        'max_value': 100000,
    },
    'temperature': {
        'type': 'float',
        'min_value': 0.0,
        'max_value': 2.0,
    },
    'timeout_seconds': {
        'type': 'integer',
        'min_value': 1,
        'max_value': 300,
    },
    'max_file_size_mb': {
        'type': 'integer',
        'min_value': 1,
        'max_value': 10000,
    },
    'max_files_per_batch': {
        'type': 'integer',
        'min_value': 1,
        'max_value': 1000,
    },
    'cache_enabled': {
        'type': 'boolean',
    },
    'cache_ttl_hours': {
        'type': 'integer',
        'min_value': 1,
        'max_value': 8760,  # 1 year
    },
    'log_level': {
        'type': 'string',
        'max_length': 20,
        'pattern': r'^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$'
    },
    'audit_enabled': {
        'type': 'boolean',
    },
    'security_mode': {
        'type': 'string',
        'max_length': 20,
        'pattern': r'^(strict|normal|permissive)$'
    }
}

# User preference schemas
USER_PREFERENCE_SCHEMA = {
    'default_action': {
        'type': 'string',
        'max_length': 20,
        'pattern': r'^(keep|delete|review)$'
    },
    'confidence_threshold': {
        'type': 'float',
        'min_value': 0.0,
        'max_value': 1.0,
    },
    'show_system_files': {
        'type': 'boolean',
    },
    'show_hidden_files': {
        'type': 'boolean',
    },
    'backup_before_delete': {
        'type': 'boolean',
    },
    'confirm_dangerous_actions': {
        'type': 'boolean',
    },
    'preferred_categories': {
        'type': 'array',
        'max_length': 50,
    },
    'excluded_patterns': {
        'type': 'array',
        'max_length': 100,
    },
    'included_patterns': {
        'type': 'array',
        'max_length': 100,
    }
}

# File metadata schema
FILE_METADATA_SCHEMA = {
    'path': {
        'type': 'string',
        'required': True,
        'max_length': 4096,
    },
    'name': {
        'type': 'string',
        'required': True,
        'max_length': 255,
    },
    'size_bytes': {
        'type': 'integer',
        'required': True,
        'min_value': 0,
        'max_value': 1099511627776,  # 1TB
    },
    'extension': {
        'type': 'string',
        'required': True,
        'max_length': 50,
    },
    'created_date': {
        'type': 'string',
        'required': False,
        'max_length': 50,
    },
    'modified_date': {
        'type': 'string',
        'required': False,
        'max_length': 50,
    },
    'accessed_date': {
        'type': 'string',
        'required': False,
        'max_length': 50,
    },
    'parent_directory': {
        'type': 'string',
        'required': False,
        'max_length': 4096,
    },
    'is_hidden': {
        'type': 'boolean',
        'required': False,
    },
    'is_system': {
        'type': 'boolean',
        'required': False,
    }
}

# Schema for nested validation
NESTED_SCHEMAS = {
    'openai_response': OPENAI_RESPONSE_SCHEMA,
    'openai_choice': OPENAI_CHOICE_SCHEMA,
    'openai_message': OPENAI_MESSAGE_SCHEMA,
    'openai_tool_call': OPENAI_TOOL_CALL_SCHEMA,
    'openai_function': OPENAI_FUNCTION_SCHEMA,
    'file_analysis_result': FILE_ANALYSIS_RESULT_SCHEMA,
    'file_metadata': FILE_METADATA_SCHEMA,
    'config': CONFIG_SCHEMA,
    'user_preferences': USER_PREFERENCE_SCHEMA,
}


def get_schema(schema_name: str) -> Dict[str, Any]:
    """Get schema by name."""
    return NESTED_SCHEMAS.get(schema_name, {})


def validate_nested_structure(data: Dict[str, Any], schema_name: str,
                            validator_func: callable) -> Dict[str, Any]:
    """
    Validate nested structure using specified validator function.

    Args:
        data: Data to validate
        schema_name: Name of schema to use
        validator_func: Validation function to use

    Returns:
        Validated and sanitized data
    """
    schema = get_schema(schema_name)
    if not schema:
        return data

    result = validator_func(data, schema)
    return result.sanitized_value if result.is_valid else {}