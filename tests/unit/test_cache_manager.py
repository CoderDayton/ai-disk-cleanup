"""
Tests for the advanced cache manager functionality.
"""

import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from src.ai_disk_cleanup.cache_manager import (
    CacheManager, CacheConfig, CacheEntry, CacheStats
)
from src.ai_disk_cleanup.types import AnalysisResult, FileRecommendation, AnalysisMode


class TestCacheEntry(unittest.TestCase):
    """Test CacheEntry class."""

    def test_cache_entry_creation(self):
        """Test cache entry creation and basic properties."""
        # Create a mock analysis result
        result = Mock(spec=AnalysisResult)
        file_hashes = {'/test/file1': 'hash1', '/test/file2': 'hash2'}

        entry = CacheEntry(result, file_hashes, ttl_hours=1)

        self.assertEqual(entry.result, result)
        self.assertEqual(entry.file_hashes, file_hashes)
        self.assertEqual(entry.access_count, 0)
        self.assertFalse(entry.is_expired())

    def test_cache_entry_expiration(self):
        """Test cache entry expiration."""
        result = Mock(spec=AnalysisResult)
        file_hashes = {'/test/file1': 'hash1'}

        # Create entry with 1 hour TTL
        entry = CacheEntry(result, file_hashes, ttl_hours=1)
        self.assertFalse(entry.is_expired())

        # Mock time to be 2 hours in the future
        with patch('src.ai_disk_cleanup.cache_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(hours=2)
            self.assertTrue(entry.is_expired())

    def test_cache_entry_access(self):
        """Test cache entry access tracking."""
        result = Mock(spec=AnalysisResult)
        file_hashes = {'/test/file1': 'hash1'}

        entry = CacheEntry(result, file_hashes)
        self.assertEqual(entry.access_count, 0)

        # Access the entry
        accessed_result = entry.access()
        self.assertEqual(accessed_result, result)
        self.assertEqual(entry.access_count, 1)

        # Access again
        entry.access()
        self.assertEqual(entry.access_count, 2)

    def test_cache_entry_validation(self):
        """Test cache entry validation with file hashes."""
        result = Mock(spec=AnalysisResult)
        file_hashes = {'/test/file1': 'hash1', '/test/file2': 'hash2'}

        entry = CacheEntry(result, file_hashes)

        # Valid hashes
        current_hashes = {'/test/file1': 'hash1', '/test/file2': 'hash2'}
        self.assertTrue(entry.is_valid(current_hashes))

        # Invalid hash - file changed
        current_hashes = {'/test/file1': 'hash1_new', '/test/file2': 'hash2'}
        self.assertFalse(entry.is_valid(current_hashes))

        # Missing file
        current_hashes = {'/test/file1': 'hash1'}
        self.assertFalse(entry.is_valid(current_hashes))

        # Expired entry
        with patch('src.ai_disk_cleanup.cache_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(hours=25)
            self.assertFalse(entry.is_valid({'/test/file1': 'hash1'}))

    def test_cache_entry_serialization(self):
        """Test cache entry serialization to/from dict."""
        result = Mock(spec=AnalysisResult)
        file_hashes = {'/test/file1': 'hash1'}

        entry = CacheEntry(result, file_hashes, ttl_hours=24)
        entry.access()  # Increment access count

        # Convert to dict
        entry_dict = entry.to_dict()

        self.assertIn('result', entry_dict)
        self.assertIn('file_hashes', entry_dict)
        self.assertIn('created_at', entry_dict)
        self.assertIn('expires_at', entry_dict)
        self.assertIn('access_count', entry_dict)
        self.assertEqual(entry_dict['access_count'], 1)

        # Convert back from dict
        restored_entry = CacheEntry.from_dict(entry_dict)
        self.assertEqual(restored_entry.result, result)
        self.assertEqual(restored_entry.file_hashes, file_hashes)
        self.assertEqual(restored_entry.access_count, 1)


class TestCacheConfig(unittest.TestCase):
    """Test CacheConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CacheConfig()

        self.assertEqual(config.default_ttl_hours, 24)
        self.assertEqual(config.max_cache_size_mb, 100)
        self.assertEqual(config.max_entries, 10000)
        self.assertEqual(config.cleanup_interval_hours, 6)
        self.assertTrue(config.enable_compression)

    def test_custom_config(self):
        """Test custom configuration values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = CacheConfig(
                cache_dir=temp_dir,
                default_ttl_hours=12,
                max_cache_size_mb=50,
                max_entries=5000,
                cleanup_interval_hours=3,
                enable_compression=False
            )

            self.assertEqual(str(config.cache_dir), temp_dir)
            self.assertEqual(config.default_ttl_hours, 12)
            self.assertEqual(config.max_cache_size_mb, 50)
            self.assertEqual(config.max_entries, 5000)
            self.assertEqual(config.cleanup_interval_hours, 3)
            self.assertFalse(config.enable_compression)


class TestCacheStats(unittest.TestCase):
    """Test CacheStats class."""

    def test_initial_stats(self):
        """Test initial statistics values."""
        stats = CacheStats()

        self.assertEqual(stats.hits, 0)
        self.assertEqual(stats.misses, 0)
        self.assertEqual(stats.evictions, 0)
        self.assertEqual(stats.cleanups, 0)
        self.assertEqual(stats.total_entries, 0)
        self.assertEqual(stats.cache_size_bytes, 0)
        self.assertEqual(stats.hit_rate, 0.0)

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        stats = CacheStats()

        # No accesses yet
        self.assertEqual(stats.hit_rate, 0.0)

        # Some hits and misses
        stats.hits = 8
        stats.misses = 2
        self.assertAlmostEqual(stats.hit_rate, 0.8, places=3)

        # Only hits
        stats.hits = 10
        stats.misses = 0
        self.assertEqual(stats.hit_rate, 1.0)

        # Only misses
        stats.hits = 0
        stats.misses = 10
        self.assertEqual(stats.hit_rate, 0.0)

    def test_stats_to_dict(self):
        """Test stats conversion to dictionary."""
        stats = CacheStats()
        stats.hits = 5
        stats.misses = 3
        stats.cache_size_bytes = 1024

        stats_dict = stats.to_dict()

        self.assertEqual(stats_dict['hits'], 5)
        self.assertEqual(stats_dict['misses'], 3)
        self.assertAlmostEqual(stats_dict['hit_rate'], 0.625, places=3)
        self.assertEqual(stats_dict['cache_size_mb'], 0.0)  # 1024 bytes = 0.0 MB


class TestCacheManager(unittest.TestCase):
    """Test CacheManager class."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_config = CacheConfig(
            cache_dir=self.temp_dir,
            default_ttl_hours=1,
            max_cache_size_mb=1,
            max_entries=10,
            cleanup_interval_hours=1
        )
        self.cache_manager = CacheManager(self.cache_config)

        # Create mock file metadata
        self.mock_file_meta = Mock()
        self.mock_file_meta.full_path = '/test/file1.txt'
        self.mock_file_meta.size_bytes = 1024
        self.mock_file_meta.modified_date = '2023-01-01T00:00:00'
        self.mock_file_meta.created_date = '2023-01-01T00:00:00'
        self.mock_file_meta.extension = '.txt'

        # Create mock analysis result
        self.mock_result = Mock(spec=AnalysisResult)
        self.mock_result.recommendations = [
            FileRecommendation(
                file_path='/test/file1.txt',
                category='test',
                recommendation='keep',
                confidence=0.8,
                reasoning='test reasoning',
                risk_level='low'
            )
        ]
        self.mock_result.summary = {'total_files': 1}
        self.mock_result.mode_used = AnalysisMode.AI
        self.mock_result.files_analyzed = 1

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cache_manager_initialization(self):
        """Test cache manager initialization."""
        self.assertTrue(self.cache_manager.cache_dir.exists())
        self.assertEqual(len(self.cache_manager._cache), 0)
        self.assertIsInstance(self.cache_manager._stats, CacheStats)

    def test_file_hash_generation(self):
        """Test file hash generation."""
        file_hash = self.cache_manager._get_file_hash(self.mock_file_meta)

        self.assertIsInstance(file_hash, str)
        self.assertEqual(len(file_hash), 16)  # SHA256 truncated to 16 chars

        # Same metadata should produce same hash
        file_hash2 = self.cache_manager._get_file_hash(self.mock_file_meta)
        self.assertEqual(file_hash, file_hash2)

        # Different metadata should produce different hash
        different_meta = Mock()
        different_meta.full_path = '/test/file2.txt'
        different_meta.size_bytes = 2048
        different_meta.modified_date = '2023-01-02T00:00:00'
        different_meta.created_date = '2023-01-02T00:00:00'
        different_meta.extension = '.txt'

        different_hash = self.cache_manager._get_file_hash(different_meta)
        self.assertNotEqual(file_hash, different_hash)

    def test_cache_key_generation(self):
        """Test cache key generation."""
        file_list = [self.mock_file_meta]
        analysis_params = {'model': 'gpt-4', 'temperature': 0.1}

        cache_key = self.cache_manager._generate_cache_key(file_list, analysis_params)

        self.assertIsInstance(cache_key, str)
        self.assertEqual(len(cache_key), 32)  # SHA256 truncated to 32 chars

        # Same inputs should produce same key
        cache_key2 = self.cache_manager._generate_cache_key(file_list, analysis_params)
        self.assertEqual(cache_key, cache_key2)

        # Different analysis params should produce different key
        different_params = {'model': 'gpt-3.5-turbo', 'temperature': 0.1}
        different_key = self.cache_manager._generate_cache_key(file_list, different_params)
        self.assertNotEqual(cache_key, different_key)

    def test_cache_result_storage_and_retrieval(self):
        """Test caching and retrieving analysis results."""
        file_list = [self.mock_file_meta]
        analysis_params = {'model': 'gpt-4', 'temperature': 0.1}

        # Cache miss initially
        cached_result = self.cache_manager.get_cached_result(file_list, analysis_params)
        self.assertIsNone(cached_result)
        self.assertEqual(self.cache_manager._stats.misses, 1)

        # Cache the result
        self.cache_manager.cache_result(file_list, self.mock_result, analysis_params)

        # Cache hit now
        cached_result = self.cache_manager.get_cached_result(file_list, analysis_params)
        self.assertIsNotNone(cached_result)
        self.assertEqual(cached_result, self.mock_result)
        self.assertEqual(self.cache_manager._stats.hits, 1)

    def test_cache_ttl_expiration(self):
        """Test cache TTL expiration."""
        file_list = [self.mock_file_meta]
        analysis_params = {'model': 'gpt-4', 'temperature': 0.1}

        # Cache result with short TTL
        self.cache_manager.cache_result(file_list, self.mock_result, analysis_params, ttl_hours=1)

        # Should be available immediately
        cached_result = self.cache_manager.get_cached_result(file_list, analysis_params)
        self.assertIsNotNone(cached_result)

        # Mock time travel to after expiration
        with patch('src.ai_disk_cleanup.cache_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(hours=2)

            # Should be expired now
            cached_result = self.cache_manager.get_cached_result(file_list, analysis_params)
            self.assertIsNone(cached_result)

    def test_cache_invalidation_on_file_change(self):
        """Test cache invalidation when files change."""
        file_list = [self.mock_file_meta]
        analysis_params = {'model': 'gpt-4', 'temperature': 0.1}

        # Cache result
        self.cache_manager.cache_result(file_list, self.mock_result, analysis_params)

        # Should be available
        cached_result = self.cache_manager.get_cached_result(file_list, analysis_params)
        self.assertIsNotNone(cached_result)

        # Change file metadata
        self.mock_file_meta.size_bytes = 2048

        # Should be invalidated
        cached_result = self.cache_manager.get_cached_result(file_list, analysis_params)
        self.assertIsNone(cached_result)

    def test_cache_invalidate_single_file(self):
        """Test invalidating cache entries for a specific file."""
        file_list = [self.mock_file_meta]
        analysis_params = {'model': 'gpt-4', 'temperature': 0.1}

        # Cache result
        self.cache_manager.cache_result(file_list, self.mock_result, analysis_params)
        self.assertEqual(len(self.cache_manager._cache), 1)

        # Invalidate specific file
        self.cache_manager.invalidate_file('/test/file1.txt')

        # Cache should be empty
        self.assertEqual(len(self.cache_manager._cache), 0)

    def test_cache_clear_all(self):
        """Test clearing all cache entries."""
        file_list = [self.mock_file_meta]
        analysis_params = {'model': 'gpt-4', 'temperature': 0.1}

        # Cache multiple results
        self.cache_manager.cache_result(file_list, self.mock_result, analysis_params)
        self.cache_manager.cache_result(file_list, self.mock_result, {'model': 'gpt-3.5-turbo'})

        self.assertEqual(len(self.cache_manager._cache), 2)

        # Clear all
        self.cache_manager.invalidate_all()

        self.assertEqual(len(self.cache_manager._cache), 0)

    def test_cache_cleanup_expired_entries(self):
        """Test cleanup of expired entries."""
        file_list = [self.mock_file_meta]
        analysis_params = {'model': 'gpt-4', 'temperature': 0.1}

        # Cache result with short TTL
        self.cache_manager.cache_result(file_list, self.mock_result, analysis_params, ttl_hours=1)

        self.assertEqual(len(self.cache_manager._cache), 1)

        # Mock time travel to after expiration and force cleanup
        with patch('src.ai_disk_cleanup.cache_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(hours=2)

            self.cache_manager.cleanup(force=True)

        # Cache should be empty
        self.assertEqual(len(self.cache_manager._cache), 0)

    def test_cache_size_limit_eviction(self):
        """Test cache eviction when size limit is exceeded."""
        # Create cache with very small size limit
        small_config = CacheConfig(
            cache_dir=self.temp_dir,
            max_cache_size_mb=0.001,  # 1 KB
            max_entries=3  # Use entry limit instead of size for more predictable behavior
        )
        small_cache = CacheManager(small_config)

        file_list = [self.mock_file_meta]
        analysis_params = {'model': 'gpt-4', 'temperature': 0.1}

        # Cache many results to exceed entry limit
        for i in range(5):
            # Create real result for each iteration
            result = AnalysisResult(
                recommendations=[FileRecommendation(
                    file_path=f'/test/file{i}.txt',
                    category='test',
                    recommendation='keep',
                    confidence=0.8,
                    reasoning='test reasoning',
                    risk_level='low'
                )],
                summary={'total_files': 1},
                mode_used=AnalysisMode.AI,
                files_analyzed=1
            )

            params = {'model': f'gpt-{i}', 'temperature': 0.1}
            small_cache.cache_result(file_list, result, params)

        # Force cleanup to trigger eviction
        small_cache.cleanup(force=True)

        # Cache should have evicted some entries due to entry limit
        self.assertLessEqual(len(small_cache._cache), 3)

    def test_cache_persistence(self):
        """Test cache persistence across manager instances."""
        file_list = [self.mock_file_meta]
        analysis_params = {'model': 'gpt-4', 'temperature': 0.1}

        # Create real result object (not mock) for pickling
        real_result = AnalysisResult(
            recommendations=[FileRecommendation(
                file_path='/test/file1.txt',
                category='test',
                recommendation='keep',
                confidence=0.8,
                reasoning='test reasoning',
                risk_level='low'
            )],
            summary={'total_files': 1},
            mode_used=AnalysisMode.AI,
            files_analyzed=1
        )

        # Cache result in first instance
        self.cache_manager.cache_result(file_list, real_result, analysis_params)
        self.assertEqual(len(self.cache_manager._cache), 1)

        # Create new cache manager instance
        new_cache_manager = CacheManager(self.cache_config)

        # Should load cached data
        self.assertEqual(len(new_cache_manager._cache), 1)

        # Should be able to retrieve cached result
        cached_result = new_cache_manager.get_cached_result(file_list, analysis_params)
        self.assertIsNotNone(cached_result)
        self.assertEqual(cached_result.summary, real_result.summary)

    def test_get_cache_info(self):
        """Test getting detailed cache information."""
        file_list = [self.mock_file_meta]
        analysis_params = {'model': 'gpt-4', 'temperature': 0.1}

        # Cache a result
        self.cache_manager.cache_result(file_list, self.mock_result, analysis_params)

        # Get cache info
        cache_info = self.cache_manager.get_cache_info()

        self.assertIn('config', cache_info)
        self.assertIn('stats', cache_info)
        self.assertIn('entries_by_age', cache_info)
        self.assertIn('last_cleanup', cache_info)

        # Check config info
        config_info = cache_info['config']
        self.assertEqual(config_info['default_ttl_hours'], 1)
        self.assertEqual(config_info['max_cache_size_mb'], 1)
        self.assertEqual(config_info['max_entries'], 10)

        # Check stats
        stats_info = cache_info['stats']
        self.assertEqual(stats_info['total_entries'], 1)

    def test_thread_safety(self):
        """Test thread safety of cache operations."""
        import threading

        file_list = [self.mock_file_meta]
        analysis_params = {'model': 'gpt-4', 'temperature': 0.1}
        results = []
        errors = []

        def cache_and_retrieve():
            try:
                for i in range(5):  # Reduce operations for faster test
                    result = AnalysisResult(
                        recommendations=[FileRecommendation(
                            file_path=f'/test/file{i}.txt',
                            category='test',
                            recommendation='keep',
                            confidence=0.8,
                            reasoning='test reasoning',
                            risk_level='low'
                        )],
                        summary={'total_files': 1},
                        mode_used=AnalysisMode.AI,
                        files_analyzed=1
                    )

                    params = {'model': f'gpt-{i}', 'temperature': 0.1}
                    self.cache_manager.cache_result(file_list, result, params)

                    cached = self.cache_manager.get_cached_result(file_list, params)
                    results.append(cached is not None)
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = []
        for _ in range(3):  # Reduce threads for faster test
            thread = threading.Thread(target=cache_and_retrieve)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check for errors
        self.assertEqual(len(errors), 0, f"Thread safety errors: {errors}")

        # All operations should have succeeded
        expected_operations = 3 * 5  # 3 threads * 5 operations each
        self.assertEqual(len(results), expected_operations)
        self.assertTrue(all(results), "Some cache operations failed")


if __name__ == '__main__':
    unittest.main()