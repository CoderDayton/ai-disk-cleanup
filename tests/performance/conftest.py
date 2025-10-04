"""
Performance testing configuration and shared fixtures.

This module provides common configuration and fixtures for performance testing
of the AI disk cleanup tool.
"""

import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch
import pytest
import psutil

from ai_disk_cleanup.openai_client import OpenAIClient, FileMetadata
from ai_disk_cleanup.cache_manager import CacheManager, CacheConfig
from ai_disk_cleanup.core.config_models import AppConfig


class PerformanceTestConfig:
    """Configuration for performance tests."""

    # Performance targets (SDD requirements)
    TARGET_API_RESPONSE_TIME = 3.0  # seconds
    TARGET_COST_PER_SESSION = 0.10  # dollars
    MIN_CACHE_HIT_RATE = 0.8  # 80%
    MAX_MEMORY_PER_FILE = 100 * 1024  # 100KB
    MIN_THROUGHPUT_FILES_PER_SECOND = 10

    # Test configuration
    LARGE_FILE_SET_SIZE = 1000
    CONCURRENT_WORKERS = 5
    MEMORY_TEST_ITERATIONS = 20

    # API simulation
    DEFAULT_API_LATENCY = 1.5  # seconds
    MAX_API_LATENCY = 2.5  # seconds

    @classmethod
    def get_test_data_dir(cls) -> Path:
        """Get test data directory."""
        return Path(__file__).parent / "test_data"

    @classmethod
    def ensure_test_data_dir(cls):
        """Ensure test data directory exists."""
        test_dir = cls.get_test_data_dir()
        test_dir.mkdir(exist_ok=True)
        return test_dir


@pytest.fixture(scope="session")
def perf_config():
    """Performance test configuration."""
    return PerformanceTestConfig()


@pytest.fixture
def mock_app_config():
    """Mock application configuration for testing."""
    return AppConfig(
        ai_model={
            "provider": "openai",
            "model_name": "gpt-4",
            "temperature": 0.1,
            "max_tokens": 4096,
            "timeout_seconds": 30
        },
        cache=CacheConfig(
            cache_dir=tempfile.mkdtemp(prefix="ai_cleanup_test_"),
            default_ttl_hours=1,
            max_cache_size_mb=50,
            max_entries=5000,
            cleanup_interval_hours=1,
            enable_compression=True
        )
    )


@pytest.fixture
def sample_file_metadata_small():
    """Small sample of file metadata for basic testing."""
    return [
        FileMetadata(
            path="/tmp/test_small.tmp",
            name="test_small.tmp",
            size_bytes=1024,
            extension=".tmp",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-01T00:00:00",
            accessed_date="2024-01-01T00:00:00",
            parent_directory="/tmp",
            is_hidden=False,
            is_system=False
        )
    ]


@pytest.fixture
def sample_file_metadata_batch():
    """Standard batch of file metadata for testing."""
    return [
        FileMetadata(
            path=f"/tmp/test_batch_{i}.tmp",
            name=f"test_batch_{i}.tmp",
            size_bytes=1024 * (i + 1),
            extension=".tmp",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-01T00:00:00",
            accessed_date="2024-01-01T00:00:00",
            parent_directory="/tmp",
            is_hidden=i % 10 == 0,
            is_system=i % 20 == 0
        )
        for i in range(50)  # Standard batch size
    ]


@pytest.fixture
def sample_file_metadata_large():
    """Large sample of file metadata for performance testing."""
    return [
        FileMetadata(
            path=f"/tmp/test_large_{i}.tmp",
            name=f"test_large_{i}.tmp",
            size_bytes=1024 * (i % 100 + 1),
            extension=".tmp",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-01T00:00:00",
            accessed_date="2024-01-01T00:00:00",
            parent_directory="/tmp",
            is_hidden=i % 50 == 0,
            is_system=i % 100 == 0
        )
        for i in range(500)
    ]


