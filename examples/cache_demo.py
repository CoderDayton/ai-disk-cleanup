#!/usr/bin/env python3
"""
Demonstration of the AI Disk Cleanup caching system.

This script shows how the advanced caching system improves performance
and reduces API costs by caching AI analysis results.
"""

import os
import tempfile
import time
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_disk_cleanup.cache_manager import CacheManager, CacheConfig
from ai_disk_cleanup.types import AnalysisResult, FileRecommendation, AnalysisMode


def create_mock_file_metadata(path: str, size: int = 1024):
    """Create mock file metadata for demonstration."""
    class MockFileMetadata:
        def __init__(self, path: str, size: int):
            self.full_path = path
            self.name = os.path.basename(path)
            self.size_bytes = size
            self.modified_date = '2023-01-01T00:00:00'
            self.created_date = '2023-01-01T00:00:00'
            self.extension = os.path.splitext(path)[1]

    return MockFileMetadata(path, size)


def create_analysis_result(file_path: str, category: str = "temp"):
    """Create a mock analysis result."""
    recommendation = "delete" if category == "temp" else "keep"
    confidence = 0.9 if category == "temp" else 0.7

    return AnalysisResult(
        recommendations=[FileRecommendation(
            file_path=file_path,
            category=category,
            recommendation=recommendation,
            confidence=confidence,
            reasoning=f"This is a {category} file",
            risk_level="low" if recommendation == "keep" else "medium"
        )],
        summary={
            'total_files': 1,
            'recommended_for_deletion': 1 if recommendation == "delete" else 0,
            'analysis_method': 'ai_cached'
        },
        mode_used=AnalysisMode.AI,
        files_analyzed=1
    )


def simulate_ai_analysis_delay():
    """Simulate the delay of an AI API call."""
    time.sleep(0.1)  # 100ms delay to simulate API call


def demonstrate_caching_performance():
    """Demonstrate the performance benefits of caching."""
    print("🚀 AI Disk Cleanup Caching Performance Demo")
    print("=" * 50)

    # Create temporary cache directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Configure cache
        cache_config = CacheConfig(
            cache_dir=temp_dir,
            default_ttl_hours=1,
            max_entries=100
        )
        cache_manager = CacheManager(cache_config)

        # Create test files
        files = [
            create_mock_file_metadata("/tmp/temp_file1.tmp", 1024),
            create_mock_file_metadata("/tmp/temp_file2.tmp", 2048),
            create_mock_file_metadata("/tmp/document.pdf", 5120),
            create_mock_file_metadata("/tmp/log_file.log", 256),
        ]

        analysis_params = {
            'model': 'gpt-4',
            'temperature': 0.1,
            'max_tokens': 1000,
            'safety_enabled': True
        }

        print(f"📁 Analyzing {len(files)} files...")
        print()

        # First analysis round - no cache
        print("🔍 First Analysis (No Cache):")
        print("-" * 30)

        start_time = time.time()
        first_results = []

        for file_meta in files:
            # Check cache
            cached_result = cache_manager.get_cached_result([file_meta], analysis_params)

            if cached_result:
                print(f"✅ {file_meta.name}: Cache HIT")
                result = cached_result
            else:
                print(f"🔄 {file_meta.name}: Cache MISS - Simulating AI analysis")
                simulate_ai_analysis_delay()

                # Simulate AI analysis
                category = "temp" if file_meta.name.endswith('.tmp') else "document"
                result = create_analysis_result(file_meta.full_path, category)

                # Cache the result
                cache_manager.cache_result([file_meta], result, analysis_params)

            first_results.append(result)

        first_duration = time.time() - start_time
        print(f"⏱️  First analysis completed in {first_duration:.2f} seconds")
        print()

        # Second analysis round - should use cache
        print("🔍 Second Analysis (With Cache):")
        print("-" * 30)

        start_time = time.time()
        second_results = []

        for file_meta in files:
            # Check cache
            cached_result = cache_manager.get_cached_result([file_meta], analysis_params)

            if cached_result:
                print(f"✅ {file_meta.name}: Cache HIT")
                result = cached_result
            else:
                print(f"🔄 {file_meta.name}: Cache MISS - This shouldn't happen!")
                simulate_ai_analysis_delay()

                # Simulate AI analysis
                category = "temp" if file_meta.name.endswith('.tmp') else "document"
                result = create_analysis_result(file_meta.full_path, category)

                # Cache the result
                cache_manager.cache_result([file_meta], result, analysis_params)

            second_results.append(result)

        second_duration = time.time() - start_time
        print(f"⏱️  Second analysis completed in {second_duration:.2f} seconds")
        print()

        # Performance improvement
        speedup = first_duration / second_duration if second_duration > 0 else float('inf')
        print("📊 Performance Results:")
        print("-" * 20)
        print(f"First analysis:  {first_duration:.2f}s")
        print(f"Second analysis: {second_duration:.2f}s")
        print(f"Speedup:         {speedup:.1f}x faster")
        print()

        # Cache statistics
        cache_stats = cache_manager.get_stats()
        print("📈 Cache Statistics:")
        print("-" * 20)
        print(f"Cache hits:       {cache_stats.hits}")
        print(f"Cache misses:     {cache_stats.misses}")
        print(f"Hit rate:         {cache_stats.hit_rate:.1%}")
        print(f"Total entries:    {cache_stats.total_entries}")
        print(f"Cache size:       {cache_stats.cache_size_bytes / 1024:.1f} KB")
        print()

        # Detailed cache information
        cache_info = cache_manager.get_cache_info()
        print("🔧 Cache Configuration:")
        print("-" * 25)
        print(f"Cache directory:  {cache_info['config']['cache_dir']}")
        print(f"Default TTL:      {cache_info['config']['default_ttl_hours']} hours")
        print(f"Max entries:      {cache_info['config']['max_entries']}")
        print(f"Max cache size:   {cache_info['config']['max_cache_size_mb']} MB")
        print()


