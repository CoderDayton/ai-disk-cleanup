#!/usr/bin/env python3
"""Example script demonstrating configuration and credential management usage."""

import os
import tempfile
from pathlib import Path

from ai_disk_cleanup.core.config_manager import ConfigManager, get_config, get_user_preferences, get_config_manager
from ai_disk_cleanup.core.config_models import ConfidenceLevel, CleanupScope
from ai_disk_cleanup.security.credential_store import CredentialStore


def demonstrate_configuration_management():
    """Demonstrate configuration management functionality."""
    print("=== Configuration Management Demo ===\n")

    # Create temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        config_file = temp_path / "demo_config.yaml"
        prefs_file = temp_path / "demo_prefs.yaml"

        # Initialize configuration manager
        print("1. Initializing Configuration Manager...")
        manager = ConfigManager(
            config_file=config_file,
            user_prefs_file=prefs_file,
            auto_load=True
        )

        print(f"   Config file: {config_file}")
        print(f"   Prefs file: {prefs_file}")
        print()

        # Show default configuration
        print("2. Default Configuration:")
        print(f"   App Name: {manager.config.app_name}")
        print(f"   Version: {manager.config.version}")
        print(f"   AI Provider: {manager.config.ai_model.provider}")
        print(f"   AI Model: {manager.config.ai_model.model_name}")
        print(f"   Confidence Threshold: {manager.config.security.min_confidence_threshold}")
        print(f"   Default Scope: {manager.config.cleanup.default_scope}")
        print()

        # Customize configuration
        print("3. Customizing Configuration...")
        manager.update_config(
            app_name="AI Disk Cleanup Demo",
            ai_model__provider="anthropic",
            ai_model__model_name="claude-3-sonnet",
            ai_model__temperature=0.3,
            security__min_confidence_threshold=ConfidenceLevel.VERY_HIGH,
            security__require_confirmation=True,
            security__backup_before_delete=True,
            cleanup__default_scope=CleanupScope.CUSTOM_PATHS,
            cleanup__file_age_threshold_days=14,
            cleanup__dry_run_by_default=True
        )

        # Show customized configuration
        print("   Updated Configuration:")
        print(f"   App Name: {manager.config.app_name}")
        print(f"   AI Provider: {manager.config.ai_model.provider}")
        print(f"   AI Model: {manager.config.ai_model.model_name}")
        print(f"   Temperature: {manager.config.ai_model.temperature}")
        print(f"   Confidence Threshold: {manager.config.security.min_confidence_threshold}")
        print(f"   Require Confirmation: {manager.config.security.require_confirmation}")
        print(f"   Backup Before Delete: {manager.config.security.backup_before_delete}")
        print(f"   Default Scope: {manager.config.cleanup.default_scope}")
        print(f"   File Age Threshold: {manager.config.cleanup.file_age_threshold_days} days")
        print(f"   Dry Run by Default: {manager.config.cleanup.dry_run_by_default}")
        print()

        # Customize user preferences
        print("4. Setting User Preferences...")
        manager.update_user_preferences(
            favorite_paths=[
                str(Path.home() / "Documents"),
                str(Path.home() / "Downloads"),
                "/tmp"
            ],
            recent_scans=["/var/log", "/tmp"],
            custom_rules={
                "temp_files": {
                    "delete": True,
                    "age_days": 1,
                    "patterns": ["*.tmp", "*.temp", "~*"]
                },
                "cache_files": {
                    "delete": True,
                    "age_days": 7,
                    "patterns": ["*.cache", "__pycache__"]
                }
            },
            last_scan_time="2024-01-15T10:30:00Z"
        )

        # Show user preferences
        print("   User Preferences:")
        print(f"   Favorite Paths: {manager.user_prefs.favorite_paths}")
        print(f"   Recent Scans: {manager.user_prefs.recent_scans}")
        print(f"   Custom Rules: {manager.user_prefs.custom_rules}")
        print(f"   Last Scan: {manager.user_prefs.last_scan_time}")
        print()

        # Demonstrate data directories
        print("5. Data Directories:")
        data_dir = manager.config.get_data_dir()
        cache_dir = manager.config.get_cache_dir()
        backup_dir = manager.config.get_backup_dir()

        print(f"   Data Directory: {data_dir}")
        print(f"   Cache Directory: {cache_dir}")
        print(f"   Backup Directory: {backup_dir}")
        print(f"   Data Dir Exists: {data_dir.exists()}")
        print(f"   Cache Dir Exists: {cache_dir.exists()}")
        print(f"   Backup Dir Exists: {backup_dir.exists()}")
        print()

        # Validate configuration
        print("6. Configuration Validation:")
        validation_results = manager.validate_config()
        print(f"   Valid: {validation_results['valid']}")
        print(f"   Errors: {len(validation_results['errors'])}")
        print(f"   Warnings: {len(validation_results['warnings'])}")

        if validation_results['warnings']:
            print("   Warnings:")
            for warning in validation_results['warnings']:
                print(f"     - {warning}")
        print()

        # Demonstrate configuration export/import
        print("7. Configuration Export/Import:")
        export_file = temp_path / "exported_config.yaml"
        export_success = manager.export_config(export_file)
        print(f"   Export Success: {export_success}")
        print(f"   Export File: {export_file}")
        print(f"   Export File Exists: {export_file.exists()}")

        if export_file.exists():
            print(f"   Export File Size: {export_file.stat().st_size} bytes")
        print()


