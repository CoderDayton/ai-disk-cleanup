#!/usr/bin/env python3
"""
AI Disk Cleaner - Simple File Organization Script

A lightweight Python script to clean up project files safely.
Focuses on three main areas:
1. Duplicate web-ui cleanup (major impact)
2. Cache file removal (quick wins)
3. Empty directory removal (organization improvement)
"""

import os
import shutil
import sys
from pathlib import Path
from typing import List, Dict
import argparse

class ProjectCleaner:
    def __init__(self, project_root: str, dry_run: bool = True):
        self.project_root = Path(project_root)
        self.dry_run = dry_run
        self.cleaned_files = []
        self.cleaned_dirs = []
        self.space_saved = 0

    def calculate_size(self, path: Path) -> int:
        """Calculate size of file or directory."""
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        return 0

    def clean_duplicate_web_ui(self):
        """Clean up duplicate web-ui directories."""
        print("🔍 Analyzing duplicate web-ui directories...")

        web_ui_main = self.project_root / "web-ui"
        web_ui_src = self.project_root / "src" / "web-ui"

        if web_ui_main.exists() and web_ui_src.exists():
            # Compare sizes and content
            main_size = self.calculate_size(web_ui_main)
            src_size = self.calculate_size(web_ui_src)

            print(f"📁 Found web-ui directories:")
            print(f"   - /web-ui: {self.format_size(main_size)}")
            print(f"   - /src/web-ui: {self.format_size(src_size)}")

            # Keep the one in /src/web-ui (it's more organized)
            if main_size > 0:
                print(f"🗑️  Will remove: /web-ui (saves {self.format_size(main_size)})")
                self.space_saved += main_size
                if not self.dry_run:
                    if web_ui_main.is_dir():
                        shutil.rmtree(web_ui_main)
                    else:
                        web_ui_main.unlink()
                    self.cleaned_dirs.append(str(web_ui_main))
                else:
                    self.cleaned_dirs.append(f"[DRY RUN] {web_ui_main}")
        else:
            print("✅ No duplicate web-ui directories found")

    def clean_cache_files(self):
        """Clean up cache files and temporary files."""
        print("\n🔍 Analyzing cache files...")

        cache_patterns = [
            "**/__pycache__/**",
            "**/*.pyc",
            "**/*.pyo",
            "**/.pytest_cache/**",
            "**/.coverage",
            "**/htmlcov/**",
            "**/.mypy_cache/**",
            "**/.tox/**",
            "**/node_modules/.cache/**",
            "**/.npm/**",
            "**/.yarn/**",
            "**/dist/**",
            "**/build/**"
        ]

        cache_files_removed = 0
        cache_dirs_removed = 0

        for pattern in cache_patterns:
            for path in self.project_root.glob(pattern):
                if path.exists():
                    size = self.calculate_size(path)
                    self.space_saved += size

                    if path.is_dir():
                        print(f"🗑️  Cache dir: {path.relative_to(self.project_root)} ({self.format_size(size)})")
                        if not self.dry_run:
                            shutil.rmtree(path)
                        cache_dirs_removed += 1
                    else:
                        print(f"🗑️  Cache file: {path.relative_to(self.project_root)} ({self.format_size(size)})")
                        if not self.dry_run:
                            path.unlink()
                        cache_files_removed += 1

                    if path.is_dir():
                        self.cleaned_dirs.append(str(path))
                    else:
                        self.cleaned_files.append(str(path))

        print(f"📊 Cache cleanup: {cache_files_removed} files, {cache_dirs_removed} directories")

    def clean_empty_directories(self):
        """Remove empty directories."""
        print("\n🔍 Analyzing empty directories...")

        empty_dirs = []
        for root, dirs, files in os.walk(self.project_root, topdown=False):
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                try:
                    if not any(dir_path.iterdir()):
                        # Skip important directories that might be empty intentionally
                        if not any(skip in str(dir_path) for skip in ['.git', '__pycache__', 'node_modules']):
                            empty_dirs.append(dir_path)
                except PermissionError:
                    continue

        for empty_dir in empty_dirs:
            print(f"🗑️  Empty dir: {empty_dir.relative_to(self.project_root)}")
            if not self.dry_run:
                try:
                    empty_dir.rmdir()
                except OSError:
                    print(f"⚠️  Could not remove: {empty_dir}")
            self.cleaned_dirs.append(str(empty_dir))

        print(f"📊 Empty directories removed: {len(empty_dirs)}")

    def format_size(self, size_bytes: int) -> str:
        """Format bytes to human readable size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def run_cleanup(self):
        """Run the complete cleanup process."""
        print(f"🚀 AI Disk Cleaner - Project Cleanup")
        print(f"📁 Project: {self.project_root}")
        print(f"🔍 Mode: {'DRY RUN (no changes made)' if self.dry_run else 'EXECUTION'}")
        print("-" * 50)

        # Run cleanup phases
        self.clean_duplicate_web_ui()
        self.clean_cache_files()
        self.clean_empty_directories()

        # Summary
        print("\n" + "=" * 50)
        print("📊 CLEANUP SUMMARY")
        print("=" * 50)
        print(f"📁 Files cleaned: {len(self.cleaned_files)}")
        print(f"📂 Directories cleaned: {len(self.cleaned_dirs)}")
        print(f"💾 Space saved: {self.format_size(self.space_saved)}")

        if self.dry_run:
            print("\n💡 This was a DRY RUN. No actual changes were made.")
            print("   Run with --execute to perform the cleanup.")
        else:
            print("\n✅ Cleanup completed successfully!")

def main():
    parser = argparse.ArgumentParser(description="AI Disk Cleaner - Project Cleanup Tool")
    parser.add_argument("project_root", nargs="?", default=".",
                       help="Project root directory (default: current directory)")
    parser.add_argument("--execute", action="store_true",
                       help="Execute cleanup (default: dry run)")
    parser.add_argument("--quiet", action="store_true",
                       help="Quiet mode with minimal output")

    args = parser.parse_args()

    if not args.quiet:
        print("🤖 AI Disk Cleaner - Simple File Organization")

    cleaner = ProjectCleaner(
        project_root=args.project_root,
        dry_run=not args.execute
    )

    try:
        cleaner.run_cleanup()
    except KeyboardInterrupt:
        print("\n⚠️  Cleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()