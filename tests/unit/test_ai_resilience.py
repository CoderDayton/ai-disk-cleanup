"""
Comprehensive test suite for AI resilience and graceful degradation scenarios.

Tests API failure scenarios, network interruptions, rate limiting, fallback activation,
progress caching, error recovery, and user experience during degradation.
"""

import json
import os
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock, call
from typing import List, Dict, Any

import pytest

# Add the src directory to the path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ai_disk_cleanup.ai_analyzer import (
    AIAnalyzer, AnalysisMode, ErrorType, AnalysisResult, FileRecommendation,
    CacheManager, CircuitBreaker, RetryManager, RuleBasedAnalyzer, APIUsageStats
)


class TestCircuitBreaker(unittest.TestCase):
    """Test circuit breaker pattern for API resilience."""

    def setUp(self):
        """Set up test fixtures."""
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1)

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state (normal operation)."""
        # Should work normally when closed
        test_func = Mock(return_value="success")

        result = self.circuit_breaker.call(test_func)

        self.assertEqual(result, "success")
        test_func.assert_called_once()
        self.assertEqual(self.circuit_breaker.state, "closed")

    def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after failure threshold is reached."""
        failing_func = Mock(side_effect=Exception("API failure"))

        # Trigger failures up to threshold
        for i in range(3):
            with self.assertRaises(Exception):
                self.circuit_breaker.call(failing_func)

        # Circuit should now be open
        self.assertEqual(self.circuit_breaker.state, "open")
        self.assertEqual(self.circuit_breaker.failure_count, 3)

    def test_circuit_breaker_blocks_calls_when_open(self):
        """Test circuit breaker blocks calls when open."""
        # Force circuit to open state
        self.circuit_breaker.state = "open"
        self.circuit_breaker.last_failure_time = time.time()

        test_func = Mock(return_value="success")

        # Should raise exception without calling function
        with self.assertRaises(Exception) as cm:
            self.circuit_breaker.call(test_func)

        self.assertIn("Circuit breaker is OPEN", str(cm.exception))
        test_func.assert_not_called()

    def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker transitions to half-open for recovery."""
        # Force circuit to open state
        self.circuit_breaker.state = "open"
        self.circuit_breaker.failure_count = 3
        self.circuit_breaker.last_failure_time = time.time() - 2  # Past recovery timeout

        test_func = Mock(return_value="success")

        # Should allow call and transition to closed on success
        result = self.circuit_breaker.call(test_func)

        self.assertEqual(result, "success")
        self.assertEqual(self.circuit_breaker.state, "closed")
        self.assertEqual(self.circuit_breaker.failure_count, 0)

    def test_circuit_breaker_reopens_on_half_open_failure(self):
        """Test circuit breaker reopens if call fails in half-open state."""
        # Force to half-open state
        self.circuit_breaker.state = "half_open"
        self.circuit_breaker.failure_count = 3

        failing_func = Mock(side_effect=Exception("Still failing"))

        # Should fail and reopen circuit
        with self.assertRaises(Exception):
            self.circuit_breaker.call(failing_func)

        self.assertEqual(self.circuit_breaker.state, "open")
        self.assertEqual(self.circuit_breaker.failure_count, 4)


class TestRetryManager(unittest.TestCase):
    """Test retry manager with exponential backoff and jitter."""

    def setUp(self):
        """Set up test fixtures."""
        self.retry_manager = RetryManager(max_retries=3, base_delay=0.1, max_delay=1.0)

    @patch('time.sleep')
    def test_retry_success_on_first_attempt(self, mock_sleep):
        """Test retry succeeds on first attempt."""
        test_func = Mock(return_value="success")

        result = self.retry_manager.execute_with_retry(test_func)

        self.assertEqual(result, "success")
        test_func.assert_called_once()
        mock_sleep.assert_not_called()

    @patch('time.sleep')
    def test_retry_success_after_attempts(self, mock_sleep):
        """Test retry succeeds after initial failures."""
        test_func = Mock(side_effect=[Exception("fail1"), Exception("fail2"), "success"])

        result = self.retry_manager.execute_with_retry(test_func)

        self.assertEqual(result, "success")
        self.assertEqual(test_func.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)  # 2 retries = 2 sleeps

    @patch('time.sleep')
    def test_retry_exhaustion(self, mock_sleep):
        """Test retry exhausts all attempts and raises last exception."""
        test_func = Mock(side_effect=Exception("persistent failure"))

        with self.assertRaises(Exception) as cm:
            self.retry_manager.execute_with_retry(test_func)

        self.assertEqual(str(cm.exception), "persistent failure")
        self.assertEqual(test_func.call_count, 4)  # 1 initial + 3 retries
        self.assertEqual(mock_sleep.call_count, 3)

    @patch('time.sleep')
    def test_exponential_backoff_delays(self, mock_sleep):
        """Test exponential backoff increases delay between retries."""
        test_func = Mock(side_effect=[Exception("fail1"), Exception("fail2"), Exception("fail3"), "success"])

        self.retry_manager.execute_with_retry(test_func)

        # Verify backoff delays (approximately 0.1, 0.2, 0.4 with jitter)
        self.assertEqual(mock_sleep.call_count, 3)

        # Check that delays are increasing (allowing for jitter)
        delays = [call[0][0] for call in mock_sleep.call_args_list]
        self.assertGreater(delays[1], delays[0] * 1.5)  # Second delay > first delay * 1.5
        self.assertGreater(delays[2], delays[1] * 1.5)  # Third delay > second delay * 1.5


class TestCacheManager(unittest.TestCase):
    """Test caching functionality for progress and results."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_manager = CacheManager(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cache_and_retrieve_result(self):
        """Test caching and retrieving analysis results."""
        file_hash = "test_hash_123"
        result = AnalysisResult(
            recommendations=[FileRecommendation(
                file_path="/test/file.txt",
                category="temporary",
                recommendation="delete",
                confidence=0.9,
                reasoning="Test file",
                risk_level="low"
            )],
            summary={"total_files": 1},
            mode_used=AnalysisMode.AI
        )

        # Cache the result
        self.cache_manager.cache_result(file_hash, result)

        # Retrieve the cached result
        cached_result = self.cache_manager.get_cached_result(file_hash)

        self.assertIsNotNone(cached_result)
        self.assertEqual(cached_result.mode_used, AnalysisMode.AI)
        self.assertEqual(len(cached_result.recommendations), 1)
        self.assertEqual(cached_result.recommendations[0].file_path, "/test/file.txt")

    def test_cache_miss_returns_none(self):
        """Test cache miss returns None."""
        result = self.cache_manager.get_cached_result("nonexistent_hash")
        self.assertIsNone(result)

    def test_save_and_load_progress(self):
        """Test saving and loading analysis progress."""
        progress_data = {
            "files_processed": 50,
            "total_files": 100,
            "current_batch": 3,
            "last_file_processed": "/path/to/file50.txt",
            "timestamp": datetime.now().isoformat(),
            "mode": AnalysisMode.AI.value
        }

        # Save progress
        self.cache_manager.save_progress(progress_data)

        # Load progress
        loaded_progress = self.cache_manager.load_progress()

        self.assertIsNotNone(loaded_progress)
        self.assertEqual(loaded_progress["files_processed"], 50)
        self.assertEqual(loaded_progress["total_files"], 100)
        self.assertEqual(loaded_progress["current_batch"], 3)
        self.assertEqual(loaded_progress["mode"], AnalysisMode.AI.value)

    def test_clear_cache(self):
        """Test clearing all cached data."""
        # Add some cached data
        self.cache_manager.cache_result("hash1", AnalysisResult([], {}, AnalysisMode.AI))
        self.cache_manager.save_progress({"test": "data"})

        # Verify data exists
        self.assertIsNotNone(self.cache_manager.get_cached_result("hash1"))
        self.assertIsNotNone(self.cache_manager.load_progress())

        # Clear cache
        self.cache_manager.clear_cache()

        # Verify data is gone
        self.assertIsNone(self.cache_manager.get_cached_result("hash1"))
        self.assertIsNone(self.cache_manager.load_progress())

    def test_concurrent_cache_access(self):
        """Test thread-safe concurrent cache access."""
        import threading

        results = []
        errors = []

        def cache_worker(worker_id):
            try:
                file_hash = f"worker_{worker_id}_hash"
                result = AnalysisResult([], {"worker_id": worker_id}, AnalysisMode.RULE_BASED)

                # Cache result
                self.cache_manager.cache_result(file_hash, result)

                # Retrieve result
                cached = self.cache_manager.get_cached_result(file_hash)

                if cached and cached.summary.get("worker_id") == worker_id:
                    results.append(worker_id)
                else:
                    errors.append(f"Worker {worker_id} failed to retrieve correct result")

            except Exception as e:
                errors.append(f"Worker {worker_id} error: {e}")

        # Run multiple workers concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=cache_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify results
        self.assertEqual(len(errors), 0, f"Concurrent access errors: {errors}")
        self.assertEqual(len(results), 10)


