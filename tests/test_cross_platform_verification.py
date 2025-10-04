"""
Comprehensive cross-platform verification test suite.

This module tests the consistency and functionality of the platform adapter
pattern across Windows, macOS, and Linux systems.
"""

import platform
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.platforms import (
    BaseAdapter, PlatformType, FileOperationResult,
    WindowsAdapter, MacOSAdapter, LinuxAdapter,
    PlatformAdapterFactory, get_platform_adapter
)
from src.ai_disk_cleanup.security import CredentialStore


class TestPlatformDetection(unittest.TestCase):
    """Test platform detection and adapter selection mechanism."""

    def test_current_platform_detection(self):
        """Test that the current platform is correctly detected."""
        adapter = get_platform_adapter()
        self.assertIsNotNone(adapter)

        # Verify the detected platform matches the actual system
        system = platform.system().lower()
        if system == 'windows':
            self.assertIsInstance(adapter, WindowsAdapter)
            self.assertEqual(adapter.platform_type, PlatformType.WINDOWS)
        elif system == 'darwin':
            self.assertIsInstance(adapter, MacOSAdapter)
            self.assertEqual(adapter.platform_type, PlatformType.MACOS)
        elif system == 'linux':
            self.assertIsInstance(adapter, LinuxAdapter)
            self.assertEqual(adapter.platform_type, PlatformType.LINUX)
        else:
            self.fail(f"Unsupported platform: {system}")

    def test_factory_adapter_creation(self):
        """Test factory pattern adapter creation."""
        # Test creating each platform adapter explicitly
        windows_adapter = PlatformAdapterFactory.create_adapter(PlatformType.WINDOWS)
        self.assertIsInstance(windows_adapter, WindowsAdapter)

        macos_adapter = PlatformAdapterFactory.create_adapter(PlatformType.MACOS)
        self.assertIsInstance(macos_adapter, MacOSAdapter)

        linux_adapter = PlatformAdapterFactory.create_adapter(PlatformType.LINUX)
        self.assertIsInstance(linux_adapter, LinuxAdapter)

    def test_supported_platforms(self):
        """Test that all expected platforms are supported."""
        supported = PlatformAdapterFactory.get_supported_platforms()
        expected = [PlatformType.WINDOWS, PlatformType.MACOS, PlatformType.LINUX]

        self.assertEqual(len(supported), len(expected))
        for platform_type in expected:
            self.assertIn(platform_type, supported)
            self.assertTrue(PlatformAdapterFactory.is_platform_supported(platform_type))

    @patch('platform.system')
    def test_platform_detection_edge_cases(self, mock_system):
        """Test platform detection with various system responses."""
        # Test unsupported platform
        mock_system.return_value = 'FreeBSD'
        with self.assertRaises(Exception):
            PlatformAdapterFactory._detect_current_platform()

        # Test case variations
        mock_system.return_value = 'WINDOWS'
        self.assertEqual(PlatformAdapterFactory._detect_current_platform(), PlatformType.WINDOWS)

        mock_system.return_value = 'Darwin'
        self.assertEqual(PlatformAdapterFactory._detect_current_platform(), PlatformType.MACOS)

        mock_system.return_value = 'LINUX'
        self.assertEqual(PlatformAdapterFactory._detect_current_platform(), PlatformType.LINUX)


