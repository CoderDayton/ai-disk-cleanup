"""
Advanced caching manager for AI analysis results with TTL support and cache invalidation.

This module provides persistent caching for AI analysis results to improve performance
and reduce API costs through intelligent caching strategies.
"""

import hashlib
import json
import logging
import os
import pickle
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .types import AnalysisResult, FileRecommendation


class CacheEntry:
    """Single cache entry with metadata."""

    def __init__(self, result: AnalysisResult, file_hashes: Dict[str, str], ttl_hours: int = 24):
        self.result = result
        self.file_hashes = file_hashes  # Maps file paths to their metadata hashes
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(hours=ttl_hours)
        self.access_count = 0
        self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.now() > self.expires_at

    def is_valid(self, current_file_hashes: Dict[str, str]) -> bool:
        """Check if cache entry is still valid based on file changes."""
        if self.is_expired():
            return False

        # Check if any files have changed
        for file_path, cached_hash in self.file_hashes.items():
            current_hash = current_file_hashes.get(file_path)
            if current_hash != cached_hash:
                logging.debug(f"Cache invalidation: {file_path} has changed")
                return False

        return True

    def access(self) -> AnalysisResult:
        """Record access and return cached result."""
        self.access_count += 1
        self.last_accessed = datetime.now()
        return self.result

    def to_dict(self) -> Dict[str, Any]:
        """Convert cache entry to dictionary for serialization."""
        return {
            'result': self.result,
            'file_hashes': self.file_hashes,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'access_count': self.access_count,
            'last_accessed': self.last_accessed.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        """Create cache entry from dictionary."""
        entry = cls.__new__(cls)
        entry.result = data['result']
        entry.file_hashes = data['file_hashes']
        entry.created_at = datetime.fromisoformat(data['created_at'])
        entry.expires_at = datetime.fromisoformat(data['expires_at'])
        entry.access_count = data['access_count']
        entry.last_accessed = datetime.fromisoformat(data['last_accessed'])
        return entry


class CacheConfig:
    """Configuration for cache manager."""

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        default_ttl_hours: int = 24,
        max_cache_size_mb: int = 100,
        max_entries: int = 10000,
        cleanup_interval_hours: int = 6,
        enable_compression: bool = True
    ):
        self.cache_dir = Path(cache_dir or Path.home() / ".ai_disk_cleanup_cache")
        self.default_ttl_hours = default_ttl_hours
        self.max_cache_size_mb = max_cache_size_mb
        self.max_entries = max_entries
        self.cleanup_interval_hours = cleanup_interval_hours
        self.enable_compression = enable_compression


class CacheStats:
    """Cache statistics for monitoring."""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.cleanups = 0
        self.total_entries = 0
        self.cache_size_bytes = 0
        self.last_cleanup = None

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': round(self.hit_rate, 3),
            'evictions': self.evictions,
            'cleanups': self.cleanups,
            'total_entries': self.total_entries,
            'cache_size_mb': round(self.cache_size_bytes / (1024 * 1024), 2),
            'last_cleanup': self.last_cleanup.isoformat() if self.last_cleanup else None
        }