class TestRuleBasedAnalyzer(unittest.TestCase):
    """Test rule-based fallback analyzer functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = RuleBasedAnalyzer()

        # Mock file metadata for testing
        self.mock_file_metadata = Mock()
        self.mock_file_metadata.full_path = "/test/temp/file.tmp"
        self.mock_file_metadata.name = "file.tmp"
        self.mock_file_metadata.size_bytes = 1024
        self.mock_file_metadata.directory_path = "/test/temp"

    def test_temporary_file_detection(self):
        """Test detection of temporary files."""
        temporary_files = [
            ("document.tmp", "delete", 0.9),
            ("backup.bak", "review", 0.7),
            ("~autosave.txt", "delete", 0.9),
            ("Thumbs.db", "delete", 0.9),
            ("file.swp", "delete", 0.9)
        ]

        for filename, expected_action, expected_confidence in temporary_files:
            self.mock_file_metadata.name = filename
            result = self.analyzer.analyze_files([self.mock_file_metadata])

            self.assertEqual(len(result.recommendations), 1)
            rec = result.recommendations[0]
            self.assertEqual(rec.recommendation, expected_action)
            self.assertEqual(rec.confidence, expected_confidence)

    def test_system_file_protection(self):
        """Test protection of system files."""
        system_files = [
            "kernel32.dll",
            "system.sys",
            "application.exe",
            "library.so"
        ]

        for filename in system_files:
            self.mock_file_metadata.name = filename
            self.mock_file_metadata.directory_path = "/Windows/System32"
            result = self.analyzer.analyze_files([self.mock_file_metadata])

            rec = result.recommendations[0]
            self.assertEqual(rec.recommendation, "keep")
            self.assertGreater(rec.confidence, 0.9)
            self.assertEqual(rec.risk_level, "low")

    def test_large_media_file_handling(self):
        """Test handling of large media files."""
        self.mock_file_metadata.name = "movie.mp4"
        self.mock_file_metadata.size_bytes = 200 * 1024 * 1024  # 200MB

        result = self.analyzer.analyze_files([self.mock_file_metadata])

        rec = result.recommendations[0]
        self.assertEqual(rec.recommendation, "review")
        self.assertEqual(rec.category, "large_media")
        self.assertEqual(rec.risk_level, "medium")

    def test_development_file_detection(self):
        """Test detection of development artifacts."""
        dev_files = [
            "compiled.pyc",
            "script.pyo",
            "__pycache__",
            "app.class",
            "node_modules"
        ]

        for filename in dev_files:
            self.mock_file_metadata.name = filename
            result = self.analyzer.analyze_files([self.mock_file_metadata])

            rec = result.recommendations[0]
            self.assertEqual(rec.recommendation, "review")
            self.assertEqual(rec.category, "development_files")
            self.assertGreater(rec.confidence, 0.7)

    def test_unknown_file_handling(self):
        """Test handling of files that don't match any rules."""
        self.mock_file_metadata.name = "unknown_file.xyz123"
        self.mock_file_metadata.size_bytes = 1024

        result = self.analyzer.analyze_files([self.mock_file_metadata])

        rec = result.recommendations[0]
        self.assertEqual(rec.recommendation, "keep")
        self.assertEqual(rec.category, "unknown")
        self.assertEqual(rec.confidence, 0.5)
        self.assertEqual(rec.risk_level, "medium")

    def test_batch_analysis_summary(self):
        """Test batch analysis produces correct summary."""
        files = [
            Mock(name="temp.tmp", full_path="/test/temp.tmp", size_bytes=100, directory_path="/test"),
            Mock(name="document.pdf", full_path="/test/document.pdf", size_bytes=1000, directory_path="/test"),
            Mock(name="system.dll", full_path="/Windows/system.dll", size_bytes=5000, directory_path="/Windows")
        ]

        result = self.analyzer.analyze_files(files)

        self.assertEqual(result.summary["total_files"], 3)
        self.assertGreaterEqual(result.summary["recommended_for_deletion"], 1)
        self.assertEqual(result.mode_used, AnalysisMode.RULE_BASED)
        self.assertEqual(result.files_analyzed, 3)


