"""Encryption service for sensitive data."""

import base64
import hashlib

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.config import settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self) -> None:
        """Initialize encryption service with key derived from SECRET_KEY or ENCRYPTION_KEY."""
        # Use dedicated encryption key if available, fall back to SECRET_KEY
        secret_key = getattr(settings, 'ENCRYPTION_KEY', settings.SECRET_KEY)
        if not secret_key:
            raise ValueError("ENCRYPTION_KEY or SECRET_KEY must be set")

        secret_key_bytes = secret_key.encode()

        # Use configurable salt from environment, or derive from secret key
        # In production, ENCRYPTION_SALT should be set to a unique value
        salt_input = getattr(settings, 'ENCRYPTION_SALT', None)
        if salt_input:
            # Use provided salt, hash it to ensure consistent length
            salt = hashlib.sha256(salt_input.encode()).digest()[:16]
        else:
            # Derive salt from secret key (deterministic but unique per deployment)
            salt = hashlib.sha256(secret_key_bytes).digest()[:16]

        # OWASP 2023 recommendation: 600,000 iterations for SHA256
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret_key_bytes))
        self.fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string.
        
        Args:
            plaintext: The string to encrypt.
            
        Returns:
            Base64 encoded encrypted string.
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")
        encrypted = self.fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt an encrypted string.
        
        Args:
            ciphertext: The encrypted string to decrypt.
            
        Returns:
            Decrypted plaintext string.
        """
        if not ciphertext:
            raise ValueError("Cannot decrypt empty string")
        encrypted = base64.urlsafe_b64decode(ciphertext.encode())
        return self.fernet.decrypt(encrypted).decode()


# Global encryption service instance
encryption_service = EncryptionService()
