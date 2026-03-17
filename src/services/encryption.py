"""Legacy encryption service wrapper for backward compatibility."""

import logging
from src.services.enhanced_encryption import enhanced_encryption_service, EncryptionError

logger = logging.getLogger(__name__)

class EncryptionService:
    """Legacy service for encrypting and decrypting sensitive data.
    
    Now wraps EnhancedEncryptionService to unify encryption across the backend.
    """

    def __init__(self) -> None:
        """Initialize encryption service (wraps enhanced service)."""
        self.service = enhanced_encryption_service

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string using the enhanced service.

        Args:
            plaintext: The string to encrypt.

        Returns:
            JSON encoded encrypted string with metadata.
        """
        try:
            # Use Fernet by default for legacy compatibility if needed, 
            # but it will be wrapped in the new JSON format.
            return self.service.encrypt(plaintext)
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError(f"Cannot encrypt string: {e}") from e

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt an encrypted string.

        Args:
            ciphertext: The encrypted string to decrypt (supports legacy and new formats).

        Returns:
            Decrypted plaintext string.
        """
        try:
            return self.service.decrypt(ciphertext)
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Cannot decrypt string: {e}") from e


# Global encryption service instance for backward compatibility
encryption_service = EncryptionService()