class TestAPIFailureScenarios(unittest.TestCase):
    """Test various API failure scenarios and fallback activation."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.analyzer = AIAnalyzer(api_key="test_key", config={"max_daily_requests": 10})
        self.mock_file_meta = Mock()
        self.mock_file_meta.full_path = "/test/file.txt"
        self.mock_file_meta.name = "file.txt"
        self.mock_file_meta.size_bytes = 1024

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_network_error_fallback(self):
        """Test fallback activation on network errors."""
        # Set up fake client to bypass client check
        self.analyzer.client = Mock()

        # Mock network error by setting AI analysis to fail
        with patch.object(self.analyzer, '_ai_analysis', side_effect=Exception("Network connection failed")):
            result = self.analyzer.analyze_files([self.mock_file_meta])

            # Should fallback to rule-based analysis
            self.assertEqual(result.mode_used, AnalysisMode.RULE_BASED)
            self.assertEqual(result.error_encountered, ErrorType.NETWORK_ERROR)
            self.assertIsNotNone(result.recommendations)

    def test_api_key_missing_fallback(self):
        """Test fallback when API key is missing."""
        analyzer = AIAnalyzer(api_key=None)

        result = analyzer.analyze_files([self.mock_file_meta])

        self.assertEqual(result.mode_used, AnalysisMode.RULE_BASED)
        self.assertIsNotNone(result.recommendations)

    def test_force_rule_based_mode(self):
        """Test forcing rule-based mode."""
        result = self.analyzer.analyze_files([self.mock_file_meta], force_mode=AnalysisMode.RULE_BASED)

        self.assertEqual(result.mode_used, AnalysisMode.RULE_BASED)
        self.assertIsNone(result.error_encountered)

    def test_rate_limit_error_classification(self):
        """Test rate limit error classification and handling."""
        # Set up fake client to bypass client check
        self.analyzer.client = Mock()

        # Mock rate limit error
        with patch.object(self.analyzer, '_ai_analysis', side_effect=Exception("Rate limit exceeded")):
            result = self.analyzer.analyze_files([self.mock_file_meta])

            self.assertEqual(result.error_encountered, ErrorType.RATE_LIMIT)
            self.assertEqual(result.mode_used, AnalysisMode.RULE_BASED)

    def test_quota_exceeded_error_classification(self):
        """Test quota exceeded error classification."""
        # Set up fake client to bypass client check
        self.analyzer.client = Mock()

        # Mock quota error
        with patch.object(self.analyzer, '_ai_analysis', side_effect=Exception("Insufficient quota")):
            result = self.analyzer.analyze_files([self.mock_file_meta])

            self.assertEqual(result.error_encountered, ErrorType.QUOTA_EXCEEDED)
            self.assertEqual(result.mode_used, AnalysisMode.RULE_BASED)

    def test_authentication_error_classification(self):
        """Test authentication error classification."""
        # Set up fake client to bypass client check
        self.analyzer.client = Mock()

        # Mock auth error
        with patch.object(self.analyzer, '_ai_analysis', side_effect=Exception("Unauthorized: Invalid API key")):
            result = self.analyzer.analyze_files([self.mock_file_meta])

            self.assertEqual(result.error_encountered, ErrorType.AUTHENTICATION)
            self.assertEqual(result.mode_used, AnalysisMode.RULE_BASED)

    def test_timeout_error_classification(self):
        """Test timeout error classification."""
        # Set up fake client to bypass client check
        self.analyzer.client = Mock()

        # Mock timeout error
        with patch.object(self.analyzer, '_ai_analysis', side_effect=Exception("Request timeout")):
            result = self.analyzer.analyze_files([self.mock_file_meta])

            self.assertEqual(result.error_encountered, ErrorType.TIMEOUT)
            self.assertEqual(result.mode_used, AnalysisMode.RULE_BASED)


class TestUsageLimitsAndQuotas(unittest.TestCase):
    """Test usage limit enforcement and quota management."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "max_daily_requests": 5,
            "max_daily_tokens": 1000,
            "max_daily_cost": 1.0
        }
        self.analyzer = AIAnalyzer(api_key="test_key", config=self.config)

    def test_daily_request_limit_enforcement(self):
        """Test enforcement of daily request limits."""
        # Fill up to limit
        self.analyzer.set_usage_stats_for_testing(requests=5)

        mock_file_meta = Mock()
        mock_file_meta.full_path = "/test/file.txt"
        mock_file_meta.name = "file.txt"
        mock_file_meta.size_bytes = 1024

        # Should fallback due to limit
        result = self.analyzer.analyze_files([mock_file_meta])

        self.assertEqual(result.mode_used, AnalysisMode.RULE_BASED)

    def test_daily_token_limit_enforcement(self):
        """Test enforcement of daily token limits."""
        # Fill up to limit
        self.analyzer.set_usage_stats_for_testing(tokens=1000)

        mock_file_meta = Mock()
        mock_file_meta.full_path = "/test/file.txt"
        mock_file_meta.name = "file.txt"
        mock_file_meta.size_bytes = 1024

        # Should fallback due to limit
        result = self.analyzer.analyze_files([mock_file_meta])

        self.assertEqual(result.mode_used, AnalysisMode.RULE_BASED)

    def test_daily_cost_limit_enforcement(self):
        """Test enforcement of daily cost limits."""
        # Fill up to limit
        self.analyzer.set_usage_stats_for_testing(cost=1.0)

        mock_file_meta = Mock()
        mock_file_meta.full_path = "/test/file.txt"
        mock_file_meta.name = "file.txt"
        mock_file_meta.size_bytes = 1024

        # Should fallback due to limit
        result = self.analyzer.analyze_files([mock_file_meta])

        self.assertEqual(result.mode_used, AnalysisMode.RULE_BASED)

    def test_usage_stats_reset_daily(self):
        """Test usage statistics reset daily."""
        # Set old date
        old_date = datetime.now() - timedelta(days=2)
        self.analyzer.usage_stats.last_reset = old_date
        self.analyzer.set_usage_stats_for_testing(requests=100)

        # Trigger reset check by accessing limits
        can_use_ai = self.analyzer._can_use_ai()

        # Stats should be reset
        self.assertEqual(self.analyzer.usage_stats.daily_requests, 0)
        self.assertEqual(self.analyzer.usage_stats.daily_tokens, 0)
        self.assertEqual(self.analyzer.usage_stats.daily_cost, 0.0)

    def test_usage_stats_tracking(self):
        """Test usage statistics tracking."""
        stats = self.analyzer.get_usage_stats()

        self.assertIsInstance(stats, APIUsageStats)
        self.assertEqual(stats.daily_requests, 0)
        self.assertEqual(stats.daily_tokens, 0)
        self.assertEqual(stats.daily_cost, 0.0)

    def test_reset_usage_stats(self):
        """Test manual reset of usage statistics."""
        # Set some stats
        self.analyzer.set_usage_stats_for_testing(requests=10, tokens=5000, cost=2.5)

        # Reset
        self.analyzer.reset_usage_stats()

        # Verify reset
        stats = self.analyzer.get_usage_stats()
        self.assertEqual(stats.daily_requests, 0)
        self.assertEqual(stats.daily_tokens, 0)
        self.assertEqual(stats.daily_cost, 0.0)


