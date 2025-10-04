"""
Integration tests for cache manager with AI analyzer.
"""

import tempfile
import unittest
from unittest.mock import Mock, patch

from src.ai_disk_cleanup.ai_analyzer import AIAnalyzer, AnalysisMode
from src.ai_disk_cleanup.cache_manager import CacheConfig
from src.ai_disk_cleanup.types import AnalysisResult, FileRecommendation


class TestCacheIntegration(unittest.TestCase):
    """Test cache manager integration with AI analyzer."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

        # Create cache configuration
        cache_config = CacheConfig(
            cache_dir=self.temp_dir,
            default_ttl_hours=1,
            max_entries=100
        )

        # Create AI analyzer with cache configuration
        self.analyzer_config = {
            'cache': {
                'cache_dir': self.temp_dir,
                'default_ttl_hours': 1,
                'max_entries': 100
            },
            'model': 'gpt-4',
            'temperature': 0.1,
            'max_tokens': 1000
        }

        self.analyzer = AIAnalyzer(
            api_key="test_key",
            config=self.analyzer_config
        )

        # Create mock file metadata
        self.mock_file_meta = Mock()
        self.mock_file_meta.full_path = '/test/file1.txt'
        self.mock_file_meta.size_bytes = 1024
        self.mock_file_meta.modified_date = '2023-01-01T00:00:00'
        self.mock_file_meta.created_date = '2023-01-01T00:00:00'
        self.mock_file_meta.extension = '.txt'

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cache_integration_with_analyzer(self):
        """Test that analyzer uses cache properly."""
        file_list = [self.mock_file_meta]

        # Create expected result
        expected_result = AnalysisResult(
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

        # Mock the AI analysis to avoid API calls
        with patch.object(self.analyzer, '_ai_analysis') as mock_ai_analysis:
            mock_ai_analysis.return_value = expected_result

            # First analysis - should call AI analysis
            result1 = self.analyzer.analyze_files(file_list)
            self.assertEqual(mock_ai_analysis.call_count, 1)
            self.assertIsNotNone(result1)

            # Second analysis with same files - should use cache
            result2 = self.analyzer.analyze_files(file_list)
            self.assertEqual(mock_ai_analysis.call_count, 1)  # Still only called once
            self.assertIsNotNone(result2)

            # Results should be equivalent
            self.assertEqual(result1.summary, result2.summary)

    def test_cache_miss_with_modified_files(self):
        """Test cache miss when files are modified."""
        file_list = [self.mock_file_meta]

        # Create expected result
        expected_result = AnalysisResult(
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

        # Mock the AI analysis
        with patch.object(self.analyzer, '_ai_analysis') as mock_ai_analysis:
            mock_ai_analysis.return_value = expected_result

            # First analysis
            result1 = self.analyzer.analyze_files(file_list)
            self.assertEqual(mock_ai_analysis.call_count, 1)

            # Modify file metadata (simulate file change)
            self.mock_file_meta.size_bytes = 2048

            # Second analysis - should miss cache and call AI again
            result2 = self.analyzer.analyze_files(file_list)
            self.assertEqual(mock_ai_analysis.call_count, 2)  # Called again due to cache miss

    def test_cache_stats_integration(self):
        """Test cache statistics integration."""
        file_list = [self.mock_file_meta]

        # Create expected result
        expected_result = AnalysisResult(
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

        # Mock the AI analysis
        with patch.object(self.analyzer, '_ai_analysis') as mock_ai_analysis:
            mock_ai_analysis.return_value = expected_result

            # Initial cache stats
            initial_stats = self.analyzer.get_performance_stats()
            self.assertEqual(initial_stats['cache_stats']['hits'], 0)
            self.assertEqual(initial_stats['cache_stats']['misses'], 0)

            # First analysis - should be cache miss
            result1 = self.analyzer.analyze_files(file_list)
            stats_after_first = self.analyzer.get_performance_stats()
            self.assertEqual(stats_after_first['cache_stats']['misses'], 1)
            self.assertEqual(stats_after_first['cache_stats']['hits'], 0)

            # Second analysis - should be cache hit
            result2 = self.analyzer.analyze_files(file_list)
            stats_after_second = self.analyzer.get_performance_stats()
            self.assertEqual(stats_after_second['cache_stats']['misses'], 1)  # Still 1 miss
            self.assertEqual(stats_after_second['cache_stats']['hits'], 1)    # 1 hit

    def test_cache_info_integration(self):
        """Test cache information integration."""
        file_list = [self.mock_file_meta]

        # Create expected result
        expected_result = AnalysisResult(
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

        # Mock the AI analysis
        with patch.object(self.analyzer, '_ai_analysis') as mock_ai_analysis:
            mock_ai_analysis.return_value = expected_result

            # Initial cache info
            initial_info = self.analyzer.get_cache_info()
            self.assertEqual(initial_info['stats']['total_entries'], 0)

            # Perform analysis
            result = self.analyzer.analyze_files(file_list)

            # Cache info should show one entry
            final_info = self.analyzer.get_cache_info()
            self.assertEqual(final_info['stats']['total_entries'], 1)
            self.assertEqual(final_info['config']['default_ttl_hours'], 1)

    def test_cache_clear_integration(self):
        """Test cache clearing integration."""
        file_list = [self.mock_file_meta]

        # Create expected result
        expected_result = AnalysisResult(
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

        # Mock the AI analysis
        with patch.object(self.analyzer, '_ai_analysis') as mock_ai_analysis:
            mock_ai_analysis.return_value = expected_result

            # Perform analysis to populate cache
            result = self.analyzer.analyze_files(file_list)
            cache_info = self.analyzer.get_cache_info()
            self.assertEqual(cache_info['stats']['total_entries'], 1)

            # Clear cache
            self.analyzer.clear_cache()

            # Cache should be empty
            cache_info_after_clear = self.analyzer.get_cache_info()
            self.assertEqual(cache_info_after_clear['stats']['total_entries'], 0)


if __name__ == '__main__':
    unittest.main()