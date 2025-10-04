#!/usr/bin/env python3
"""
Performance test runner for AI Disk Cleanup.

This script provides comprehensive performance testing capabilities including:
- API response time validation (<3 second target)
- Cost control validation (<$0.10 per session)
- Batching optimization efficiency
- Cache performance and hit rate validation
- Large file set performance
- Memory usage and efficiency validation

Usage:
    python run_performance_tests.py --all                    # Run all performance tests
    python run_performance_tests.py --api                    # Run API performance tests only
    python run_performance_tests.py --cache                  # Run cache performance tests only
    python run_performance_tests.py --memory                 # Run memory tests only
    python run_performance_tests.py --load                   # Run load tests only
    python run_performance_tests.py --slow                   # Include slow performance tests
    python run_performance_tests.py --report                 # Generate detailed performance report
"""

import sys
import os
import subprocess
import argparse
import time
import json
from datetime import datetime
from pathlib import Path

def run_command(cmd, cwd=None, timeout=600):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout
        )
        return True, result.stdout, result.stderr
    except subprocess.TimeoutExpired as e:
        return False, e.stdout, f"Command timed out after {timeout}s"
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def run_performance_tests(test_types, include_slow=False, generate_report=False, verbose=False):
    """Run performance tests with specified configuration."""
    project_root = Path(__file__).parent
    os.chdir(project_root)

    print("🚀 AI Disk Cleanup Performance Test Suite")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Test types: {', '.join(test_types)}")
    print(f"Include slow tests: {include_slow}")
    print(f"Generate report: {generate_report}")
    print("=" * 60)

    # Ensure test dependencies are installed
    print("\n📦 Installing test dependencies...")
    success, stdout, stderr = run_command("python -m pip install -e .[test]")
    if not success:
        print(f"❌ Failed to install test dependencies: {stderr}")
        return 1

    # Build pytest command
    cmd_parts = ["python", "-m", "pytest", "tests/performance/"]

    # Add test type filters
    test_type_map = {
        "api": "api_test",
        "cache": "cache_test",
        "memory": "memory_test",
        "load": "load_test",
        "all": "performance"
    }

    markers = []
    for test_type in test_types:
        if test_type in test_type_map:
            markers.append(test_type_map[test_type])

    if markers:
        if "all" in test_types:
            cmd_parts.extend(["-m", "performance"])
        else:
            cmd_parts.extend(["-m", " or ".join(markers)])

    # Add slow test marker if requested
    if include_slow:
        cmd_parts.append("--run-slow")

    # Add verbosity
    if verbose:
        cmd_parts.append("-v")
    else:
        cmd_parts.append("-q")

    # Add performance-specific options
    cmd_parts.extend([
        "--tb=short",  # Short traceback format
        "--durations=10",  # Show 10 slowest tests
        "--benchmark-only",  # Run only benchmark tests
        "--benchmark-sort=mean",  # Sort by mean time
        "--benchmark-json=benchmark_results.json",  # Save benchmark results
        "--benchmark-html=benchmark_report.html"  # Generate HTML report
    ])

    cmd = " ".join(cmd_parts)
    print(f"\n🔧 Running command: {cmd}")
    print("-" * 60)

    # Run tests
    start_time = time.time()
    success, stdout, stderr = run_command(cmd, timeout=1800)  # 30 minute timeout
    end_time = time.time()

    print(stdout)
    if stderr:
        print("STDERR:", stderr)

    # Calculate test duration
    duration = end_time - start_time
    print(f"\n⏱️  Tests completed in {duration:.1f} seconds")

    # Parse results
    if success:
        print("-" * 60)
        print("✅ Performance tests completed successfully!")

        # Generate additional analysis if requested
        if generate_report:
            generate_performance_report(stdout, duration, test_types)

        return 0
    else:
        print("-" * 60)
        print("❌ Performance tests failed!")

        # Try to extract useful error information
        if "FAILED" in stdout:
            failed_tests = [line.strip() for line in stdout.split('\n') if line.strip().startswith('FAILED')]
            if failed_tests:
                print("\nFailed tests:")
                for test in failed_tests[:10]:  # Show first 10 failures
                    print(f"  - {test}")

        return 1