class TestAPIConsistency(unittest.TestCase):
    """Test consistent API behavior across platform adapters."""

    def setUp(self):
        """Set up test adapters for all platforms."""
        self.adapters = {
            PlatformType.WINDOWS: WindowsAdapter(),
            PlatformType.MACOS: MacOSAdapter(),
            PlatformType.LINUX: LinuxAdapter(),
        }

    def test_interface_completeness(self):
        """Test that all adapters implement the complete interface."""
        required_methods = [
            'normalize_path',
            'get_file_manager_integration',
            'get_directory_size',
            'list_directory_contents',
            'move_to_trash',
            'restore_from_trash',
            'open_in_file_manager',
            'get_file_metadata',
            'set_file_permissions',
            'optimize_for_platform'
        ]

        for platform_type, adapter in self.adapters.items():
            with self.subTest(platform=platform_type):
                for method_name in required_methods:
                    self.assertTrue(hasattr(adapter, method_name),
                                  f"{platform_type} adapter missing method: {method_name}")

    def test_consistent_return_types(self):
        """Test that methods return consistent types across platforms."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir)

            # Test normalize_path
            for platform_type, adapter in self.adapters.items():
                with self.subTest(platform=platform_type, method='normalize_path'):
                    result = adapter.normalize_path("/test/path")
                    self.assertIsInstance(result, Path)

            # Test get_file_manager_integration
            for platform_type, adapter in self.adapters.items():
                with self.subTest(platform=platform_type, method='get_file_manager_integration'):
                    result = adapter.get_file_manager_integration()
                    self.assertIsInstance(result, dict)
                    self.assertIn('name', result)
                    self.assertIn('features', result)

            # Test get_directory_size
            for platform_type, adapter in self.adapters.items():
                with self.subTest(platform=platform_type, method='get_directory_size'):
                    result = adapter.get_directory_size(test_path)
                    self.assertIsInstance(result, int)
                    self.assertGreaterEqual(result, 0)

            # Test list_directory_contents
            for platform_type, adapter in self.adapters.items():
                with self.subTest(platform=platform_type, method='list_directory_contents'):
                    result = adapter.list_directory_contents(test_path)
                    self.assertIsInstance(result, list)
                    for item in result:
                        self.assertIsInstance(item, Path)

            # Test file operation results
            for platform_type, adapter in self.adapters.items():
                with self.subTest(platform=platform_type, method='move_to_trash'):
                    # Create a test file
                    test_file = test_path / "test.txt"
                    test_file.write_text("test")

                    result = adapter.move_to_trash(test_file)
                    self.assertIsInstance(result, FileOperationResult)
                    self.assertIsInstance(result.success, bool)

                with self.subTest(platform=platform_type, method='get_file_metadata'):
                    # Test with non-existent path (should return empty dict)
                    result = adapter.get_file_metadata(Path("/non/existent/path"))
                    self.assertIsInstance(result, dict)

    def test_consistent_error_handling(self):
        """Test that error handling is consistent across platforms."""
        non_existent_path = Path("/non/existent/path")

        for platform_type, adapter in self.adapters.items():
            with self.subTest(platform=platform_type):
                # Test operations with non-existent paths
                size = adapter.get_directory_size(non_existent_path)
                self.assertEqual(size, 0)

                contents = adapter.list_directory_contents(non_existent_path)
                self.assertEqual(len(contents), 0)

                metadata = adapter.get_file_metadata(non_existent_path)
                self.assertEqual(metadata, {})


class TestPathHandling(unittest.TestCase):
    """Test cross-platform file path handling and normalization."""

    def setUp(self):
        """Set up test adapters."""
        self.adapters = {
            PlatformType.WINDOWS: WindowsAdapter(),
            PlatformType.MACOS: MacOSAdapter(),
            PlatformType.LINUX: LinuxAdapter(),
        }

    def test_path_normalization(self):
        """Test path normalization across platforms."""
        test_cases = [
            "/test/path",
            "C:\\Users\\test",
            "/mixed\\path/separators",
            "relative/path",
            "..\\parent\\path"
        ]

        for test_path in test_cases:
            with self.subTest(path=test_path):
                results = {}
                for platform_type, adapter in self.adapters.items():
                    normalized = adapter.normalize_path(test_path)
                    results[platform_type] = normalized

                    # Should always return a Path object
                    self.assertIsInstance(normalized, Path)

                # Windows adapter should use backslashes
                windows_result = results[PlatformType.WINDOWS]
                self.assertNotIn('/', str(windows_result))

                # macOS and Linux adapters should use forward slashes
                macos_result = results[PlatformType.MACOS]
                linux_result = results[PlatformType.LINUX]
                self.assertNotIn('\\', str(macos_result))
                self.assertNotIn('\\', str(linux_result))

    def test_path_separator_consistency(self):
        """Test that path separators are handled consistently."""
        # Test mixed separators
        mixed_path = "C:/Users\\test/Documents/file.txt"

        windows_normalized = self.adapters[PlatformType.WINDOWS].normalize_path(mixed_path)
        macos_normalized = self.adapters[PlatformType.MACOS].normalize_path(mixed_path)
        linux_normalized = self.adapters[PlatformType.LINUX].normalize_path(mixed_path)

        # Windows should use backslashes
        self.assertIn('\\', str(windows_normalized))
        self.assertNotIn('/', str(windows_normalized))

        # macOS and Linux should use forward slashes
        self.assertNotIn('\\', str(macos_normalized))
        self.assertNotIn('\\', str(linux_normalized))
        self.assertIn('/', str(macos_normalized))
        self.assertIn('/', str(linux_normalized))


class TestFileManagerIntegration(unittest.TestCase):
    """Test platform-specific file manager integrations."""

    def setUp(self):
        """Set up test adapters."""
        self.adapters = {
            PlatformType.WINDOWS: WindowsAdapter(),
            PlatformType.MACOS: MacOSAdapter(),
            PlatformType.LINUX: LinuxAdapter(),
        }

    def test_file_manager_capabilities(self):
        """Test that each platform reports appropriate file manager capabilities."""
        windows_info = self.adapters[PlatformType.WINDOWS].get_file_manager_integration()
        macos_info = self.adapters[PlatformType.MACOS].get_file_manager_integration()
        linux_info = self.adapters[PlatformType.LINUX].get_file_manager_integration()

        # Windows should mention Explorer
        self.assertEqual(windows_info['name'], 'Windows Explorer')
        self.assertIn('shell_integration', windows_info['features'])
        self.assertIn('recycle_bin_access', windows_info['features'])

        # macOS should mention Finder
        self.assertEqual(macos_info['name'], 'macOS Finder')
        self.assertIn('spotlight_search', macos_info['features'])
        self.assertIn('tags_support', macos_info['features'])

        # Linux should mention multiple file managers
        self.assertEqual(linux_info['name'], 'Linux File Manager')
        self.assertIn('supported_managers', linux_info)
        self.assertIn('trash_integration', linux_info['features'])

    @patch('subprocess.run')
    def test_open_in_file_manager(self, mock_run):
        """Test opening paths in system file managers."""
        mock_run.return_value = MagicMock()

        test_path = Path("/test/path")

        # Test Windows
        windows_adapter = self.adapters[PlatformType.WINDOWS]
        result = windows_adapter.open_in_file_manager(test_path)
        self.assertTrue(result.success)
        mock_run.assert_called_with(['explorer', str(test_path)], check=True)

        # Test macOS
        mock_run.reset_mock()
        macos_adapter = self.adapters[PlatformType.MACOS]
        result = macos_adapter.open_in_file_manager(test_path)
        self.assertTrue(result.success)
        mock_run.assert_called_with(['open', str(test_path)], check=True)

        # Test Linux
        mock_run.reset_mock()
        linux_adapter = self.adapters[PlatformType.LINUX]
        result = linux_adapter.open_in_file_manager(test_path)
        self.assertTrue(result.success)
        mock_run.assert_called_with(['xdg-open', str(test_path)], check=True)


class TestPlatformOptimizations(unittest.TestCase):
    """Test platform-specific optimizations."""

    def setUp(self):
        """Set up test adapters."""
        self.adapters = {
            PlatformType.WINDOWS: WindowsAdapter(),
            PlatformType.MACOS: MacOSAdapter(),
            PlatformType.LINUX: LinuxAdapter(),
        }

    def test_optimization_strategies(self):
        """Test that each platform provides appropriate optimizations."""
        operations = ['directory_scan', 'file_deletion', 'nonexistent_operation']

        for operation in operations:
            with self.subTest(operation=operation):
                results = {}
                for platform_type, adapter in self.adapters.items():
                    optimization = adapter.optimize_for_platform(operation, {})
                    results[platform_type] = optimization

                    # Should always return a dict
                    self.assertIsInstance(optimization, dict)

                if operation == 'directory_scan':
                    # Windows should mention Windows APIs
                    windows_opt = results[PlatformType.WINDOWS]
                    self.assertIn('use_windows_apis', windows_opt)

                    # macOS should mention Spotlight
                    macos_opt = results[PlatformType.MACOS]
                    self.assertIn('use_spotlight', macos_opt)

                    # Linux should mention inotify
                    linux_opt = results[PlatformType.LINUX]
                    self.assertIn('use_inotify', linux_opt)

                elif operation == 'file_deletion':
                    # All platforms should mention trash/recycle bin integration
                    for platform_type, optimization in results.items():
                        if platform_type == PlatformType.WINDOWS:
                            self.assertIn('use_recycle_bin', optimization)
                        else:
                            self.assertIn('trash_integration', optimization)


class TestCredentialStorageConsistency(unittest.TestCase):
    """Test credential storage consistency across platforms."""

    def test_credential_store_initialization(self):
        """Test that credential store initializes consistently."""
        store = CredentialStore()

        # Should initialize regardless of platform
        self.assertIsNotNone(store.service_name)
        self.assertIsNotNone(store.system_name)
        self.assertIsNotNone(store._encryption_key)

        # Should provide storage info
        info = store.get_secure_storage_info()
        self.assertIsInstance(info, dict)
        self.assertIn('system', info)
        self.assertIn('keyring_available', info)
        self.assertIn('encryption_enabled', info)

    def test_api_key_operations(self):
        """Test API key storage and retrieval."""
        store = CredentialStore()
        test_provider = "test_provider"
        test_key = "test_api_key_12345"

        # Test setting API key (may fail if keyring not available)
        set_result = store.set_api_key(test_provider, test_key)
        if set_result:
            # If successful, test retrieval
            retrieved_key = store.get_api_key(test_provider)
            self.assertEqual(retrieved_key, test_key)

            # Test deletion
            delete_result = store.delete_api_key(test_provider)
            self.assertTrue(delete_result)

            # Verify deletion
            deleted_key = store.get_api_key(test_provider)
            self.assertIsNone(deleted_key)

    def test_provider_listing(self):
        """Test provider listing functionality."""
        store = CredentialStore()
        providers = store.list_providers()

        # Should return a list
        self.assertIsInstance(providers, list)

        # Environment variables should be detected
        with patch.dict('os.environ', {'TEST_API_KEY': 'test_key'}):
            providers = store.list_providers()
            self.assertIsInstance(providers, list)


class TestCrossPlatformIntegration(unittest.TestCase):
    """Integration tests for cross-platform functionality."""

    def test_end_to_end_workflow(self):
        """Test a complete workflow across all platforms."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            test_files = []
            for i in range(3):
                test_file = temp_path / f"test_file_{i}.txt"
                test_file.write_text(f"Test content {i}")
                test_files.append(test_file)

            # Test with all adapters
            adapters = [WindowsAdapter(), MacOSAdapter(), LinuxAdapter()]

            for adapter in adapters:
                with self.subTest(adapter=adapter.__class__.__name__):
                    # Test directory listing
                    contents = adapter.list_directory_contents(temp_path)
                    self.assertEqual(len(contents), 3)

                    # Test directory size calculation
                    size = adapter.get_directory_size(temp_path)
                    self.assertGreater(size, 0)

                    # Test file metadata
                    for test_file in test_files:
                        metadata = adapter.get_file_metadata(test_file)
                        self.assertIn('size', metadata)
                        self.assertEqual(metadata['size'], len(f"Test content {test_files.index(test_file)}"))

                        # Test platform-specific metadata
                        platform_key = f"{adapter.platform_type.value}_specific"
                        self.assertIn(platform_key, metadata)

    def test_error_recovery(self):
        """Test error recovery across platforms."""
        adapters = [WindowsAdapter(), MacOSAdapter(), LinuxAdapter()]

        for adapter in adapters:
            with self.subTest(adapter=adapter.__class__.__name__):
                # Test operations with invalid paths
                invalid_path = Path("/invalid/nonexistent/path")

                # Should handle gracefully without exceptions
                size = adapter.get_directory_size(invalid_path)
                self.assertEqual(size, 0)

                contents = adapter.list_directory_contents(invalid_path)
                self.assertEqual(len(contents), 0)

                metadata = adapter.get_file_metadata(invalid_path)
                self.assertEqual(metadata, {})

                # Test trash operation with non-existent file
                result = adapter.move_to_trash(invalid_path)
                self.assertIsInstance(result, FileOperationResult)


if __name__ == '__main__':
    unittest.main()