def demonstrate_credential_management():
    """Demonstrate credential management functionality."""
    print("=== Credential Management Demo ===\n")

    # Note: This demo uses a mock environment to avoid storing real credentials
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        config_file = temp_path / "credential_config.yaml"

        print("1. Initializing Credential Store...")
        manager = ConfigManager(config_file=config_file, auto_load=True)

        # Show credential store information
        print("2. Credential Store Information:")
        store_info = manager.credential_store.get_secure_storage_info()
        print(f"   System: {store_info['system']}")
        print(f"   Keyring Available: {store_info['keyring_available']}")
        print(f"   Encryption Enabled: {store_info['encryption_enabled']}")
        print(f"   Service Name: {store_info['service_name']}")

        if 'backend' in store_info:
            backend = store_info['backend']
            print(f"   Backend: {backend['name']} ({backend['module']})")
        print()

        # Demonstrate API key testing (without real keys)
        print("3. API Key Format Validation:")

        test_keys = {
            "OpenAI": "sk-1234567890abcdef1234567890abcdef12345678",
            "Anthropic": "sk-ant-1234567890abcdef1234567890abcdef12345678",
            "Invalid": "invalid-key"
        }

        for provider, key in test_keys.items():
            result = manager.credential_store.test_api_key(key, provider)
            print(f"   {provider}: {'✓ Valid' if result['valid'] else '✗ Invalid'}")
            if not result['valid']:
                print(f"     Error: {result['error']}")
            else:
                print(f"     Message: {result['message']}")
        print()

        # Check for environment variables (demo only)
        print("4. Environment Variable API Keys:")
        env_providers = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]

        found_keys = False
        for env_var in env_providers:
            if os.environ.get(env_var):
                provider = env_var.replace('_API_KEY', '').lower()
                key = os.environ.get(env_var)
                # Mask the key for display
                masked_key = key[:8] + "*" * (len(key) - 12) + key[-4:] if len(key) > 12 else "*" * len(key)
                print(f"   {provider}: {masked_key}")
                found_keys = True

        if not found_keys:
            print("   No API keys found in environment variables")
        print()

        # List available providers
        print("5. Available Providers:")
        providers = manager.credential_store.list_providers()
        if providers:
            for provider in providers:
                print(f"   - {provider}")
        else:
            print("   No providers with stored API keys found")
        print()


def demonstrate_global_functions():
    """Demonstrate global convenience functions."""
    print("=== Global Functions Demo ===\n")

    print("1. Using Global Configuration Functions...")

    # Get global configuration
    config = get_config()
    print(f"   Global Config App Name: {config.app_name}")
    print(f"   Global Config AI Provider: {config.ai_model.provider}")

    # Get global user preferences
    prefs = get_user_preferences()
    print(f"   Global Prefs Favorite Paths: {prefs.favorite_paths}")
    print(f"   Global Prefs Custom Rules: {list(prefs.custom_rules.keys())}")
    print()

    print("2. Configuration Manager Singleton...")
    manager1 = get_config_manager()
    manager2 = get_config_manager()
    print(f"   Manager1 ID: {id(manager1)}")
    print(f"   Manager2 ID: {id(manager2)}")
    print(f"   Same Instance: {manager1 is manager2}")
    print()


def main():
    """Run all demonstrations."""
    print("AI Disk Cleanup - Configuration & Credential Management Demo")
    print("=" * 60)
    print()

    try:
        demonstrate_configuration_management()
        demonstrate_credential_management()
        demonstrate_global_functions()

        print("=" * 60)
        print("Demo completed successfully!")
        print("\nNote: This demo used temporary directories and mock data.")
        print("In a real application, your configuration and credentials would")
        print("be stored in platform-specific locations.")

    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()