"""Configuration data models for AI disk cleanup."""

from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class ConfidenceLevel(str, Enum):
    """AI confidence levels for file classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class ProtectionMode(str, Enum):
    """File protection modes."""
    PROTECT_NONE = "protect_none"
    PROTECT_LOW = "protect_low"
    PROTECT_MEDIUM = "protect_medium"
    PROTECT_HIGH = "protect_high"
    PROTECT_CRITICAL = "protect_critical"


class CleanupScope(str, Enum):
    """Cleanup operation scopes."""
    HOME_DIRECTORY = "home_directory"
    CUSTOM_PATHS = "custom_paths"
    TEMP_FILES = "temp_files"
    SYSTEM_CACHE = "system_cache"


class AIModelConfig(BaseModel):
    """AI model configuration settings."""
    provider: str = Field(default="openai", description="AI provider name")
    model_name: str = Field(default="gpt-4", description="Model name")
    api_base_url: Optional[str] = Field(default=None, description="Custom API base URL")
    max_tokens: int = Field(default=4096, ge=1, le=8192, description="Maximum tokens per request")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="Sampling temperature")
    timeout_seconds: int = Field(default=30, ge=5, le=300, description="Request timeout in seconds")

    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        return round(v, 2)


class SecurityConfig(BaseModel):
    """Security and protection settings."""
    min_confidence_threshold: ConfidenceLevel = Field(
        default=ConfidenceLevel.HIGH,
        description="Minimum confidence level for file deletion"
    )
    protected_paths: List[str] = Field(
        default_factory=list,
        description="List of paths that are always protected"
    )
    protected_extensions: List[str] = Field(
        default_factory=lambda: ['.exe', '.dll', '.sys', '.bat', '.cmd', '.sh'],
        description="File extensions that are always protected"
    )
    protected_patterns: List[str] = Field(
        default_factory=lambda: ['*.system*', '*critical*', '*config*'],
        description="File patterns that are always protected"
    )
    max_file_size_bytes: int = Field(
        default=1024*1024*100,  # 100MB
        ge=0,
        description="Maximum file size to analyze"
    )
    require_confirmation: bool = Field(
        default=True,
        description="Require user confirmation for deletions"
    )
    backup_before_delete: bool = Field(
        default=True,
        description="Create backup before file deletion"
    )
    backup_retention_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Days to retain backup files"
    )


class UserInterfaceConfig(BaseModel):
    """User interface settings."""
    theme: str = Field(default="dark", description="UI theme")
    log_level: str = Field(default="INFO", description="Logging level")
    show_progress: bool = Field(default=True, description="Show progress indicators")
    verbose_output: bool = Field(default=False, description="Enable verbose output")
    language: str = Field(default="en", description="Interface language")
    auto_save_preferences: bool = Field(default=True, description="Auto-save user preferences")


class CleanupConfig(BaseModel):
    """Cleanup operation settings."""
    default_scope: CleanupScope = Field(
        default=CleanupScope.HOME_DIRECTORY,
        description="Default cleanup scope"
    )
    custom_paths: List[str] = Field(
        default_factory=list,
        description="Custom paths to include in cleanup"
    )
    exclude_paths: List[str] = Field(
        default_factory=lambda: [
            "~/.config",
            "~/.ssh",
            "~/.gnupg",
            "~/Documents",
            "~/Desktop"
        ],
        description="Paths to exclude from cleanup"
    )
    file_age_threshold_days: int = Field(
        default=30,
        ge=0,
        description="Minimum file age in days to consider for cleanup"
    )
    dry_run_by_default: bool = Field(
        default=True,
        description="Perform dry run by default"
    )
    batch_size: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Number of files to process in each batch"
    )


class AppConfig(BaseModel):
    """Main application configuration."""
    ai_model: AIModelConfig = Field(default_factory=AIModelConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    ui: UserInterfaceConfig = Field(default_factory=UserInterfaceConfig)
    cleanup: CleanupConfig = Field(default_factory=CleanupConfig)

    # Application metadata
    app_name: str = Field(default="ai-disk-cleanup", description="Application name")
    version: str = Field(default="0.1.0", description="Application version")
    config_version: str = Field(default="1.0", description="Configuration schema version")

    # Data directories
    data_dir: Optional[Path] = Field(default=None, description="Application data directory")
    cache_dir: Optional[Path] = Field(default=None, description="Application cache directory")
    backup_dir: Optional[Path] = Field(default=None, description="Backup directory")

    model_config = {"extra": "forbid"}

    def get_data_dir(self) -> Path:
        """Get the application data directory, creating if necessary."""
        if self.data_dir is None:
            from pathlib import Path
            import os

            # Use platform-specific data directory
            if os.name == 'nt':  # Windows
                data_dir = Path(os.environ.get('APPDATA', '')) / self.app_name
            elif os.name == 'posix':
                if os.name == 'darwin':  # macOS
                    data_dir = Path.home() / 'Library' / 'Application Support' / self.app_name
                else:  # Linux/Unix
                    data_dir = Path.home() / '.local' / 'share' / self.app_name
            else:
                data_dir = Path.home() / f'.{self.app_name}'

            self.data_dir = data_dir

        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir

    def get_cache_dir(self) -> Path:
        """Get the application cache directory, creating if necessary."""
        if self.cache_dir is None:
            import os

            if os.name == 'nt':  # Windows
                cache_dir = Path(os.environ.get('TEMP', '')) / self.app_name
            elif os.name == 'posix':
                if os.name == 'darwin':  # macOS
                    cache_dir = Path.home() / 'Library' / 'Caches' / self.app_name
                else:  # Linux/Unix
                    cache_dir = Path.home() / '.cache' / self.app_name
            else:
                cache_dir = self.get_data_dir() / 'cache'

            self.cache_dir = cache_dir

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        return self.cache_dir

    def get_backup_dir(self) -> Path:
        """Get the backup directory, creating if necessary."""
        if self.backup_dir is None:
            self.backup_dir = self.get_data_dir() / 'backups'

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        return self.backup_dir


class UserPreferences(BaseModel):
    """User-specific preferences and settings."""
    favorite_paths: List[str] = Field(default_factory=list, description="Frequently used paths")
    recent_scans: List[str] = Field(default_factory=list, description="Recent scan locations")
    custom_rules: Dict[str, Any] = Field(default_factory=dict, description="Custom cleanup rules")
    shortcuts: Dict[str, str] = Field(default_factory=dict, description="Keyboard shortcuts")
    last_scan_time: Optional[str] = Field(default=None, description="Last scan timestamp")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="Usage statistics")

    model_config = {"extra": "allow"}