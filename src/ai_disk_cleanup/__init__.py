"""
AI Disk Cleanup - Intelligent file cleanup with multi-layer safety protection.

This package provides intelligent disk cleanup capabilities with comprehensive safety mechanisms
to prevent accidental data loss. The safety layer includes protection rules, confidence scoring,
and audit trail logging.
"""

__version__ = "0.1.0"
__author__ = "AI Disk Cleanup Team"

# Import main components
from .core.config_manager import ConfigManager, get_config, get_user_preferences
from .core.config_models import AppConfig, UserPreferences
from .security.credential_store import CredentialStore

# Try to import existing components if they exist
try:
    from .safety_layer import SafetyLayer, ProtectionRule, SafetyScore, ProtectionLevel
    from .audit_trail import AuditTrail, SafetyDecision
    from .file_scanner import FileMetadata, FileScanner
    SAFETY_COMPONENTS_AVAILABLE = True
except ImportError:
    SAFETY_COMPONENTS_AVAILABLE = False

__all__ = [
    "ConfigManager",
    "get_config",
    "get_user_preferences",
    "AppConfig",
    "UserPreferences",
    "CredentialStore",
]

# Add safety components if available
if SAFETY_COMPONENTS_AVAILABLE:
    __all__.extend([
        "SafetyLayer",
        "ProtectionRule",
        "SafetyScore",
        "ProtectionLevel",
        "AuditTrail",
        "SafetyDecision",
        "FileMetadata",
        "FileScanner"
    ])