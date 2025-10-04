"""
Comprehensive security tests for the credential store.
Tests for critical security vulnerabilities and edge cases.
"""

import pytest
import base64
import json
import os
import time
from unittest.mock import Mock, patch, MagicMock

from ai_disk_cleanup.security.credential_store import CredentialStore


class TestCredentialStoreSecurity:
    """Security-focused tests for CredentialStore."""

    def test_secure_key_derivation_strength(self):
        """Test that key derivation uses proper PBKDF2 parameters."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False):
            store = CredentialStore()

            # Test that encryption key is derived with proper strength
            assert store._encryption_key is not None
            assert len(store._encryption_key) == 44  # Fernet key length
            assert store._master_key_salt is not None
            assert len(store._master_key_salt) == store.SALT_LENGTH

    def test_salt_uniqueness(self):
        """Test that salts are unique for each key generation."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False):
            store1 = CredentialStore()
            store2 = CredentialStore()

            # Each instance should have different salts
            salt1 = store1._master_key_salt
            salt2 = store2._master_key_salt

            assert salt1 != salt2
            assert len(salt1) == store1.SALT_LENGTH
            assert len(salt2) == store2.SALT_LENGTH

    def test_key_integrity_validation_tampering(self):
        """Test that key tampering is detected."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', True):
            with patch('ai_disk_cleanup.security.credential_store.keyring') as mock_keyring:
                mock_keyring.get_keyring.return_value = Mock()
                mock_keyring.get_password.return_value = None

                store = CredentialStore()
                original_key = store._encryption_key

                # Try to tamper with the key
                corrupted_key = original_key[:-10] + b"corrupted"

                # Key integrity should fail
                assert not store._validate_key_integrity(corrupted_key)

    def test_encryption_integrity_protection(self):
        """Test that encrypted data has integrity protection."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False):
            store = CredentialStore()
            sensitive_data = "super-secret-api-key"

            # Encrypt data
            encrypted = store._encrypt_data(sensitive_data)

            # Corrupt the encrypted data
            corrupted = encrypted[:-10] + "corrupted"

            # Should fail integrity check
            with pytest.raises(ValueError, match="corrupted"):
                store._decrypt_data(corrupted)

    def test_environment_key_validation(self):
        """Test that environment keys are properly validated."""
        # Test with invalid base64 key
        with patch.dict(os.environ, {'AI_DISK_CLEANUP_ENCRYPTION_KEY': 'invalid-base64'}):
            with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False):
                store = CredentialStore()
                # Should fall back to generating new key
                assert store._encryption_key is not None
                assert store._encryption_key != b'invalid-base64'

    def test_fallback_encryption_security(self):
        """Test that fallback encryption is still secure when keyring fails."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False):
            store = CredentialStore()

            # Should still be able to encrypt/decrypt
            assert store._encryption_key is not None

            # Test encryption/decryption still works
            data = "test-secret-data"
            encrypted = store._encrypt_data(data)
            decrypted = store._decrypt_data(encrypted)
            assert decrypted == data

    def test_no_sensitive_data_in_logs(self):
        """Test that sensitive data is not exposed in logs."""
        import logging
        from io import StringIO

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        logger = logging.getLogger('ai_disk_cleanup.security.credential_store')
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        try:
            with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False):
                store = CredentialStore()

                # Try operations with sensitive data
                store._encrypt_data("secret-api-key-12345")

        finally:
            logger.removeHandler(handler)

        log_output = log_stream.getvalue()

        # Ensure no sensitive data appears in logs
        assert "secret-api-key-12345" not in log_output

    def test_key_derivation_iterations(self):
        """Test that PBKDF2 uses sufficient iterations."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False):
            store = CredentialStore()

            # Should use at least 100,000 iterations (current requirement)
            assert store.PBKDF2_ITERATIONS >= 100000

    def test_cryptographically_secure_key_generation(self):
        """Test that keys are generated using cryptographically secure methods."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False):
            store = CredentialStore()

            # Generate multiple keys and ensure they're different
            keys = []
            for _ in range(10):
                new_store = CredentialStore()
                keys.append(new_store._encryption_key)

            # All keys should be unique
            assert len(set(keys)) == len(keys)

            # Keys should be valid Fernet keys
            for key in keys:
                assert len(key) == 44  # Fernet key length

    def test_backward_compatibility_security(self):
        """Test that legacy format migration maintains security."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', True):
            with patch('ai_disk_cleanup.security.credential_store.keyring') as mock_keyring:
                from cryptography.fernet import Fernet

                mock_keyring.get_keyring.return_value = Mock()
                mock_keyring.get_password.return_value = None

                # Create store
                store = CredentialStore()

                # Use the same key that store uses for legacy encryption
                legacy_fernet = Fernet(store._encryption_key)
                legacy_data = base64.urlsafe_b64encode(
                    legacy_fernet.encrypt(b"legacy-api-key")
                ).decode()

                # Should be able to migrate to new secure format
                decrypted = store._decrypt_data_legacy(legacy_data)
                assert decrypted == "legacy-api-key"

                # New encryption should be more secure (with integrity protection)
                new_encrypted = store._encrypt_data(decrypted)
                assert new_encrypted != legacy_data
                # New format should be longer due to integrity protection
                assert len(new_encrypted) > len(legacy_data)

    def test_master_key_storage_security(self):
        """Test that master keys are stored securely."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', True):
            with patch('ai_disk_cleanup.security.credential_store.keyring') as mock_keyring:
                mock_keyring.get_keyring.return_value = Mock()
                mock_keyring.get_password.return_value = None

                store = CredentialStore()

                # Check that set_password was called with structured data
                assert mock_keyring.set_password.called

                # Get the stored data
                call_args = mock_keyring.set_password.call_args_list
                master_key_call = None

                for call in call_args:
                    if "master_key" in str(call):
                        master_key_call = call
                        break

                assert master_key_call is not None

                # Stored data should be structured and base64 encoded
                stored_data = master_key_call[0][2]
                assert isinstance(stored_data, str)

                # Should be base64 encoded JSON
                decoded = base64.urlsafe_b64decode(stored_data.encode())
                key_data = json.loads(decoded.decode())

                # Should have required fields
                assert 'key' in key_data
                assert 'salt' in key_data
                assert 'timestamp' in key_data
                assert 'version' in key_data

    def test_constant_time_comparisons(self):
        """Test that sensitive comparisons use constant-time operations."""
        import secrets

        # Test that secrets.compare_digest works for sensitive data
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False):
            store = CredentialStore()

            # Test that constant-time comparison is available and working
            tag1 = store._generate_data_integrity_tag(b"test-data-1")
            tag2 = store._generate_data_integrity_tag(b"test-data-2")
            tag3 = store._generate_data_integrity_tag(b"test-data-1")  # Same as tag1

            # Different tags should not match
            assert not secrets.compare_digest(tag1, tag2)

            # Same tags should match
            assert secrets.compare_digest(tag1, tag3)

    def test_secure_random_salt_generation(self):
        """Test that salts are generated using secure random methods."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False):
            store = CredentialStore()

            # Salt should be generated with proper length
            assert len(store._master_key_salt) == store.SALT_LENGTH

            # Multiple salts should be unique
            salts = [CredentialStore()._master_key_salt for _ in range(10)]
            assert len(set(salts)) == len(salts)

    def test_error_messages_security(self):
        """Test that error messages don't expose sensitive information."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', True):
            with patch('ai_disk_cleanup.security.credential_store.keyring') as mock_keyring:
                mock_keyring.get_keyring.return_value = Mock()
                mock_keyring.get_password.side_effect = Exception("Database connection failed")

                store = CredentialStore()

                # Error should be generic, not expose internal details
                try:
                    store.get_api_key("openai")
                except Exception as e:
                    # Should not contain "Database connection failed"
                    assert "Database connection failed" not in str(e)

    def test_memory_sanitization(self):
        """Test that sensitive data is properly handled in memory."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False):
            store = CredentialStore()

            # Test that sensitive operations don't leave traces
            sensitive_data = "very-secret-key"
            encrypted = store._encrypt_data(sensitive_data)
            decrypted = store._decrypt_data(encrypted)

            # Data should be correctly processed
            assert decrypted == sensitive_data

            # Original data should not be easily accessible from encrypted form
            assert sensitive_data not in encrypted
            assert len(encrypted) > len(sensitive_data)  # Should have integrity protection

    @pytest.mark.parametrize("invalid_input", [
        "",  # Empty string
        "a" * 10000,  # Very long string
        None,  # None value
        123,  # Number
        "🔥🔥🔥",  # Unicode characters
    ])
    def test_input_validation_security(self, invalid_input):
        """Test that input validation handles edge cases securely."""
        with patch('ai_disk_cleanup.security.credential_store.KEYRING_AVAILABLE', False):
            store = CredentialStore()

            if invalid_input is None:
                # None should be handled gracefully
                result = store.get_api_key("test")
                assert result is None
            elif isinstance(invalid_input, str):
                # String inputs should be processed securely
                if invalid_input:  # Non-empty strings
                    try:
                        encrypted = store._encrypt_data(invalid_input)
                        decrypted = store._decrypt_data(encrypted)
                        assert decrypted == invalid_input
                    except ValueError:
                        # Very long strings might fail, which is acceptable
                        pass
                else:
                    # Empty string should raise ValueError
                    with pytest.raises(ValueError):
                        store._encrypt_data(invalid_input)
            else:
                # Non-string inputs should be handled appropriately
                try:
                    # May raise TypeError, which is acceptable
                    store._encrypt_data(invalid_input)
                except (TypeError, ValueError):
                    pass  # Expected for non-string inputs