class CacheManager:
    """Advanced cache manager for AI analysis results."""

    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self.cache_dir = self.config.cache_dir
        self.cache_dir.mkdir(exist_ok=True)

        # Cache files
        self.cache_file = self.cache_dir / "analysis_cache_v2.pkl"
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.lock_file = self.cache_dir / "cache.lock"

        # Thread safety
        self._lock = threading.RLock()
        self._file_lock = threading.Lock()

        # In-memory cache
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = CacheStats()
        self._last_cleanup = datetime.now()

        # Load existing cache
        self._load_cache()

        logging.info(f"Cache manager initialized: {self.cache_dir}")

    def _get_file_hash(self, file_metadata: Any) -> str:
        """Generate hash for file metadata."""
        try:
            # Extract relevant metadata for hashing
            metadata_dict = {
                'path': getattr(file_metadata, 'full_path', getattr(file_metadata, 'path', str(file_metadata))),
                'size_bytes': getattr(file_metadata, 'size_bytes', getattr(file_metadata, 'size', 0)),
                'modified_date': getattr(file_metadata, 'modified_date', ''),
                'created_date': getattr(file_metadata, 'created_date', ''),
                'extension': getattr(file_metadata, 'extension', ''),
            }

            # Create hash from metadata
            metadata_str = json.dumps(metadata_dict, sort_keys=True)
            return hashlib.sha256(metadata_str.encode()).hexdigest()[:16]
        except Exception as e:
            logging.warning(f"Failed to generate file hash: {e}")
            # Fallback to path-based hash
            return hashlib.md5(str(file_metadata).encode()).hexdigest()[:16]

    def _generate_cache_key(self, file_metadata_list: List[Any], analysis_params: Dict[str, Any]) -> str:
        """Generate cache key based on file metadata and analysis parameters."""
        try:
            # Create hash from file metadata
            file_hashes = {}
            for file_meta in file_metadata_list:
                file_path = getattr(file_meta, 'full_path', str(file_meta))
                file_hash = self._get_file_hash(file_meta)
                file_hashes[file_path] = file_hash

            # Include analysis parameters in hash
            analysis_key = {
                'file_hashes': sorted(file_hashes.items()),
                'model': analysis_params.get('model', 'default'),
                'temperature': analysis_params.get('temperature', 0.1),
                'max_tokens': analysis_params.get('max_tokens', 4000),
                'safety_enabled': analysis_params.get('safety_enabled', False)
            }

            # Generate final cache key
            key_str = json.dumps(analysis_key, sort_keys=True)
            return hashlib.sha256(key_str.encode()).hexdigest()[:32]
        except Exception as e:
            logging.warning(f"Failed to generate cache key: {e}")
            # Fallback to simple hash
            return hashlib.md5(str(len(file_metadata_list)).encode()).hexdigest()[:16]

    def _should_cleanup(self) -> bool:
        """Check if cache cleanup should be performed."""
        cleanup_delta = timedelta(hours=self.config.cleanup_interval_hours)
        return datetime.now() - self._last_cleanup > cleanup_delta

    def _cleanup_cache(self, force: bool = False):
        """Clean up expired and invalid cache entries."""
        if not force and not self._should_cleanup():
            return

        try:
            with self._lock:
                original_size = len(self._cache)

                # Remove expired entries
                expired_keys = [
                    key for key, entry in self._cache.items()
                    if entry.is_expired()
                ]
                for key in expired_keys:
                    del self._cache[key]

                # Remove old entries if we exceed max entries
                if len(self._cache) > self.config.max_entries:
                    # Sort by last accessed time and remove oldest
                    sorted_entries = sorted(
                        self._cache.items(),
                        key=lambda x: x[1].last_accessed
                    )
                    excess_count = len(self._cache) - self.config.max_entries
                    for key, _ in sorted_entries[:excess_count]:
                        del self._cache[key]
                        self._stats.evictions += 1

                # Check cache size and evict if necessary
                cache_size = self._get_cache_size()
                max_size_bytes = self.config.max_cache_size_mb * 1024 * 1024

                if cache_size > max_size_bytes:
                    # Sort by size and access count
                    sorted_entries = sorted(
                        self._cache.items(),
                        key=lambda x: (x[1].access_count, x[1].last_accessed)
                    )

                    # Remove entries until under size limit
                    for key, entry in sorted_entries:
                        del self._cache[key]
                        self._stats.evictions += 1
                        cache_size = self._get_cache_size()
                        if cache_size <= max_size_bytes * 0.8:  # Leave some buffer
                            break

                removed_count = original_size - len(self._cache)
                if removed_count > 0:
                    logging.debug(f"Cache cleanup removed {removed_count} entries")
                    self._stats.cleanups += 1
                    self._last_cleanup = datetime.now()

                # Update stats
                self._stats.total_entries = len(self._cache)
                self._stats.cache_size_bytes = cache_size
                self._stats.last_cleanup = self._last_cleanup

        except Exception as e:
            logging.error(f"Cache cleanup failed: {e}")

    def _get_cache_size(self) -> int:
        """Get current cache size in bytes."""
        try:
            return len(pickle.dumps(self._cache))
        except Exception:
            return 0

    def _load_cache(self):
        """Load cache from disk."""
        try:
            with self._file_lock:
                if self.cache_file.exists():
                    with open(self.cache_file, 'rb') as f:
                        self._cache = pickle.load(f)
                    logging.info(f"Loaded {len(self._cache)} cache entries")
        except Exception as e:
            logging.warning(f"Failed to load cache: {e}")
            self._cache = {}

        # Clean up on load
        self._cleanup_cache(force=True)

    def _save_cache(self):
        """Save cache to disk."""
        try:
            with self._file_lock:
                # Create backup
                if self.cache_file.exists():
                    backup_file = self.cache_file.with_suffix('.bak')
                    self.cache_file.rename(backup_file)

                # Save cache
                with open(self.cache_file, 'wb') as f:
                    pickle.dump(self._cache, f)

                # Remove backup
                backup_file = self.cache_file.with_suffix('.bak')
                if backup_file.exists():
                    backup_file.unlink()
        except Exception as e:
            logging.error(f"Failed to save cache: {e}")

    def get_cached_result(
        self,
        file_metadata_list: List[Any],
        analysis_params: Optional[Dict[str, Any]] = None
    ) -> Optional[AnalysisResult]:
        """Get cached analysis result if available and valid."""
        analysis_params = analysis_params or {}
        cache_key = self._generate_cache_key(file_metadata_list, analysis_params)

        try:
            with self._lock:
                # Check cache cleanup
                self._cleanup_cache()

                # Look up cache entry
                entry = self._cache.get(cache_key)
                if not entry:
                    self._stats.misses += 1
                    return None

                # Generate current file hashes for validation
                current_hashes = {}
                for file_meta in file_metadata_list:
                    file_path = getattr(file_meta, 'full_path', str(file_meta))
                    current_hashes[file_path] = self._get_file_hash(file_meta)

                # Check if entry is still valid
                if entry.is_valid(current_hashes):
                    self._stats.hits += 1
                    return entry.access()
                else:
                    # Remove invalid entry
                    del self._cache[cache_key]
                    self._stats.misses += 1
                    return None

        except Exception as e:
            logging.error(f"Failed to get cached result: {e}")
            self._stats.misses += 1
            return None

    def cache_result(
        self,
        file_metadata_list: List[Any],
        result: AnalysisResult,
        analysis_params: Optional[Dict[str, Any]] = None,
        ttl_hours: Optional[int] = None
    ):
        """Cache analysis result."""
        analysis_params = analysis_params or {}
        ttl_hours = ttl_hours or self.config.default_ttl_hours
        cache_key = self._generate_cache_key(file_metadata_list, analysis_params)

        try:
            with self._lock:
                # Generate file hashes
                file_hashes = {}
                for file_meta in file_metadata_list:
                    file_path = getattr(file_meta, 'full_path', str(file_meta))
                    file_hashes[file_path] = self._get_file_hash(file_meta)

                # Create cache entry
                entry = CacheEntry(result, file_hashes, ttl_hours)
                self._cache[cache_key] = entry

                # Update stats
                self._stats.total_entries = len(self._cache)
                self._stats.cache_size_bytes = self._get_cache_size()

                # Save cache
                self._save_cache()

                logging.debug(f"Cached analysis result for {len(file_metadata_list)} files")

        except Exception as e:
            logging.error(f"Failed to cache result: {e}")

    def invalidate_file(self, file_path: str):
        """Invalidate cache entries for a specific file."""
        try:
            with self._lock:
                invalidated_keys = []
                for key, entry in self._cache.items():
                    if file_path in entry.file_hashes:
                        invalidated_keys.append(key)

                for key in invalidated_keys:
                    del self._cache[key]

                if invalidated_keys:
                    self._save_cache()
                    logging.info(f"Invalidated {len(invalidated_keys)} cache entries for {file_path}")

        except Exception as e:
            logging.error(f"Failed to invalidate file cache: {e}")

    def invalidate_all(self):
        """Clear all cache entries."""
        try:
            with self._lock:
                self._cache.clear()
                self._save_cache()
                logging.info("Cleared all cache entries")
        except Exception as e:
            logging.error(f"Failed to clear cache: {e}")

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            self._stats.total_entries = len(self._cache)
            self._stats.cache_size_bytes = self._get_cache_size()
            return self._stats

    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information."""
        with self._lock:
            stats = self.get_stats()

            # Calculate additional metrics
            entries_by_age = {}
            now = datetime.now()
            for entry in self._cache.values():
                age_hours = (now - entry.created_at).total_seconds() / 3600
                if age_hours < 1:
                    entries_by_age['<1h'] = entries_by_age.get('<1h', 0) + 1
                elif age_hours < 6:
                    entries_by_age['1-6h'] = entries_by_age.get('1-6h', 0) + 1
                elif age_hours < 24:
                    entries_by_age['6-24h'] = entries_by_age.get('6-24h', 0) + 1
                elif age_hours < 168:  # 1 week
                    entries_by_age['1-7d'] = entries_by_age.get('1-7d', 0) + 1
                else:
                    entries_by_age['>7d'] = entries_by_age.get('>7d', 0) + 1

            return {
                'config': {
                    'cache_dir': str(self.config.cache_dir),
                    'default_ttl_hours': self.config.default_ttl_hours,
                    'max_cache_size_mb': self.config.max_cache_size_mb,
                    'max_entries': self.config.max_entries,
                    'cleanup_interval_hours': self.config.cleanup_interval_hours
                },
                'stats': stats.to_dict(),
                'entries_by_age': entries_by_age,
                'last_cleanup': self._last_cleanup.isoformat()
            }

    def cleanup(self, force: bool = False):
        """Force cache cleanup."""
        self._cleanup_cache(force=force)
        self._save_cache()

    def __del__(self):
        """Cleanup on object destruction."""
        try:
            self._save_cache()
        except Exception:
            pass