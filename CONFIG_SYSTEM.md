# Configuration Management System

This document describes the configuration management and credential storage system implemented for the AI Disk Cleanup application.

## Overview

The configuration system provides:

- **Secure credential storage** using platform-native keychain/credential managers
- **Structured configuration management** with validation and defaults
- **User preferences persistence** across application restarts
- **Cross-platform compatibility** (Windows, macOS, Linux)

## Components

### Core Components

#### 1. Configuration Models (`src/ai_disk_cleanup/core/config_models.py`)

Defines structured data models using Pydantic:

- `AppConfig`: Main application configuration
- `AIModelConfig`: AI provider and model settings
- `SecurityConfig`: Safety and protection settings
- `UserInterfaceConfig`: UI preferences
- `CleanupConfig`: Cleanup operation settings
- `UserPreferences`: User-specific preferences

#### 2. Configuration Manager (`src/ai_disk_cleanup/core/config_manager.py`)

Manages configuration loading, saving, and validation:

- Loads configuration from YAML/JSON files
- Provides automatic save functionality
- Handles nested configuration updates
- Validates configuration integrity
- Supports configuration export/import

#### 3. Credential Store (`src/ai_disk_cleanup/security/credential_store.py`)

Secure credential storage using platform-native systems:

- **Windows**: Windows Credential Manager
- **macOS**: Keychain Services
- **Linux**: Secret Service API (libsecret)
- **Fallback**: Environment variables and encrypted local storage

## Usage Examples

### Basic Configuration Management

```python
from ai_disk_cleanup.core.config_manager import ConfigManager, get_config

# Initialize configuration manager
manager = ConfigManager(auto_load=True)

# Access configuration
config = get_config()
print(f"AI Provider: {config.ai_model.provider}")

# Update configuration
manager.update_config(
    ai_model__provider="anthropic",
    ai_model__model_name="claude-3",
    security__min_confidence_threshold="very_high"
)

# Update user preferences
manager.update_user_preferences(
    favorite_paths=["/home/user/docs", "/home/user/downloads"]
)
```

### Credential Management

```python
from ai_disk_cleanup.core.config_manager import ConfigManager

manager = ConfigManager()

# Store API key securely
success = manager.set_api_key("openai", "sk-your-api-key-here")

# Retrieve API key
api_key = manager.get_api_key("openai")

# Test API key format
result = manager.test_api_key("openai")
print(f"API Key Valid: {result['valid']}")

# List providers with stored keys
providers = manager.credential_store.list_providers()
```

### Configuration Validation

```python
manager = ConfigManager()

# Validate current configuration
results = manager.validate_config()
print(f"Configuration Valid: {results['valid']}")
print(f"Errors: {results['errors']}")
print(f"Warnings: {results['warnings']}")
```

### Configuration Export/Import

```python
manager = ConfigManager()

# Export configuration
success = manager.export_config("backup_config.yaml")

# Import configuration
success = manager.import_config("backup_config.yaml")
```

## Configuration Files

### Default Locations

- **Linux**: `~/.local/share/ai-disk-cleanup/config.yaml`
- **macOS**: `~/Library/Application Support/ai-disk-cleanup/config.yaml`
- **Windows**: `%APPDATA%/ai-disk-cleanup/config.yaml`

### Configuration Structure

```yaml
app_name: "ai-disk-cleanup"
version: "0.1.0"

ai_model:
  provider: "openai"
  model_name: "gpt-4"
  max_tokens: 4096
  temperature: 0.1
  timeout_seconds: 30

security:
  min_confidence_threshold: "high"
  protected_paths: []
  protected_extensions: [".exe", ".dll", ".sys"]
  require_confirmation: true
  backup_before_delete: true

ui:
  theme: "dark"
  log_level: "INFO"
  show_progress: true
  auto_save_preferences: true

cleanup:
  default_scope: "home_directory"
  file_age_threshold_days: 30
  dry_run_by_default: true
  batch_size: 50
```

## Security Features

### Credential Storage

- **Encryption**: All stored credentials are encrypted using Fernet symmetric encryption
- **Platform Integration**: Uses system credential managers when available
- **Environment Fallback**: Supports environment variables as fallback
- **Key Management**: Encryption keys are stored securely in the credential manager

### API Key Validation

The system validates API key formats for common providers:

- **OpenAI**: Keys starting with `sk-`
- **Anthropic**: Keys starting with `sk-ant-`
- **Generic**: Minimum length validation for other providers

## Configuration Validation

The system performs comprehensive validation:

- **Schema Validation**: Using Pydantic models
- **Data Integrity**: Checks for required fields
- **Security Warnings**: Alerts about missing API keys
- **Directory Validation**: Verifies data directory accessibility

## Testing

Run the test suite:

```bash
# Run all configuration tests
python -m pytest tests/test_config*.py -v

# Run example demonstration
python example_config_usage.py
```

## Environment Variables

The following environment variables are supported:

- `AI_DISK_CLEANUP_CONFIG`: Path to custom configuration file
- `AI_DISK_CLEANUP_ENCRYPTION_KEY`: Custom encryption key
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key
- `GOOGLE_API_KEY`: Google AI API key
- `AZURE_API_KEY`: Azure AI API key

## Error Handling

The system provides robust error handling:

- **Graceful Degradation**: Falls back to defaults when configuration is invalid
- **Detailed Logging**: Comprehensive error messages for debugging
- **Recovery Mechanisms**: Automatic creation of missing directories
- **Validation Feedback**: Clear error messages for configuration issues

## Dependencies

- `pydantic>=2.0.0`: Data validation and serialization
- `keyring>=24.0.0`: Cross-platform credential storage
- `cryptography>=41.0.0`: Encryption and security
- `pyyaml>=6.0`: YAML configuration file support

## Best Practices

1. **Secure Storage**: Always use the credential store for API keys
2. **Validation**: Validate configuration before critical operations
3. **Backups**: Export configuration regularly for backup
4. **Environment-Specific**: Use different configurations for development/production
5. **Minimal Secrets**: Avoid storing secrets in configuration files