"""Unit tests for encryption service."""

import sys

import pytest
from cryptography.fernet import InvalidToken

# Remove any mock encryption module before importing
encryption_modules = [
    key
    for key in sys.modules
    if "encryption" in key.lower() and key != "tests.unit.test_encryption"
]
for key in encryption_modules:
    del sys.modules[key]

from src.services.encryption import EncryptionService, encryption_service


class TestEncryptionService:
    """Test cases for EncryptionService."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypt and decrypt are inverse operations."""
        service = EncryptionService()
        original = "my-super-secret-value"

        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)

        assert encrypted != original
        assert decrypted == original

    def test_encrypt_different_results(self):
        """Test that encrypting same value twice gives different results (Fernet uses random IV)."""
        service = EncryptionService()
        value = "test-value"

        encrypted1 = service.encrypt(value)
        encrypted2 = service.encrypt(value)

        # Due to random IV, encrypted values should be different
        assert encrypted1 != encrypted2

        # But both should decrypt to the same value
        assert service.decrypt(encrypted1) == value
        assert service.decrypt(encrypted2) == value

    def test_encrypt_empty_string_raises(self):
        """Test that encrypting empty string raises ValueError."""
        service = EncryptionService()

        with pytest.raises(ValueError, match="Cannot encrypt empty string"):
            service.encrypt("")

    def test_decrypt_empty_string_raises(self):
        """Test that decrypting empty string raises ValueError."""
        service = EncryptionService()

        with pytest.raises(ValueError, match="Cannot decrypt empty string"):
            service.decrypt("")

    def test_decrypt_invalid_data_raises(self):
        """Test that decrypting invalid data raises an error."""
        service = EncryptionService()

        with pytest.raises((InvalidToken, Exception)):
            service.decrypt("not-valid-encrypted-data")

    def test_global_encryption_service(self):
        """Test that global encryption service is initialized."""
        assert encryption_service is not None
        assert isinstance(encryption_service, EncryptionService)

        # Test basic operation
        value = "test"
        encrypted = encryption_service.encrypt(value)
        decrypted = encryption_service.decrypt(encrypted)
        assert decrypted == value

    def test_encrypt_special_characters(self):
        """Test encryption of strings with special characters."""
        service = EncryptionService()
        special_values = [
            "value with spaces",
            "value\nwith\nnewlines",
            "value\twith\ttabs",
            "value!@#$%^&*()_+-=[]{}|;':\",./<>?",
            "unicode: ñ 中文 🎉",
            "a" * 1000,  # Long string
        ]

        for value in special_values:
            encrypted = service.encrypt(value)
            decrypted = service.decrypt(encrypted)
            assert decrypted == value, f"Failed for value: {value[:50]}"

    def test_encrypt_binary_like_data(self):
        """Test encryption of binary-like string data."""
        service = EncryptionService()
        binary_like = "\\x00\\x01\\x02\\x03"

        encrypted = service.encrypt(binary_like)
        decrypted = service.decrypt(encrypted)

        assert decrypted == binary_like
