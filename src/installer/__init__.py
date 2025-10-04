"""
Cross-platform installer system for AI Disk Cleanup.

This package provides a comprehensive installer system that can generate native
installers for Windows (MSI) and Linux (AppImage) from a single Python codebase.
"""

__version__ = "0.1.0"

from .config import InstallerConfig, ConfigValidationError
from .orchestrator import BuildOrchestrator, BuildError, BuildResult

__all__ = [
    "InstallerConfig",
    "ConfigValidationError",
    "BuildOrchestrator",
    "BuildError",
    "BuildResult",
]