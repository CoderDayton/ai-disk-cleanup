"""Tests for credential store."""

import pytest
import base64
import os
from unittest.mock import Mock, patch, MagicMock

from ai_disk_cleanup.security.credential_store import CredentialStore


class TestCredentialStore:
    """Test CredentialStore class."""

    @patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', True)
    @patch('ai_disk_cleanup.security.credential_store.keyring')
    def test_init_with_keyring_available(self, mock_keyring):
        """Test initialization when keyring is available."""
        mock_keyring.get_keyring.return_value = Mock()

        # Mock get_password to return None initially (no stored key)
        mock_keyring.get_password.return_value = None

        store = CredentialStore()

        assert store.service_name == "ai-disk-cleanup"
        assert store._keyring_available is True
        assert store._encryption_key is not None
        assert store._master_key_salt is not None

    @patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False)
    def test_init_without_keyring(self):
        """Test initialization when keyring is not available."""
        store = CredentialStore()

        assert store._keyring_available is False
        # Should still initialize encryption key for environment fallback

    @patch.dict(os.environ, {'AI_DISK_CLEANUP_ENCRYPTION_KEY': base64.urlsafe_b64encode(b'test-key-32-bytes-long-key').decode()})
    def test_encryption_key_from_environment(self):
        """Test getting encryption key from environment variable."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False):
            store = CredentialStore()
            assert store._encryption_key is not None
            assert store._master_key_salt is not None

    @patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', True)
    @patch('ai_disk_cleanup.security.credential_store.keyring')
    def test_encryption_key_from_keyring(self, mock_keyring):
        """Test getting encryption key from keyring."""
        # Use a proper Fernet key for testing
        from cryptography.fernet import Fernet
        test_key = Fernet.generate_key()
        mock_keyring.get_password.return_value = base64.urlsafe_b64encode(test_key).decode()

        store = CredentialStore()
        assert store._encryption_key is not None
        assert store._master_key_salt is not None

    @patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', True)
    @patch('ai_disk_cleanup.security.credential_store.keyring')
    def test_encrypt_decrypt_data(self, mock_keyring):
        """Test data encryption and decryption."""
        mock_keyring.get_keyring.return_value = Mock()
        mock_keyring.get_password.return_value = None

        store = CredentialStore()
        original_data = "sensitive-api-key"

        # Encrypt data
        encrypted = store._encrypt_data(original_data)
        assert encrypted != original_data
        assert isinstance(encrypted, str)

        # Decrypt data
        decrypted = store._decrypt_data(encrypted)
        assert decrypted == original_data

        # Test that encrypted data has integrity protection
        # Corrupt the data and verify it fails integrity check
        corrupted = encrypted[:-10] + "corrupted"
        try:
            store._decrypt_data(corrupted)
            assert False, "Should have failed integrity check"
        except ValueError:
            pass  # Expected

    @patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', True)
    @patch('ai_disk_cleanup.security.credential_store.keyring')
    def test_get_api_key_from_keyring(self, mock_keyring):
        """Test getting API key from keyring."""
        mock_keyring.get_keyring.return_value = Mock()
        mock_keyring.get_password.return_value = None

        store = CredentialStore()
        encrypted_key = store._encrypt_data("sk-test-key")
        mock_keyring.get_password.return_value = encrypted_key

        api_key = store.get_api_key("openai")
        assert api_key == "sk-test-key"
        mock_keyring.get_password.assert_called_with("ai-disk-cleanup", "api_key_openai")

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-env-key'})
    def test_get_api_key_from_environment(self):
        """Test getting API key from environment variable."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False):
            store = CredentialStore()
            api_key = store.get_api_key("openai")
            assert api_key == "sk-env-key"

    def test_get_api_key_not_found(self):
        """Test getting API key when not found."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False):
            store = CredentialStore()
            api_key = store.get_api_key("nonexistent")
            assert api_key is None

    @patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', True)
    @patch('ai_disk_cleanup.security.credential_store.keyring')
    def test_set_api_key(self, mock_keyring):
        """Test setting API key."""
        mock_keyring.get_keyring.return_value = Mock()
        mock_keyring.get_password.return_value = None

        store = CredentialStore()
        success = store.set_api_key("openai", "sk-new-key")

        assert success is True
        # Should be called at least twice: once for master key, once for API key
        assert mock_keyring.set_password.call_count >= 2

        # Find the API key call (not the master key call)
        api_key_call = None
        for call in mock_keyring.set_password.call_args_list:
            if call[0][1] == "api_key_openai":
                api_key_call = call
                break

        assert api_key_call is not None
        assert api_key_call[0][0] == "ai-disk-cleanup"
        assert api_key_call[0][1] == "api_key_openai"
        # Verify the key was encrypted
        stored_key = api_key_call[0][2]
        assert stored_key != "sk-new-key"

    def test_set_api_key_no_keyring(self):
        """Test setting API key when keyring is not available."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False):
            store = CredentialStore()
            success = store.set_api_key("openai", "sk-test-key")
            assert success is False

    @patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', True)
    @patch('ai_disk_cleanup.security.credential_store.keyring')
    def test_delete_api_key(self, mock_keyring):
        """Test deleting API key."""
        mock_keyring.get_keyring.return_value = Mock()
        mock_keyring.get_password.return_value = None

        store = CredentialStore()
        success = store.delete_api_key("openai")

        assert success is True
        mock_keyring.delete_password.assert_called_once_with("ai-disk-cleanup", "api_key_openai")

    @patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', True)
    @patch('ai_disk_cleanup.security.credential_store.keyring')
    def test_delete_api_key_not_found(self, mock_keyring):
        """Test deleting API key when not found."""
        from keyring.errors import PasswordDeleteError
        mock_keyring.get_keyring.return_value = Mock()
        mock_keyring.get_password.return_value = None
        mock_keyring.delete_password.side_effect = PasswordDeleteError()

        store = CredentialStore()
        success = store.delete_api_key("nonexistent")

        assert success is True  # Should succeed even if key doesn't exist

    @patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', True)
    @patch('ai_disk_cleanup.security.credential_store.keyring')
    def test_list_providers(self, mock_keyring):
        """Test listing providers with stored API keys."""
        mock_keyring.get_keyring.return_value = Mock()
        mock_keyring.get_password.return_value = None

        store = CredentialStore()

        # Mock get_api_key to return keys for some providers
        with patch.object(store, 'get_api_key') as mock_get_key:
            mock_get_key.side_effect = lambda provider: f"key-{provider}" if provider in ["openai", "anthropic"] else None

            providers = store.list_providers()

            assert "openai" in providers
            assert "anthropic" in providers

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-env-key', 'ANTHROPIC_API_KEY': 'sk-ant-env-key'})
    def test_list_providers_with_env_keys(self):
        """Test listing providers with environment variable keys."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False):
            store = CredentialStore()
            providers = store.list_providers()

            assert "openai" in providers
            assert "anthropic" in providers

    def test_test_openai_key_valid(self):
        """Test OpenAI API key validation."""
        store = CredentialStore()
        result = store._test_openai_key("sk-1234567890abcdef1234567890abcdef12345678")

        assert result['valid'] is True
        assert result['provider'] == 'openai'
        assert 'appears valid' in result['message']

    def test_test_openai_key_invalid(self):
        """Test invalid OpenAI API key validation."""
        store = CredentialStore()
        result = store._test_openai_key("invalid-key")

        assert result['valid'] is False
        assert result['provider'] == 'openai'
        assert 'Invalid OpenAI API key format' in result['error']

    def test_test_anthropic_key_valid(self):
        """Test Anthropic API key validation."""
        store = CredentialStore()
        result = store._test_anthropic_key("sk-ant-1234567890abcdef1234567890abcdef12345678")

        assert result['valid'] is True
        assert result['provider'] == 'anthropic'
        assert 'appears valid' in result['message']

    def test_test_anthropic_key_invalid(self):
        """Test invalid Anthropic API key validation."""
        store = CredentialStore()
        result = store._test_anthropic_key("invalid-key")

        assert result['valid'] is False
        assert result['provider'] == 'anthropic'
        assert 'Invalid Anthropic API key format' in result['error']

    def test_test_generic_key_valid(self):
        """Test generic API key validation."""
        store = CredentialStore()
        result = store._test_generic_key("generic-api-key-12345", "custom")

        assert result['valid'] is True
        assert result['provider'] == 'custom'
        assert 'appears valid' in result['message']

    def test_test_generic_key_invalid(self):
        """Test invalid generic API key validation."""
        store = CredentialStore()
        result = store._test_generic_key("short", "custom")

        assert result['valid'] is False
        assert result['provider'] == 'custom'
        assert 'too short' in result['error']

    @patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', True)
    @patch('ai_disk_cleanup.security.credential_store.keyring')
    def test_test_api_key_with_stored_key(self, mock_keyring):
        """Test API key validation with stored key."""
        mock_keyring.get_keyring.return_value = Mock()
        mock_keyring.get_password.return_value = None

        store = CredentialStore()
        # Store a test key
        store.set_api_key("openai", "sk-1234567890abcdef1234567890abcdef12345678")
        mock_keyring.get_password.return_value = store._encrypt_data("sk-1234567890abcdef1234567890abcdef12345678")

        result = store.test_api_key("openai")

        assert result['valid'] is True
        assert result['provider'] == 'openai'

    def test_test_api_key_no_key(self):
        """Test API key validation when no key is available."""
        store = CredentialStore()
        result = store.test_api_key("nonexistent")

        assert result['valid'] is False
        assert 'No API key provided' in result['error']

    def test_get_secure_storage_info_with_keyring(self):
        """Test getting secure storage information when keyring is available."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', True):
            with patch('ai_disk_cleanup.security.credential_store.keyring') as mock_keyring:
                mock_backend = Mock()
                mock_backend.__class__.__name__ = "TestBackend"
                mock_backend.__class__.__module__ = "test.module"
                mock_keyring.get_keyring.return_value = mock_backend

                store = CredentialStore()
                info = store.get_secure_storage_info()

                assert info['keyring_available'] is True
                assert info['encryption_enabled'] is True
                assert 'backend' in info
                assert info['backend']['name'] == "TestBackend"

    def test_get_secure_storage_info_without_keyring(self):
        """Test getting secure storage information when keyring is not available."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False):
            store = CredentialStore()
            info = store.get_secure_storage_info()

            assert info['keyring_available'] is False
            assert info['encryption_enabled'] is True  # Still has encryption
            assert 'backend' not in info

    @patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', True)
    @patch('ai_disk_cleanup.security.credential_store.keyring')
    def test_migrate_credentials(self, mock_keyring):
        """Test credential migration from old service name."""
        mock_keyring.get_keyring.return_value = Mock()

        # Mock that no existing keys for current service
        def mock_get_password_initial(service, username):
            if service == "ai-disk-cleanup":
                return None  # No existing keys
            return None

        mock_keyring.get_password.side_effect = mock_get_password_initial

        # Initialize store first
        store = CredentialStore()

        # Reset the mock to prepare for migration
        mock_keyring.reset_mock()

        # Mock old service having credentials
        def mock_get_password_migration(service, username):
            if service == "old-service":
                if username == "api_key_openai":
                    # Use plain text base64 encoded for this test
                    return base64.urlsafe_b64encode(b"sk-old-openai-key").decode()
                elif username == "api_key_anthropic":
                    return base64.urlsafe_b64encode(b"sk-old-anthropic-key").decode()
            return None

        mock_keyring.get_password.side_effect = mock_get_password_migration

        success = store.migrate_credentials("old-service")

        assert success is True
        # Should have called set_password for migrated keys
        assert mock_keyring.set_password.call_count >= 2

    @patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', True)
    @patch('ai_disk_cleanup.security.credential_store.keyring')
    def test_clear_all_credentials(self, mock_keyring):
        """Test clearing all stored credentials."""
        mock_keyring.get_keyring.return_value = Mock()
        mock_keyring.get_password.return_value = None

        store = CredentialStore()

        # Mock having some providers
        with patch.object(store, 'list_providers', return_value=['openai', 'anthropic']):
            success = store.clear_all_credentials()

        assert success is True
        assert mock_keyring.delete_password.call_count == 2

    def test_clear_all_credentials_no_keyring(self):
        """Test clearing credentials when keyring is not available."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False):
            store = CredentialStore()
            success = store.clear_all_credentials()
            assert success is False

    @patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False)
    def test_error_handling(self):
        """Test error handling in credential operations when keyring is not available."""
        store = CredentialStore()

        # Should handle errors gracefully - encryption should still work with fallback
        assert store._encryption_key is not None  # Fallback encryption should work
        assert store._keyring_available is False  # Keyring should be marked as unavailable

        # API key operations should handle keyring failures gracefully
        api_key = store.get_api_key("openai")
        assert api_key is None  # No stored key, should return None

        success = store.set_api_key("openai", "sk-test")
        assert success is False  # Should fail because keyring storage fails

        success = store.delete_api_key("openai")
        assert success is False  # Should fail because keyring fails

        # Should not crash on any operation
        result = store.test_api_key("openai")
        assert result['valid'] is False
        assert 'provider' in result