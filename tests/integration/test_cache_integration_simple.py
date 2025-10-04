"""
Simple integration tests for cache manager functionality.
"""

import tempfile
import unittest

from src.ai_disk_cleanup.cache_manager import CacheManager, CacheConfig
from src.ai_disk_cleanup.types import AnalysisResult, FileRecommendation, AnalysisMode


class TestCacheIntegrationSimple(unittest.TestCase):
    """Test cache manager basic integration functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_config = CacheConfig(
            cache_dir=self.temp_dir,
            default_ttl_hours=1,
            max_entries=10
        )
        self.cache_manager = CacheManager(self.cache_config)

        # Create mock file metadata
        self.mock_file_meta = Mock()
        self.mock_file_meta.full_path = '/test/file1.txt'
        self.mock_file_meta.size_bytes = 1024
        self.mock_file_meta.modified_date = '2023-01-01T00:00:00'
        self.mock_file_meta.created_date = '2023-01-01T00:00:00'
        self.mock_file_meta.extension = '.txt'

        # Create analysis result
        self.analysis_result = AnalysisResult(
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

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_end_to_end_caching_workflow(self):
        """Test complete caching workflow."""
        file_list = [self.mock_file_meta]
        analysis_params = {'model': 'gpt-4', 'temperature': 0.1}

        # Initially no cached result
        cached_result = self.cache_manager.get_cached_result(file_list, analysis_params)
        self.assertIsNone(cached_result)
        stats = self.cache_manager.get_stats()
        self.assertEqual(stats.misses, 1)
        self.assertEqual(stats.hits, 0)

        # Cache a result
        self.cache_manager.cache_result(file_list, self.analysis_result, analysis_params)

        # Should have cached result now
        cached_result = self.cache_manager.get_cached_result(file_list, analysis_params)
        self.assertIsNotNone(cached_result)
        self.assertEqual(cached_result.summary, self.analysis_result.summary)

        # Stats should show hit
        stats = self.cache_manager.get_stats()
        self.assertEqual(stats.misses, 1)  # Still 1 miss
        self.assertEqual(stats.hits, 1)    # 1 hit

    def test_cache_persistence_across_instances(self):
        """Test that cache persists across manager instances."""
        file_list = [self.mock_file_meta]
        analysis_params = {'model': 'gpt-4', 'temperature': 0.1}

        # Cache result in first instance
        self.cache_manager.cache_result(file_list, self.analysis_result, analysis_params)
        self.assertEqual(len(self.cache_manager._cache), 1)

        # Create new cache manager instance
        new_cache_manager = CacheManager(self.cache_config)

        # Should load cached data
        self.assertEqual(len(new_cache_manager._cache), 1)

        # Should be able to retrieve cached result
        cached_result = new_cache_manager.get_cached_result(file_list, analysis_params)
        self.assertIsNotNone(cached_result)
        self.assertEqual(cached_result.summary, self.analysis_result.summary)

    def test_cache_invalidation_workflow(self):
        """Test cache invalidation workflow."""
        file_list = [self.mock_file_meta]
        analysis_params = {'model': 'gpt-4', 'temperature': 0.1}

        # Cache result
        self.cache_manager.cache_result(file_list, self.analysis_result, analysis_params)
        self.assertEqual(len(self.cache_manager._cache), 1)

        # Should be able to retrieve
        cached_result = self.cache_manager.get_cached_result(file_list, analysis_params)
        self.assertIsNotNone(cached_result)

        # Invalidate the file
        self.cache_manager.invalidate_file('/test/file1.txt')

        # Should no longer be able to retrieve
        cached_result = self.cache_manager.get_cached_result(file_list, analysis_params)
        self.assertIsNone(cached_result)
        self.assertEqual(len(self.cache_manager._cache), 0)

    def test_cache_info_and_stats(self):
        """Test cache information and statistics."""
        file_list = [self.mock_file_meta]
        analysis_params = {'model': 'gpt-4', 'temperature': 0.1}

        # Initial cache info
        cache_info = self.cache_manager.get_cache_info()
        self.assertEqual(cache_info['stats']['total_entries'], 0)
        self.assertEqual(cache_info['config']['default_ttl_hours'], 1)

        # Cache result
        self.cache_manager.cache_result(file_list, self.analysis_result, analysis_params)

        # Updated cache info
        cache_info = self.cache_manager.get_cache_info()
        self.assertEqual(cache_info['stats']['total_entries'], 1)
        self.assertIn('entries_by_age', cache_info)
        self.assertIn('config', cache_info)

        # Clear cache
        self.cache_manager.invalidate_all()

        # Cache should be empty
        cache_info = self.cache_manager.get_cache_info()
        self.assertEqual(cache_info['stats']['total_entries'], 0)


# Import Mock for test usage
from unittest.mock import Mock


if __name__ == '__main__':
    unittest.main()