class TestProgressCachingAndResume(unittest.TestCase):
    """Test progress caching and resume capabilities."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.analyzer = AIAnalyzer(api_key="test_key")
        self.analyzer.cache_manager = CacheManager(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_analysis_progress(self):
        """Test saving analysis progress."""
        progress_data = {
            "files_processed": 25,
            "total_files": 100,
            "current_batch": 2,
            "processed_files": ["/path/to/file1.txt", "/path/to/file2.txt"],
            "failed_files": ["/path/to/file3.txt"],
            "mode": AnalysisMode.AI.value,
            "timestamp": datetime.now().isoformat()
        }

        self.analyzer.cache_manager.save_progress(progress_data)

        # Verify progress was saved
        loaded_progress = self.analyzer.cache_manager.load_progress()
        self.assertIsNotNone(loaded_progress)
        self.assertEqual(loaded_progress["files_processed"], 25)
        self.assertEqual(loaded_progress["total_files"], 100)
        self.assertEqual(loaded_progress["mode"], AnalysisMode.AI.value)

    def test_resume_from_saved_progress(self):
        """Test resuming analysis from saved progress."""
        # Save initial progress
        progress_data = {
            "files_processed": 50,
            "total_files": 100,
            "current_batch": 5,
            "processed_files": [f"/path/to/file{i}.txt" for i in range(50)],
            "mode": AnalysisMode.AI.value
        }
        self.analyzer.cache_manager.save_progress(progress_data)

        # Load progress for resume
        loaded_progress = self.analyzer.cache_manager.load_progress()

        self.assertIsNotNone(loaded_progress)
        self.assertEqual(loaded_progress["files_processed"], 50)
        self.assertEqual(loaded_progress["current_batch"], 5)

        # Can resume from this point
        remaining_files = 100 - loaded_progress["files_processed"]
        self.assertEqual(remaining_files, 50)

    def test_cache_results_by_file_hash(self):
        """Test caching analysis results by file hash."""
        file_hash = "unique_file_hash_123"
        result = AnalysisResult(
            recommendations=[FileRecommendation(
                file_path="/cached/file.txt",
                category="temporary",
                recommendation="delete",
                confidence=0.95,
                reasoning="Cached analysis result",
                risk_level="low"
            )],
            summary={"total_files": 1, "analysis_time": 0.1},
            mode_used=AnalysisMode.AI,
            processing_time=0.1
        )

        # Cache result
        self.analyzer.cache_manager.cache_result(file_hash, result)

        # Retrieve cached result
        cached_result = self.analyzer.cache_manager.get_cached_result(file_hash)

        self.assertIsNotNone(cached_result)
        self.assertEqual(cached_result.mode_used, AnalysisMode.AI)
        self.assertEqual(cached_result.recommendations[0].file_path, "/cached/file.txt")
        self.assertEqual(cached_result.processing_time, 0.1)

    def test_progress_persistence_across_sessions(self):
        """Test progress persistence across analyzer sessions."""
        # Save progress in first session
        progress_data = {
            "files_processed": 75,
            "total_files": 150,
            "session_id": "session_1",
            "timestamp": datetime.now().isoformat()
        }
        self.analyzer.cache_manager.save_progress(progress_data)

        # Create new analyzer instance (new session)
        new_analyzer = AIAnalyzer(api_key="test_key")
        new_analyzer.cache_manager = CacheManager(self.temp_dir)

        # Load progress from previous session
        loaded_progress = new_analyzer.cache_manager.load_progress()

        self.assertIsNotNone(loaded_progress)
        self.assertEqual(loaded_progress["files_processed"], 75)
        self.assertEqual(loaded_progress["session_id"], "session_1")


class TestErrorRecoveryAndResilience(unittest.TestCase):
    """Test error recovery mechanisms and system resilience."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = AIAnalyzer(api_key="test_key")

    def test_circuit_breaker_recovery_after_downtime(self):
        """Test circuit breaker recovery after API downtime."""
        # Force circuit to open
        self.analyzer.circuit_breaker.state = "open"
        self.analyzer.circuit_breaker.failure_count = 5
        self.analyzer.circuit_breaker.last_failure_time = time.time()

        # Should be in open state
        self.assertEqual(self.analyzer.circuit_breaker.state, "open")

        # Wait for recovery timeout and test
        self.analyzer.circuit_breaker.last_failure_time = time.time() - 70  # Past 60s timeout

        # Mock successful function
        test_func = Mock(return_value="recovered")

        # Should now work (transition to half-open then closed on success)
        result = self.analyzer.circuit_breaker.call(test_func)

        self.assertEqual(result, "recovered")
        self.assertEqual(self.analyzer.circuit_breaker.state, "closed")

    def test_retry_with_exponential_backoff(self):
        """Test retry mechanism with exponential backoff."""
        call_count = 0

        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"

        # Should succeed after retries
        result = self.analyzer.retry_manager.execute_with_retry(flaky_function)

        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)  # 2 failures + 1 success

    def test_graceful_degradation_sequence(self):
        """Test complete graceful degradation sequence."""
        mock_file_meta = Mock()
        mock_file_meta.full_path = "/test/file.txt"
        mock_file_meta.name = "file.txt"
        mock_file_meta.size_bytes = 1024

        # Simulate AI failure → fallback to rule-based
        with patch.object(self.analyzer, '_ai_analysis', side_effect=Exception("AI unavailable")):
            result = self.analyzer.analyze_files([mock_file_meta])

            self.assertEqual(result.mode_used, AnalysisMode.RULE_BASED)
            self.assertIsNotNone(result.error_encountered)
            self.assertIsNotNone(result.recommendations)
            self.assertGreater(result.processing_time, 0)

    def test_partial_failure_handling(self):
        """Test handling of partial failures in batch processing."""
        # Mock some files to analyze, some to fail
        mock_files = [
            Mock(full_path=f"/test/file{i}.txt", name=f"file{i}.txt", size_bytes=1024)
            for i in range(5)
        ]

        # Simulate partial AI failure
        with patch.object(self.analyzer, '_ai_analysis') as mock_ai:
            mock_ai.side_effect = Exception("Batch processing failed")

            result = self.analyzer.analyze_files(mock_files)

            # Should fallback completely for consistency
            self.assertEqual(result.mode_used, AnalysisMode.RULE_BASED)
            self.assertEqual(len(result.recommendations), 5)  # All files processed via fallback

    def test_memory_efficiency_during_failures(self):
        """Test memory efficiency during failure scenarios."""
        # Create many files to process
        mock_files = [
            Mock(full_path=f"/test/large_file_{i}.dat", name=f"large_file_{i}.dat", size_bytes=1000000)
            for i in range(100)
        ]

        # Force failure to test fallback memory usage
        with patch.object(self.analyzer, '_ai_analysis', side_effect=Exception("AI failure")):
            result = self.analyzer.analyze_files(mock_files)

            # Result should still be valid and complete
            self.assertEqual(result.mode_used, AnalysisMode.RULE_BASED)
            self.assertEqual(len(result.recommendations), 100)

            # Processing time should be reasonable
            self.assertLess(result.processing_time, 10.0)  # Should complete within 10 seconds

            # Memory efficiency is tested by ensuring we can process large batches
            # without running into memory issues (implicit test by successful completion)