def generate_performance_report(test_output, duration, test_types):
    """Generate a detailed performance report."""
    print("\n📊 Generating detailed performance report...")

    report = {
        "test_session": {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "test_types": test_types,
            "python_version": sys.version,
            "platform": sys.platform
        },
        "performance_targets": {
            "api_response_time": "<3 seconds",
            "cost_per_session": "<$0.10",
            "cache_hit_rate": ">80%",
            "memory_per_file": "<100KB",
            "throughput": ">10 files/second"
        },
        "test_output": test_output,
        "summary": {
            "total_tests_run": test_output.count("passed") + test_output.count("failed"),
            "passed_tests": test_output.count("passed"),
            "failed_tests": test_output.count("failed"),
            "skipped_tests": test_output.count("skipped")
        }
    }

    # Try to parse benchmark results if available
    benchmark_file = Path("benchmark_results.json")
    if benchmark_file.exists():
        try:
            with open(benchmark_file, 'r') as f:
                benchmark_data = json.load(f)
            report["benchmark_results"] = benchmark_data
            print("✅ Benchmark results included in report")
        except Exception as e:
            print(f"⚠️  Could not parse benchmark results: {e}")

    # Save detailed report
    report_file = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"📄 Detailed report saved to: {report_file}")

    # Generate summary
    print("\n📋 Performance Test Summary:")
    print(f"  Duration: {duration:.1f} seconds")
    print(f"  Total Tests: {report['summary']['total_tests_run']}")
    print(f"  Passed: {report['summary']['passed_tests']}")
    print(f"  Failed: {report['summary']['failed_tests']}")
    print(f"  Skipped: {report['summary']['skipped_tests']}")

    if report['summary']['failed_tests'] == 0:
        print("\n🎉 All performance tests passed! System meets performance requirements.")
    else:
        print(f"\n⚠️  {report['summary']['failed_tests']} test(s) failed. Review output for details.")

    # Performance recommendations
    print("\n💡 Performance Recommendations:")
    if "api" in test_types:
        print("  • Monitor API response times in production")
        print("  • Set up alerts for response time >3 seconds")

    if "cache" in test_types:
        print("  • Monitor cache hit rates regularly")
        print("  • Consider cache warming strategies for common file patterns")

    if "memory" in test_types:
        print("  • Monitor memory usage during large file operations")
        print("  • Set up memory usage alerts")

def check_system_requirements():
    """Check if system meets requirements for performance testing."""
    print("🔍 Checking system requirements...")

    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required for performance testing")
        return False

    # Check available memory
    try:
        import psutil
        available_memory_gb = psutil.virtual_memory().available / (1024**3)
        if available_memory_gb < 1:
            print("⚠️  Low available memory (<1GB), performance tests may be slow")
        else:
            print(f"✅ Available memory: {available_memory_gb:.1f}GB")
    except ImportError:
        print("⚠️  psutil not available, cannot check memory usage")

    # Check disk space
    import shutil
    disk_usage_gb = shutil.disk_usage('.').free / (1024**3)
    if disk_usage_gb < 0.5:
        print("⚠️  Low disk space (<500MB), may affect test results")
    else:
        print(f"✅ Available disk space: {disk_usage_gb:.1f}GB")

    print("✅ System requirements met")
    return True

def main():
    """Main performance test runner."""
    parser = argparse.ArgumentParser(
        description="Run AI Disk Cleanup performance tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_performance_tests.py --all                    # Run all performance tests
  python run_performance_tests.py --api                    # Run API performance tests only
  python run_performance_tests.py --cache                  # Run cache performance tests only
  python run_performance_tests.py --memory                 # Run memory tests only
  python run_performance_tests.py --load                   # Run load tests only
  python run_performance_tests.py --slow                   # Include slow performance tests
  python run_performance_tests.py --report                 # Generate detailed performance report
        """
    )

    # Test type options
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument("--all", action="store_true", help="Run all performance tests")
    test_group.add_argument("--api", action="store_true", help="Run API performance tests only")
    test_group.add_argument("--cache", action="store_true", help="Run cache performance tests only")
    test_group.add_argument("--memory", action="store_true", help="Run memory usage tests only")
    test_group.add_argument("--load", action="store_true", help="Run load tests only")

    # Additional options
    parser.add_argument("--slow", action="store_true",
                       help="Include slow performance tests")
    parser.add_argument("--report", action="store_true",
                       help="Generate detailed performance report")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    parser.add_argument("--timeout", type=int, default=1800,
                       help="Test timeout in seconds (default: 1800)")

    args = parser.parse_args()

    # Determine test types
    test_types = []
    if args.all:
        test_types = ["all"]
    elif args.api:
        test_types = ["api"]
    elif args.cache:
        test_types = ["cache"]
    elif args.memory:
        test_types = ["memory"]
    elif args.load:
        test_types = ["load"]
    else:
        # Default to all tests if no specific type selected
        test_types = ["all"]

    # Check system requirements
    if not check_system_requirements():
        return 1

    # Run performance tests
    return run_performance_tests(
        test_types=test_types,
        include_slow=args.slow,
        generate_report=args.report,
        verbose=args.verbose
    )

if __name__ == "__main__":
    sys.exit(main())