"""Comprehensive tests for encryption services."""

import base64
from unittest.mock import MagicMock, patch

import pytest

from src.services.encryption import EncryptionService


class TestEncryptionService:
    """Tests for EncryptionService."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypt followed by decrypt returns original data."""
        service = EncryptionService()
        original = "test-secret-data"

        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)

        assert decrypted == original

    def test_encrypt_produces_different_output(self):
        """Test that encryption produces different output than input."""
        service = EncryptionService()
        original = "test-secret-data"

        encrypted = service.encrypt(original)

        assert encrypted != original
        assert isinstance(encrypted, str)

    def test_encrypt_same_data_different_ciphertext(self):
        """Test that encrypting same data twice produces different ciphertext."""
        service = EncryptionService()
        original = "test-secret-data"

        encrypted1 = service.encrypt(original)
        encrypted2 = service.encrypt(original)

        # Should be different due to random IV
        assert encrypted1 != encrypted2

        # But both should decrypt to the same value
        assert service.decrypt(encrypted1) == original
        assert service.decrypt(encrypted2) == original

    def test_decrypt_invalid_data(self):
        """Test decrypting invalid data raises error."""
        service = EncryptionService()

        with pytest.raises(Exception):
            service.decrypt("invalid-base64!!!")

    def test_decrypt_tampered_data(self):
        """Test decrypting tampered data raises error."""
        service = EncryptionService()
        original = "test-secret-data"

        encrypted = service.encrypt(original)

        # Tamper with the encrypted data
        tampered = encrypted[:-5] + "XXXXX"

        with pytest.raises(Exception):
            service.decrypt(tampered)

    def test_encrypt_empty_string(self):
        """Test encrypting empty string raises error."""
        service = EncryptionService()

        with pytest.raises(ValueError, match="Cannot encrypt empty string"):
            service.encrypt("")

    def test_encrypt_unicode(self):
        """Test encrypting unicode characters."""
        service = EncryptionService()
        original = "Hello 世界! Привет мир! 🌍"

        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)

        assert decrypted == original

    def test_encrypt_long_data(self):
        """Test encrypting long data."""
        service = EncryptionService()
        original = "x" * 10000

        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)

        assert decrypted == original

    def test_encryption_service_singleton(self):
        """Test that encryption_service is a singleton-like instance."""
        from src.services.encryption import encryption_service

        assert encryption_service is not None
        assert isinstance(encryption_service, EncryptionService)


class TestEncryptionServiceWithMockKey:
    """Tests with mocked encryption key."""

    @patch("src.services.encryption.settings")
    def test_init_with_explicit_key(self, mock_settings):
        """Test initialization with explicit key."""
        mock_settings.ENCRYPTION_KEY = base64.b64encode(b"0" * 32).decode()
        mock_settings.ENCRYPTION_SALT = base64.b64encode(b"salt" * 8).decode()

        service = EncryptionService()

        assert service.fernet is not None

    @patch("src.services.encryption.settings")
    def test_encryption_with_explicit_key(self, mock_settings):
        """Test encryption/decryption with explicit key."""
        mock_settings.ENCRYPTION_KEY = base64.b64encode(b"0" * 32).decode()
        mock_settings.ENCRYPTION_SALT = base64.b64encode(b"salt" * 8).decode()

        service = EncryptionService()
        original = "test-data"

        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)

        assert decrypted == original
