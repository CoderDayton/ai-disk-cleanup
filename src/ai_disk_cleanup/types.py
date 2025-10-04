"""
Shared types and data models for the AI disk cleanup system.

This module contains common types used across multiple modules to avoid circular imports.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class AnalysisMode(Enum):
    """Analysis mode enumeration."""
    AI = "ai"
    RULE_BASED = "rule_based"
    HYBRID = "hybrid"


class ErrorType(Enum):
    """Error type enumeration for categorizing failures."""
    NETWORK_ERROR = "network_error"
    RATE_LIMIT = "rate_limit"
    QUOTA_EXCEEDED = "quota_exceeded"
    AUTHENTICATION = "authentication"
    SERVER_ERROR = "server_error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class FileRecommendation:
    """File deletion recommendation from analysis."""
    file_path: str
    category: str
    recommendation: str  # "delete", "keep", "review"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    risk_level: str  # "low", "medium", "high"


@dataclass
class AnalysisResult:
    """Result of file analysis operation."""
    recommendations: List[FileRecommendation]
    summary: Dict[str, Any]
    mode_used: AnalysisMode
    error_encountered: Optional[ErrorType] = None
    processing_time: float = 0.0
    files_analyzed: int = 0