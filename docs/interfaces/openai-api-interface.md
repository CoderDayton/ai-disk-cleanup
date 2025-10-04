# OpenAI API Interface Specification

## Overview

This document defines the interface contract for OpenAI API integration in the AI Directory Cleaner. The interface provides intelligent file analysis capabilities while maintaining user privacy and safety.

## Authentication

### API Key Management
```python
class OpenAIConfig:
    api_key: str  # User-provided OpenAI API key
    model: str = "gpt-3.5-turbo"  # Default model
    max_tokens: int = 1000  # Tokens per request
    temperature: float = 0.3  # Lower temperature for consistent results
    rate_limit: int = 60  # Requests per minute
```

### Configuration Storage
- Store API keys securely in platform-specific credential managers
- Allow user configuration of model and parameters
- Implement rate limiting and cost tracking
- Provide usage statistics and warnings

## File Analysis API

### Input Format
```json
{
  "files": [
    {
      "name": "example.txt",
      "extension": ".txt",
      "size_bytes": 1024,
      "modified_date": "2024-01-15T10:30:00Z",
      "directory_path": "/Users/name/Downloads",
      "file_type": "text/plain"
    }
  ],
  "cleaning_objective": "free_disk_space",
  "user_preferences": {
    "conservative_mode": true,
    "protected_categories": ["work_documents", "photos"]
  }
}
```

### Function Definition
```python
analyze_files_function = {
    "name": "analyze_files_for_deletion",
    "description": "Analyze files and provide deletion recommendations with safety focus",
    "parameters": {
        "type": "object",
        "properties": {
            "files": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/FileMetadata"}
            },
            "cleaning_objective": {
                "type": "string",
                "enum": ["free_disk_space", "remove_duplicates", "organize_files", "custom"]
            }
        },
        "required": ["files", "cleaning_objective"]
    }
}
```

### Expected Output Format
```json
{
  "recommendations": [
    {
      "file_path": "/Users/name/Downloads/temp.txt",
      "category": "temporary_file",
      "recommendation": "delete",
      "confidence": 0.95,
      "reasoning": "File appears to be temporary based on name pattern and location in Downloads folder",
      "risk_level": "low"
    }
  ],
  "summary": {
    "total_files": 10,
    "recommended_for_deletion": 7,
    "high_confidence_deletions": 5,
    "estimated_space_freed": "156.7 MB"
  }
}
```

## Prompt Templates

### Safety-First System Prompt
```
You are an expert file management assistant helping users safely organize their digital files.

Your primary responsibility is user safety and data protection. When uncertain about a file's importance, always recommend keeping it.

Analysis Guidelines:
1. Be conservative - better to keep a file than delete something important
2. Consider file location, name patterns, and typical usage
3. Provide clear reasoning for all recommendations
4. Assign confidence scores based on available information
5. Flag any files that seem potentially important

File Categories:
- temporary_files: Safe to delete (cache, temp, backup files)
- working_files: Keep (active projects, recent documents)
- system_files: Do not delete (OS, application files)
- personal_files: Keep unless clearly redundant (photos, documents)
- duplicate_files: Delete only if clearly redundant and recent backup exists
```

### Analysis Prompts

#### General File Analysis
```
Analyze these files for safe deletion opportunities. Consider:
- File location and typical usage patterns
- File names and extensions
- Modification dates and file sizes
- Common file organization patterns

For each file provide:
1. Category classification
2. Deletion recommendation (keep/delete/review)
3. Confidence score (0.0-1.0)
4. Risk level (low/medium/high)
5. Brief reasoning

Be especially careful with files in user directories, recent files, and documents.
```

#### Duplicate File Analysis
```
Review these potential duplicate files and identify which can be safely removed.

Consider:
- File modification dates (keep newest version)
- File sizes (investigate size differences)
- File locations (prefer organized locations over temp folders)
- File names (prefer descriptive names over generic ones)

Only recommend deletion if you're confident it's a true duplicate and a newer/better version exists.
```

#### Large File Analysis
```
Review these large files and identify candidates for deletion.

Large files require extra caution:
- Consider if these might be important archives, backups, or work files
- Look for patterns indicating old or unused files
- Check if files are in temporary or backup locations
- Consider file types (videos, disk images, archives need special care)

Provide detailed reasoning for any large file deletion recommendations.
```

## Error Handling

### API Error Responses
```python
class APIError(Exception):
    def __init__(self, message, error_type, retry_after=None):
        self.message = message
        self.error_type = error_type  # rate_limit, auth, quota, server_error
        self.retry_after = retry_after

# Error handling strategies
ERROR_HANDLING = {
    "rate_limit": "exponential_backoff",
    "auth": "user_notification",
    "quota": "graceful_degradation",
    "server_error": "retry_with_backoff"
}
```

### Fallback Strategies
1. **Local Rule-Based Analysis**: When API unavailable, use predefined rules
2. **Cached Results**: Use previous analysis results for unchanged files
3. **Partial Analysis**: Process files in smaller batches
4. **User Notification**: Clearly communicate limitations to users

## Rate Limiting and Cost Control

### Usage Monitoring
```python
class UsageTracker:
    daily_requests: int = 0
    daily_tokens: int = 0
    daily_cost: float = 0.0
    last_reset: datetime

    def can_make_request(self, estimated_tokens: int) -> bool:
        return (self.daily_requests < 1000 and
                self.daily_tokens + estimated_tokens < 50000 and
                self.daily_cost < 5.0)
```

### Cost Optimization
- Batch files efficiently to minimize API calls
- Use appropriate models (GPT-3.5-turbo for cost efficiency)
- Implement intelligent caching to avoid re-analysis
- Provide usage warnings and limits to users

## Privacy and Security

### Data Protection
- Never send file contents to OpenAI API
- Only send metadata (name, size, dates, paths)
- Sanitize sensitive information from file paths
- Allow user to opt out of AI analysis entirely

### Secure Communication
- Use HTTPS for all API communications
- Store API keys securely in platform keychain
- Implement proper authentication token management
- Log API calls without sensitive data

## Response Processing

### Confidence Thresholds
```python
CONFIDENCE_THRESHOLDS = {
    "auto_approve": 0.95,      # Automatically approve deletions
    "show_warning": 0.70,      # Show warning but allow approval
    "manual_review": 0.40,     # Require manual review
    "recommend_keep": 0.0      # Keep if confidence below this
}
```

### Risk Assessment
- **Low Risk**: Temporary files, cache files, obvious duplicates
- **Medium Risk**: Old files in user directories, unclear purpose
- **High Risk**: Recent files, important file types, system locations

### Recommendation Categories
1. **Delete Safe**: High confidence temporary files
2. **Review Recommended**: Medium confidence, user should review
3. **Keep**: Low confidence or potentially important files
4. **Protected**: System files, user-specified protected categories