"""Encryption service for sensitive data."""

import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.config import settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self) -> None:
        """Initialize encryption service with key derived from SECRET_KEY."""
        # Use SECRET_KEY to derive encryption key
        secret_key = settings.SECRET_KEY.encode()
        
        # Use a fixed salt (in production, this should be stored securely)
        salt = b"specterdefence_salt_v1"
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret_key))
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