def demonstrate_cache_invalidation():
    """Demonstrate cache invalidation when files change."""
    print("🔄 Cache Invalidation Demo")
    print("=" * 30)

    with tempfile.TemporaryDirectory() as temp_dir:
        cache_config = CacheConfig(cache_dir=temp_dir)
        cache_manager = CacheManager(cache_config)

        # Create a file and analyze it
        file_meta = create_mock_file_metadata("/tmp/important_file.txt", 1024)
        analysis_params = {'model': 'gpt-4', 'temperature': 0.1}

        print("1. Analyzing file for the first time...")
        cached_result = cache_manager.get_cached_result([file_meta], analysis_params)
        if not cached_result:
            print("   Cache miss - performing analysis")
            result = create_analysis_result(file_meta.full_path, "document")
            cache_manager.cache_result([file_meta], result, analysis_params)

        print("2. Analyzing same file again...")
        cached_result = cache_manager.get_cached_result([file_meta], analysis_params)
        if cached_result:
            print("   ✅ Cache hit - using cached result")

        print("3. Simulating file modification (size change)...")
        file_meta.size_bytes = 2048  # File changed

        print("4. Analyzing modified file...")
        cached_result = cache_manager.get_cached_result([file_meta], analysis_params)
        if not cached_result:
            print("   🔄 Cache miss - file changed, performing new analysis")
            result = create_analysis_result(file_meta.full_path, "document")
            cache_manager.cache_result([file_meta], result, analysis_params)

        print("5. Manual cache invalidation for specific file...")
        cache_manager.invalidate_file("/tmp/important_file.txt")

        print("6. Analyzing after manual invalidation...")
        cached_result = cache_manager.get_cached_result([file_meta], analysis_params)
        if not cached_result:
            print("   🔄 Cache miss - manually invalidated, performing new analysis")

        print()


def main():
    """Run all demonstrations."""
    try:
        demonstrate_caching_performance()
        demonstrate_cache_invalidation()

        print("✅ Demo completed successfully!")
        print("\nKey Benefits of the Caching System:")
        print("• 🚀 Significant performance improvements for repeated analyses")
        print("• 💰 Reduced API costs by avoiding redundant calls")
        print("• 🔄 Automatic cache invalidation when files change")
        print("• 📊 Detailed cache statistics and monitoring")
        print("• ⚙️  Configurable TTL and cache size limits")
        print("• 💾 Persistent cache storage across sessions")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())