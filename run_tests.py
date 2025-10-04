#!/usr/bin/env python3
"""
Test runner for AI Disk Cleanup.

This script provides a convenient way to run the test suite with
various options and configurations.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run AI Disk Cleanup tests")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--benchmark", action="store_true", help="Run performance benchmarks")
    parser.add_argument("--file", "-f", help="Run specific test file")
    parser.add_argument("--function", "-k", help="Run specific test function")

    args = parser.parse_args()

    # Get project root directory
    project_root = Path(__file__).parent
    os.chdir(project_root)

    # Build pytest command
    cmd_parts = ["python", "-m", "pytest"]

    if args.unit:
        cmd_parts.append("tests/unit/")
    elif args.file:
        cmd_parts.append(args.file)
    else:
        cmd_parts.append("tests/")

    if args.function:
        cmd_parts.extend(["-k", args.function])

    if args.verbose:
        cmd_parts.append("-v")

    if args.coverage or args.benchmark:
        # Install test dependencies if needed
        print("Installing test dependencies...")
        success, stdout, stderr = run_command(
            "python -m pip install -e .[test]"
        )
        if not success:
            print(f"Failed to install test dependencies: {stderr}")
            return 1

    if args.coverage:
        cmd_parts.extend([
            "--cov=src/ai_disk_cleanup",
            "--cov-report=term-missing",
            "--cov-report=html"
        ])

    if args.benchmark:
        cmd_parts.append("--benchmark-only")

    cmd = " ".join(cmd_parts)

    print(f"Running: {cmd}")
    print("-" * 60)

    success, stdout, stderr = run_command(cmd)

    print(stdout)
    if stderr:
        print("STDERR:", stderr)

    if success:
        print("-" * 60)
        print("✅ Tests completed successfully!")
        return 0
    else:
        print("-" * 60)
        print("❌ Tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())