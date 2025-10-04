"""
Command-line interface for the cross-platform installer system.

This module provides the CLI commands for building installers for different
platforms and managing the build process.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from .config import InstallerConfig, ConfigValidationError
from .orchestrator import BuildOrchestrator, BuildError


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Build cross-platform installers for AI Disk Cleanup",
        prog="installer"
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Build command
    build_parser = subparsers.add_parser("build", help="Build installers")
    build_parser.add_argument(
        "platforms",
        nargs="?",
        choices=["windows", "linux", "macos", "all"],
        default="all",
        help="Platforms to build for (default: all)"
    )
    build_parser.add_argument(
        "--config",
        type=Path,
        default=Path("build/installer-config.yaml"),
        help="Path to configuration file (default: build/installer-config.yaml)"
    )
    build_parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build directory before building"
    )
    build_parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate configuration and environment, don't build"
    )

    # Config command
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate configuration file"
    )
    config_parser.add_argument(
        "--show",
        action="store_true",
        help="Show current configuration"
    )
    config_parser.add_argument(
        "--config",
        type=Path,
        default=Path("build/installer-config.yaml"),
        help="Path to configuration file (default: build/installer-config.yaml)"
    )

    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean build directory")
    clean_parser.add_argument(
        "--config",
        type=Path,
        default=Path("build/installer-config.yaml"),
        help="Path to configuration file (default: build/installer-config.yaml)"
    )

    # Version command
    subparsers.add_parser("version", help="Show version information")

    return parser


def load_config(config_path: Path) -> InstallerConfig:
    """
    Load and validate the configuration.

    Args:
        config_path: Path to configuration file

    Returns:
        Loaded configuration

    Raises:
        ConfigValidationError: If configuration is invalid
    """
    try:
        return InstallerConfig.load_from_file(config_path)
    except ConfigValidationError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)


def handle_build_command(args) -> None:
    """Handle the build command."""
    try:
        # Load configuration
        config = load_config(args.config)
        print(f"📦 Building installers for {config.project_name} v{config.version}")

        # Create orchestrator
        orchestrator = BuildOrchestrator(config)

        # Validate build environment
        print("🔍 Validating build environment...")
        orchestrator.validate_build_environment()
        print("✅ Build environment validated")

        # Clean if requested
        if args.clean:
            print("🧹 Cleaning build directory...")
            orchestrator.clean_build_directory()
            print("✅ Build directory cleaned")

        # If validate only, exit here
        if args.validate_only:
            print("✅ Configuration and environment validation complete")
            return

        # Determine platforms to build
        platforms_to_build = []
        if args.platforms == "all":
            platforms_to_build = config.get_enabled_platforms()
        else:
            platforms_to_build = [args.platforms]

        if not platforms_to_build:
            print("❌ No platforms enabled for building")
            sys.exit(1)

        print(f"🏗️  Building for platforms: {', '.join(platforms_to_build)}")

        # For now, just show what would be built (Phase 1 limitation)
        print("\n📋 Build Plan (Phase 1 - Core Infrastructure):")
        for platform in platforms_to_build:
            output_path = config.get_output_path(platform)
            print(f"  • {platform.title()}: {output_path}")

        print("\n⚠️  Phase 1 complete: Core infrastructure implemented")
        print("   Next phases will implement actual platform-specific builders")
        print("   Run: installer build windows --config build/installer-config.yaml")

    except BuildError as e:
        print(f"❌ Build error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


def handle_config_command(args) -> None:
    """Handle the config command."""
    try:
        if args.validate:
            print(f"🔍 Validating configuration: {args.config}")
            config = load_config(args.config)
            print("✅ Configuration is valid")
            print(f"   Project: {config.project_name} v{config.version}")
            print(f"   Enabled platforms: {', '.join(config.get_enabled_platforms())}")

        elif args.show:
            print(f"📄 Configuration: {args.config}")
            config = load_config(args.config)
            print(f"   Project: {config.project_name}")
            print(f"   Version: {config.version}")
            print(f"   Description: {config.description}")
            print(f"   Output directory: {config.output_dir}")
            print(f"   Enabled platforms: {', '.join(config.get_enabled_platforms())}")

    except ConfigValidationError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)


def handle_clean_command(args) -> None:
    """Handle the clean command."""
    try:
        config = load_config(args.config)
        orchestrator = BuildOrchestrator(config)

        print("🧹 Cleaning build directory...")
        orchestrator.clean_build_directory()
        print("✅ Build directory cleaned")

    except Exception as e:
        print(f"❌ Error cleaning directory: {e}")
        sys.exit(1)


def handle_version_command() -> None:
    """Handle the version command."""
    from . import __version__
    print(f"Installer v{__version__}")
    print("Cross-platform installer system for AI Disk Cleanup")


def main(argv: Optional[List[str]] = None) -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "build":
            handle_build_command(args)
        elif args.command == "config":
            handle_config_command(args)
        elif args.command == "clean":
            handle_clean_command(args)
        elif args.command == "version":
            handle_version_command()
        else:
            print(f"❌ Unknown command: {args.command}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n❌ Build interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()