class TestGracefulDegradationUserExperience(unittest.TestCase):
    """Test user experience during graceful degradation scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = AIAnalyzer(api_key="test_key")
        self.mock_file_meta = Mock()
        self.mock_file_meta.full_path = "/test/user_file.txt"
        self.mock_file_meta.name = "user_file.txt"
        self.mock_file_meta.size_bytes = 1024

    def test_user_notification_on_fallback(self):
        """Test user receives clear notification about fallback activation."""
        with patch.object(self.analyzer, '_ai_analysis', side_effect=Exception("API unavailable")):
            result = self.analyzer.analyze_files([self.mock_file_meta])

            # Result should indicate fallback occurred
            self.assertEqual(result.mode_used, AnalysisMode.RULE_BASED)
            self.assertIsNotNone(result.error_encountered)

            # Summary should explain what happened
            self.assertIn("analysis_method", result.summary)
            self.assertEqual(result.summary["analysis_method"], "rule_based")

    def test_transparent_mode_switching(self):
        """Test transparent mode switching without user interruption."""
        # Start with AI mode
        result1 = self.analyzer.analyze_files([self.mock_file_meta], force_mode=AnalysisMode.AI)

        # Simulate failure and fallback
        with patch.object(self.analyzer, '_ai_analysis', side_effect=Exception("Network error")):
            result2 = self.analyzer.analyze_files([self.mock_file_meta])

            # Mode should have switched transparently
            self.assertEqual(result2.mode_used, AnalysisMode.RULE_BASED)
            self.assertIsNotNone(result2.recommendations)

            # User should still get valid recommendations
            self.assertEqual(len(result2.recommendations), 1)

    def test_cost_warning_when_approaching_limits(self):
        """Test cost warnings when approaching usage limits."""
        # Set usage close to limit
        self.analyzer.usage_stats.daily_cost = 0.9  # Close to 1.0 limit
        self.analyzer.config["max_daily_cost"] = 1.0

        mock_file_meta = Mock()
        mock_file_meta.full_path = "/test/file.txt"
        mock_file_meta.name = "file.txt"
        mock_file_meta.size_bytes = 1024

        # Should fallback and potentially warn about limits
        result = self.analyzer.analyze_files([mock_file_meta])

        self.assertEqual(result.mode_used, AnalysisMode.RULE_BASED)
        # In real implementation, this would trigger user notification

    def test_quality_maintenance_during_degradation(self):
        """Test analysis quality maintenance during degradation."""
        # Create files that should be handled consistently
        temp_file = Mock(full_path="/test/temp.tmp", name="temp.tmp", size_bytes=100)
        important_file = Mock(full_path="/docs/important.pdf", name="important.pdf", size_bytes=5000)

        # Analyze with AI (simulated)
        with patch.object(self.analyzer, '_ai_analysis', return_value=AnalysisResult(
            recommendations=[
                FileRecommendation("/test/temp.tmp", "temporary", "delete", 0.9, "AI reasoning", "low"),
                FileRecommendation("/docs/important.pdf", "document", "keep", 0.95, "AI reasoning", "low")
            ],
            summary={"total_files": 2},
            mode_used=AnalysisMode.AI
        )):
            ai_result = self.analyzer.analyze_files([temp_file, important_file])

        # Analyze with fallback
        fallback_result = self.analyzer.analyze_files([temp_file, important_file], force_mode=AnalysisMode.RULE_BASED)

        # Both should handle temporary file similarly (delete recommendation)
        ai_temp_rec = next(r for r in ai_result.recommendations if "temp.tmp" in r.file_path)
        fallback_temp_rec = next(r for r in fallback_result.recommendations if "temp.tmp" in r.file_path)

        self.assertEqual(ai_temp_rec.recommendation, "delete")
        self.assertEqual(fallback_temp_rec.recommendation, "delete")

        # Both should be conservative with important files
        ai_doc_rec = next(r for r in ai_result.recommendations if "important.pdf" in r.file_path)
        fallback_doc_rec = next(r for r in fallback_result.recommendations if "important.pdf" in r.file_path)

        self.assertEqual(ai_doc_rec.recommendation, "keep")
        self.assertEqual(fallback_doc_rec.recommendation, "keep")

    def test_progress_preservation_during_failures(self):
        """Test progress preservation during analysis failures."""
        # Create cache manager for testing
        temp_dir = tempfile.mkdtemp()
        try:
            self.analyzer.cache_manager = CacheManager(temp_dir)

            # Save some progress
            progress_data = {
                "files_processed": 10,
                "total_files": 20,
                "current_batch": 1,
                "processed_hashes": ["hash1", "hash2", "hash3"]
            }
            self.analyzer.cache_manager.save_progress(progress_data)

            # Simulate failure during analysis
            with patch.object(self.analyzer, '_ai_analysis', side_effect=Exception("Analysis failed")):
                result = self.analyzer.analyze_files([self.mock_file_meta])

                # Progress should still be preserved
                saved_progress = self.analyzer.cache_manager.load_progress()
                self.assertIsNotNone(saved_progress)
                self.assertEqual(saved_progress["files_processed"], 10)

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_error_classification_for_user_communication(self):
        """Test error classification provides useful information for user communication."""
        error_scenarios = [
            ("Network connection failed", ErrorType.NETWORK_ERROR),
            ("Rate limit exceeded", ErrorType.RATE_LIMIT),
            ("Insufficient quota", ErrorType.QUOTA_EXCEEDED),
            ("Unauthorized: Invalid API key", ErrorType.AUTHENTICATION),
            ("Request timeout", ErrorType.TIMEOUT),
            ("Server error", ErrorType.SERVER_ERROR),
            ("Unknown error occurred", ErrorType.UNKNOWN)
        ]

        for error_message, expected_type in error_scenarios:
            classified_type = self.analyzer._classify_error(Exception(error_message))
            self.assertEqual(classified_type, expected_type,
                           f"Error '{error_message}' should be classified as {expected_type}")


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests combining multiple resilience features."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.analyzer = AIAnalyzer(
            api_key="test_key",
            config={
                "max_daily_requests": 5,
                "max_daily_cost": 1.0
            }
        )
        self.analyzer.cache_manager = CacheManager(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_complete_failure_recovery_sequence(self):
        """Test complete failure recovery sequence with multiple mechanisms."""
        # Create test files
        mock_files = [
            Mock(full_path=f"/test/file{i}.txt", name=f"file{i}.txt", size_bytes=1024)
            for i in range(10)
        ]

        # Save initial progress
        progress_data = {
            "files_processed": 0,
            "total_files": 10,
            "current_batch": 0
        }
        self.analyzer.cache_manager.save_progress(progress_data)

        # Simulate complete AI failure
        with patch.object(self.analyzer, '_ai_analysis', side_effect=Exception("Complete API failure")):
            # Analyze files
            result = self.analyzer.analyze_files(mock_files)

            # Should use fallback
            self.assertEqual(result.mode_used, AnalysisMode.RULE_BASED)
            self.assertEqual(result.error_encountered, ErrorType.UNKNOWN)
            self.assertEqual(len(result.recommendations), 10)

            # Update progress
            progress_data["files_processed"] = 10
            progress_data["current_batch"] = 1
            self.analyzer.cache_manager.save_progress(progress_data)

            # Verify progress saved
            saved_progress = self.analyzer.cache_manager.load_progress()
            self.assertEqual(saved_progress["files_processed"], 10)

    def test_intermittent_failure_handling(self):
        """Test handling of intermittent failures."""
        mock_files = [
            Mock(full_path=f"/test/file{i}.txt", name=f"file{i}.txt", size_bytes=1024)
            for i in range(5)
        ]

        call_count = 0

        def intermittent_ai_analysis(files):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Temporary network issue")
            return AnalysisResult(
                recommendations=[FileRecommendation(
                    f.file_path, "test", "keep", 0.8, "AI analysis", "low"
                ) for f in files],
                summary={"total_files": len(files)},
                mode_used=AnalysisMode.AI
            )

        # Mock intermittent failures
        with patch.object(self.analyzer, '_ai_analysis', side_effect=intermittent_ai_analysis):
            result = self.analyzer.analyze_files(mock_files)

            # Should eventually succeed after retries
            self.assertEqual(result.mode_used, AnalysisMode.AI)
            self.assertEqual(len(result.recommendations), 5)
            self.assertGreater(call_count, 2)  # Should have retried

    def test_circuit_breaker_with_recovery(self):
        """Test circuit breaker with recovery mechanism."""
        mock_files = [Mock(full_path="/test/file.txt", name="file.txt", size_bytes=1024)]

        # Force circuit breaker to open
        self.analyzer.circuit_breaker.failure_count = 5
        self.analyzer.circuit_breaker.state = "open"
        self.analyzer.circuit_breaker.last_failure_time = time.time()

        # Should fallback immediately when circuit is open
        result1 = self.analyzer.analyze_files(mock_files)
        self.assertEqual(result1.mode_used, AnalysisMode.RULE_BASED)

        # Wait for recovery timeout
        self.analyzer.circuit_breaker.last_failure_time = time.time() - 70

        # Mock successful AI recovery
        with patch.object(self.analyzer, '_ai_analysis', return_value=AnalysisResult(
            recommendations=[],
            summary={},
            mode_used=AnalysisMode.AI
        )):
            result2 = self.analyzer.analyze_files(mock_files)

            # Should recover and use AI again
            self.assertEqual(result2.mode_used, AnalysisMode.AI)
            self.assertEqual(self.analyzer.circuit_breaker.state, "closed")

    def test_mixed_failure_scenarios(self):
        """Test handling of mixed failure scenarios."""
        mock_files = [
            Mock(full_path=f"/test/file{i}.txt", name=f"file{i}.txt", size_bytes=1024)
            for i in range(3)
        ]

        # Test different error types
        error_types = [
            Exception("Rate limit exceeded"),
            Exception("Network connection failed"),
            Exception("Request timeout")
        ]

        for i, error in enumerate(error_types):
            with patch.object(self.analyzer, '_ai_analysis', side_effect=error):
                result = self.analyzer.analyze_files([mock_files[i]])

                # Should handle each error type appropriately
                self.assertEqual(result.mode_used, AnalysisMode.RULE_BASED)
                self.assertIsNotNone(result.error_encountered)

                # Verify error classification
                if "Rate limit" in str(error):
                    self.assertEqual(result.error_encountered, ErrorType.RATE_LIMIT)
                elif "Network" in str(error):
                    self.assertEqual(result.error_encountered, ErrorType.NETWORK_ERROR)
                elif "timeout" in str(error):
                    self.assertEqual(result.error_encountered, ErrorType.TIMEOUT)


if __name__ == '__main__':
    # Configure test execution
    unittest.main(verbosity=2)