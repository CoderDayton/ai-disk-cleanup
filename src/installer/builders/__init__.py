"""
Platform-specific builders for creating native installers.

This package contains builders for different platforms that can generate
native installers from the Python application.
"""

from .base_builder import BaseBuilder

__all__ = ["BaseBuilder"]