@pytest.fixture
def mock_openai_response_factory():
    """Factory for creating mock OpenAI API responses."""
    def create_response(num_files: int, base_path: str = "/tmp/test") -> Dict[str, Any]:
        """Create mock response for specified number of files."""
        analyses = []
        for i in range(num_files):
            analyses.append({
                "path": f"{base_path}_{i}.tmp",
                "deletion_recommendation": "delete" if i % 2 == 0 else "keep",
                "confidence": "high",
                "reason": f"Analysis for test file {i}",
                "category": "temporary",
                "risk_level": "low",
                "suggested_action": "Safe to delete"
            })

        return {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "analyze_files_for_cleanup",
                                    "arguments": json.dumps({"file_analyses": analyses})
                                }
                            }
                        ]
                    }
                }
            ]
        }

    return create_response


@pytest.fixture
def mock_openai_client_factory():
    """Factory for creating mock OpenAI clients with realistic behavior."""
    def create_client(api_latency: float = 1.5, response_factory=None):
        """Create a mock OpenAI client with specified latency."""
        mock_client_instance = Mock()
        mock_response = Mock()

        if response_factory is None:
            # Use default response factory
            def default_response_factory(num_files):
                analyses = []
                for i in range(num_files):
                    analyses.append({
                        "path": f"/tmp/test_{i}.tmp",
                        "deletion_recommendation": "delete",
                        "confidence": "high",
                        "reason": "Test file",
                        "category": "temporary",
                        "risk_level": "low",
                        "suggested_action": "Safe to delete"
                    })
                return {
                    "choices": [
                        {
                            "message": {
                                "tool_calls": [
                                    {
                                        "function": {
                                            "name": "analyze_files_for_cleanup",
                                            "arguments": json.dumps({"file_analyses": analyses})
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            response_factory = default_response_factory

        def mock_create(*args, **kwargs):
            """Mock API call with realistic latency."""
            # Simulate API processing time
            time.sleep(api_latency)

            # Determine number of files from request
            messages = kwargs.get('messages', [])
            if messages:
                content = messages[0].get('content', '')
                # Parse content to estimate number of files (simplified)
                if '"path":' in content:
                    file_count = content.count('"path":')
                else:
                    file_count = 50  # Default
            else:
                file_count = 50

            # Create appropriate response
            mock_response.model_dump.return_value = response_factory(file_count)
            return mock_response

        mock_client_instance.chat.completions.create.side_effect = mock_create
        return mock_client_instance

    return create_client


@pytest.fixture
def memory_monitor():
    """Memory monitoring utility for tests."""
    class MemoryMonitor:
        def __init__(self):
            self.process = psutil.Process()
            self.samples = []

        def sample(self, label: str = None):
            """Take a memory sample."""
            memory_info = self.process.memory_info()
            sample = {
                "timestamp": datetime.now(),
                "rss": memory_info.rss,
                "vms": memory_info.vms,
                "label": label
            }
            self.samples.append(sample)
            return sample

        def get_current_rss(self) -> int:
            """Get current RSS memory usage."""
            return self.process.memory_info().rss

        def get_peak_memory(self) -> int:
            """Get peak memory usage from samples."""
            if not self.samples:
                return 0
            return max(sample["rss"] for sample in self.samples)

        def get_memory_increase(self, baseline_sample_idx: int = 0) -> int:
            """Get memory increase since baseline sample."""
            if len(self.samples) <= baseline_sample_idx:
                return 0
            current = self.samples[-1]["rss"]
            baseline = self.samples[baseline_sample_idx]["rss"]
            return current - baseline

        def print_summary(self):
            """Print memory usage summary."""
            if len(self.samples) < 2:
                print("Memory Monitor: Not enough samples for summary")
                return

            initial = self.samples[0]["rss"]
            final = self.samples[-1]["rss"]
            peak = self.get_peak_memory()
            increase = final - initial

            print(f"\nMemory Usage Summary:")
            print(f"  Initial: {initial / 1024 / 1024:.1f}MB")
            print(f"  Final: {final / 1024 / 1024:.1f}MB")
            print(f"  Peak: {peak / 1024 / 1024:.1f}MB")
            print(f"  Increase: {increase / 1024 / 1024:.1f}MB")
            print(f"  Samples: {len(self.samples)}")

        def clear(self):
            """Clear all samples."""
            self.samples.clear()

    return MemoryMonitor()


@pytest.fixture
def performance_logger():
    """Performance logging utility."""
    class PerformanceLogger:
        def __init__(self):
            self.metrics = []

        def log_metric(self, name: str, value: float, unit: str = "",
                      context: Dict[str, Any] = None):
            """Log a performance metric."""
            metric = {
                "name": name,
                "value": value,
                "unit": unit,
                "timestamp": datetime.now(),
                "context": context or {}
            }
            self.metrics.append(metric)

        def log_timing(self, operation: str, duration: float,
                      context: Dict[str, Any] = None):
            """Log a timing metric."""
            self.log_metric(f"{operation}_duration", duration, "seconds", context)

        def log_throughput(self, operation: str, count: int, duration: float,
                          context: Dict[str, Any] = None):
            """Log a throughput metric."""
            throughput = count / duration if duration > 0 else 0
            self.log_metric(f"{operation}_throughput", throughput, "items/sec", context)

        def log_memory(self, operation: str, memory_bytes: int,
                      context: Dict[str, Any] = None):
            """Log a memory metric."""
            self.log_metric(f"{operation}_memory", memory_bytes, "bytes", context)

        def get_metrics(self, name_filter: str = None) -> List[Dict[str, Any]]:
            """Get metrics, optionally filtered by name."""
            if name_filter:
                return [m for m in self.metrics if name_filter in m["name"]]
            return self.metrics.copy()

        def print_summary(self):
            """Print performance summary."""
            if not self.metrics:
                print("Performance Logger: No metrics recorded")
                return

            print(f"\nPerformance Metrics Summary:")
            print(f"Total metrics: {len(self.metrics)}")

            # Group metrics by name
            grouped = {}
            for metric in self.metrics:
                name = metric["name"]
                if name not in grouped:
                    grouped[name] = []
                grouped[name].append(metric)

            for name, metrics in grouped.items():
                values = [m["value"] for m in metrics]
                unit = metrics[0]["unit"]
                avg_val = sum(values) / len(values)
                min_val = min(values)
                max_val = max(values)

                print(f"  {name}:")
                print(f"    Count: {len(metrics)}")
                print(f"    Average: {avg_val:.3f} {unit}")
                print(f"    Min: {min_val:.3f} {unit}")
                print(f"    Max: {max_val:.3f} {unit}")

        def clear(self):
            """Clear all metrics."""
            self.metrics.clear()

    return PerformanceLogger()


@pytest.fixture
def file_metadata_factory():
    """Factory for creating file metadata with various patterns."""
    def create_files(count: int, pattern: str = "simple") -> List[FileMetadata]:
        """Create file metadata with specified pattern."""
        files = []

        for i in range(count):
            if pattern == "simple":
                path = f"/tmp/simple_{i}.tmp"
                name = f"simple_{i}.tmp"
                size = 1024
                parent = "/tmp"

            elif pattern == "deep_paths":
                depth = i % 5 + 1
                path_parts = ["deep"] * depth + [f"file_{i}.tmp"]
                path = "/" + "/".join(path_parts)
                name = f"file_{i}.tmp"
                size = 1024
                parent = "/" + "/".join(path_parts[:-1])

            elif pattern == "varied_sizes":
                path = f"/tmp/varied_{i}.tmp"
                name = f"varied_{i}.tmp"
                size = 1024 * (i % 100 + 1)  # 1KB to 100KB
                parent = "/tmp"

            elif pattern == "hidden_system":
                path = f"/tmp/hidden_{i}.tmp"
                name = f"hidden_{i}.tmp"
                size = 1024
                parent = "/tmp"

            else:  # default
                path = f"/tmp/test_{i}.tmp"
                name = f"test_{i}.tmp"
                size = 1024
                parent = "/tmp"

            metadata = FileMetadata(
                path=path,
                name=name,
                size_bytes=size,
                extension=".tmp",
                created_date="2024-01-01T00:00:00",
                modified_date="2024-01-01T00:00:00",
                accessed_date="2024-01-01T00:00:00",
                parent_directory=parent,
                is_hidden=(pattern == "hidden_system" and i % 3 == 0),
                is_system=(pattern == "hidden_system" and i % 5 == 0)
            )
            files.append(metadata)

        return files

    return create_files


@pytest.fixture
def cache_performance_analyzer():
    """Cache performance analysis utility."""
    class CachePerformanceAnalyzer:
        def __init__(self):
            self.operations = []

        def record_operation(self, operation_type: str, duration: float,
                           result_count: int = 0, cache_hit: bool = None):
            """Record a cache operation."""
            operation = {
                "type": operation_type,
                "duration": duration,
                "result_count": result_count,
                "cache_hit": cache_hit,
                "timestamp": datetime.now()
            }
            self.operations.append(operation)

        def analyze_performance(self) -> Dict[str, Any]:
            """Analyze cache performance."""
            if not self.operations:
                return {"error": "No operations recorded"}

            # Separate hit and miss operations
            hits = [op for op in self.operations if op.get("cache_hit") is True]
            misses = [op for op in self.operations if op.get("cache_hit") is False]
            reads = [op for op in self.operations if op["type"] == "read"]
            writes = [op for op in self.operations if op["type"] == "write"]

            # Calculate statistics
            total_ops = len(self.operations)
            hit_rate = len(hits) / total_ops if total_ops > 0 else 0

            avg_hit_duration = sum(op["duration"] for op in hits) / len(hits) if hits else 0
            avg_miss_duration = sum(op["duration"] for op in misses) / len(misses) if misses else 0
            avg_read_duration = sum(op["duration"] for op in reads) / len(reads) if reads else 0
            avg_write_duration = sum(op["duration"] for op in writes) / len(writes) if writes else 0

            return {
                "total_operations": total_ops,
                "hit_rate": hit_rate,
                "hits": len(hits),
                "misses": len(misses),
                "reads": len(reads),
                "writes": len(writes),
                "avg_hit_duration": avg_hit_duration,
                "avg_miss_duration": avg_miss_duration,
                "avg_read_duration": avg_read_duration,
                "avg_write_duration": avg_write_duration,
                "hit_miss_speedup": avg_miss_duration / avg_hit_duration if avg_hit_duration > 0 else 0
            }

        def print_report(self):
            """Print performance report."""
            analysis = self.analyze_performance()
            if "error" in analysis:
                print(f"Cache Analysis Error: {analysis['error']}")
                return

            print(f"\nCache Performance Analysis:")
            print(f"  Total Operations: {analysis['total_operations']}")
            print(f"  Hit Rate: {analysis['hit_rate']:.1%}")
            print(f"  Hits: {analysis['hits']}, Misses: {analysis['misses']}")
            print(f"  Reads: {analysis['reads']}, Writes: {analysis['writes']}")
            print(f"  Avg Hit Duration: {analysis['avg_hit_duration']:.3f}s")
            print(f"  Avg Miss Duration: {analysis['avg_miss_duration']:.3f}s")
            print(f"  Hit/Miss Speedup: {analysis['hit_miss_speedup']:.1f}x")

        def clear(self):
            """Clear all operations."""
            self.operations.clear()

    return CachePerformanceAnalyzer()


@pytest.fixture
def load_test_runner():
    """Load testing utility for concurrent operations."""
    class LoadTestRunner:
        def __init__(self):
            self.results = []

        def run_concurrent_test(self, worker_func, num_workers: int,
                              iterations_per_worker: int = 1) -> Dict[str, Any]:
            """Run a test with concurrent workers."""
            import concurrent.futures
            import threading

            results = []
            errors = []
            start_time = time.time()

            def worker_wrapper(worker_id):
                """Wrapper for worker function to capture results and errors."""
                try:
                    worker_results = []
                    for iteration in range(iterations_per_worker):
                        result = worker_func(worker_id, iteration)
                        worker_results.append(result)
                    return {"worker_id": worker_id, "results": worker_results, "error": None}
                except Exception as e:
                    return {"worker_id": worker_id, "results": None, "error": str(e)}

            # Run workers
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                future_to_worker = {
                    executor.submit(worker_wrapper, worker_id): worker_id
                    for worker_id in range(num_workers)
                }

                for future in concurrent.futures.as_completed(future_to_worker):
                    worker_id = future_to_worker[future]
                    try:
                        result = future.result()
                        results.append(result)
                        if result["error"]:
                            errors.append(f"Worker {worker_id}: {result['error']}")
                    except Exception as e:
                        errors.append(f"Worker {worker_id}: {str(e)}")

            end_time = time.time()
            total_duration = end_time - start_time

            # Analyze results
            successful_workers = [r for r in results if not r["error"]]
            total_operations = sum(len(r["results"]) for r in successful_workers)
            successful_operations = total_operations - len(errors)

            return {
                "total_duration": total_duration,
                "num_workers": num_workers,
                "iterations_per_worker": iterations_per_worker,
                "total_operations": total_operations,
                "successful_operations": successful_operations,
                "failed_operations": len(errors),
                "success_rate": successful_operations / total_operations if total_operations > 0 else 0,
                "operations_per_second": total_operations / total_duration if total_duration > 0 else 0,
                "errors": errors,
                "worker_results": results
            }

        def print_load_test_report(self, test_result: Dict[str, Any]):
            """Print load test report."""
            print(f"\nLoad Test Results:")
            print(f"  Duration: {test_result['total_duration']:.2f}s")
            print(f"  Workers: {test_result['num_workers']}")
            print(f"  Iterations per Worker: {test_result['iterations_per_worker']}")
            print(f"  Total Operations: {test_result['total_operations']}")
            print(f"  Successful Operations: {test_result['successful_operations']}")
            print(f"  Failed Operations: {test_result['failed_operations']}")
            print(f"  Success Rate: {test_result['success_rate']:.1%}")
            print(f"  Operations per Second: {test_result['operations_per_second']:.1f}")

            if test_result["errors"]:
                print(f"  Errors:")
                for error in test_result["errors"][:5]:  # Show first 5 errors
                    print(f"    {error}")
                if len(test_result["errors"]) > 5:
                    print(f"    ... and {len(test_result['errors']) - 5} more errors")

    return LoadTestRunner()


# Performance test markers
def pytest_configure(config):
    """Configure custom pytest markers for performance tests."""
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "slow_performance: mark test as slow performance test (run with --run-slow)"
    )
    config.addinivalue_line(
        "markers", "memory_test: mark test as memory usage test"
    )
    config.addinivalue_line(
        "markers", "load_test: mark test as load test"
    )
    config.addinivalue_line(
        "markers", "api_test: mark test as API performance test"
    )
    config.addinivalue_line(
        "markers", "cache_test: mark test as cache performance test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add markers based on test location and name
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)

        if any(keyword in item.name.lower() for keyword in [
            "large_file_set", "performance_degradation", "memory_leak"
        ]):
            item.add_marker(pytest.mark.slow_performance)

        if any(keyword in item.name.lower() for keyword in [
            "memory", "leak", "efficiency"
        ]):
            item.add_marker(pytest.mark.memory_test)

        if "load_test" in item.name.lower() or "concurrent" in item.name.lower():
            item.add_marker(pytest.mark.load_test)

        if "response_time" in item.name.lower() or "api" in item.name.lower():
            item.add_marker(pytest.mark.api_test)

        if "cache" in item.name.lower():
            item.add_marker(pytest.mark.cache_test)