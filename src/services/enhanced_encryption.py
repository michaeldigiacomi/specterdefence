"""Enhanced encryption service with AES-256-GCM support and key rotation."""

import base64
import hashlib
import json
import secrets
from datetime import UTC, datetime
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.config import settings


class EncryptionError(Exception):
    """Raised when encryption/decryption operations fail."""

    pass


class KeyRotationError(Exception):
    """Raised when key rotation operations fail."""

    pass


class EncryptedData:
    """Container for encrypted data with metadata."""

    def __init__(
        self,
        ciphertext: str,
        algorithm: str = "fernet",
        key_version: int = 1,
        encrypted_at: str | None = None,
        nonce: str | None = None,
        tag: str | None = None,
    ):
        self.ciphertext = ciphertext
        self.algorithm = algorithm
        self.key_version = key_version
        self.encrypted_at = encrypted_at or datetime.now(UTC).isoformat()
        self.nonce = nonce
        self.tag = tag

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = {
            "ciphertext": self.ciphertext,
            "algorithm": self.algorithm,
            "key_version": self.key_version,
            "encrypted_at": self.encrypted_at,
        }
        if self.nonce:
            data["nonce"] = self.nonce
        if self.tag:
            data["tag"] = self.tag
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EncryptedData":
        """Create from dictionary."""
        return cls(
            ciphertext=data["ciphertext"],
            algorithm=data.get("algorithm", "fernet"),
            key_version=data.get("key_version", 1),
            encrypted_at=data.get("encrypted_at"),
            nonce=data.get("nonce"),
            tag=data.get("tag"),
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "EncryptedData":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


class EnhancedEncryptionService:
    """Enhanced encryption service supporting multiple algorithms and key rotation."""

    # Supported encryption algorithms
    ALGORITHM_FERNET = "fernet"
    ALGORITHM_AES256_GCM = "aes-256-gcm"

    def __init__(self) -> None:
        """Initialize encryption service with key versioning support."""
        self._keys: dict[int, bytes] = {}
        self._fernets: dict[int, Fernet] = {}
        self._current_key_version = 1
        self._init_keys()

    def _init_keys(self) -> None:
        """Initialize encryption keys from configuration."""
        # Primary key (current)
        primary_key = self._derive_key(
            getattr(settings, "ENCRYPTION_KEY", settings.SECRET_KEY),
            getattr(settings, "ENCRYPTION_SALT", None),
            version=1,
        )
        self._keys[1] = primary_key
        self._fernets[1] = Fernet(base64.urlsafe_b64encode(primary_key))

        # Load additional keys for rotation support
        # Format: ENCRYPTION_KEY_v2, ENCRYPTION_KEY_v3, etc.
        version = 2
        while True:
            key_env = getattr(settings, f"ENCRYPTION_KEY_v{version}", None)
            if not key_env:
                break
            salt_env = getattr(settings, f"ENCRYPTION_SALT_v{version}", None)
            key = self._derive_key(key_env, salt_env, version=version)
            self._keys[version] = key
            self._fernets[version] = Fernet(base64.urlsafe_b64encode(key))
            version += 1

        # Determine current key version from env or use latest
        current_version = getattr(settings, "ENCRYPTION_KEY_VERSION", None)
        if current_version:
            self._current_key_version = int(current_version)
        else:
            self._current_key_version = max(self._keys.keys())

    def _derive_key(self, secret_key: str, salt_input: str | None, version: int = 1) -> bytes:
        """Derive encryption key using PBKDF2.

        Args:
            secret_key: Base secret key
            salt_input: Optional salt input
            version: Key version for salt derivation

        Returns:
            32-byte encryption key
        """
        if not secret_key:
            raise EncryptionError("Secret key must be provided")

        secret_key_bytes = secret_key.encode()

        # Use provided salt or derive from secret key with version
        if salt_input:
            salt = hashlib.sha256(salt_input.encode()).digest()[:16]
        else:
            # Include version in salt derivation for key separation
            version_bytes = str(version).encode()
            salt = hashlib.sha256(secret_key_bytes + version_bytes).digest()[:16]

        # OWASP 2023 recommendation: 600,000 iterations for SHA256
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600000,
        )
        return kdf.derive(secret_key_bytes)

    def encrypt(
        self, plaintext: str, algorithm: str | None = None, key_version: int | None = None
    ) -> str:
        """Encrypt a string with metadata.

        Args:
            plaintext: The string to encrypt
            algorithm: Encryption algorithm (default: fernet)
            key_version: Key version to use (default: current)

        Returns:
            JSON string containing encrypted data and metadata
        """
        if not plaintext:
            raise EncryptionError("Cannot encrypt empty string")

        algorithm = algorithm or self.ALGORITHM_FERNET
        key_version = key_version or self._current_key_version

        if algorithm == self.ALGORITHM_FERNET:
            encrypted = self._encrypt_fernet(plaintext, key_version)
            # Fernet returns base64-encoded bytes. We just decode to string.
            ciphertext_str = encrypted["ciphertext"].decode()
            nonce_str = None
            tag_str = None
        elif algorithm == self.ALGORITHM_AES256_GCM:
            encrypted = self._encrypt_aes256_gcm(plaintext, key_version)
            # GCM returns raw bytes. We must base64 encode them.
            ciphertext_str = base64.urlsafe_b64encode(encrypted["ciphertext"]).decode()
            nonce_str = base64.urlsafe_b64encode(encrypted["nonce"]).decode()
            tag_str = base64.urlsafe_b64encode(encrypted["tag"]).decode()
        else:
            raise EncryptionError(f"Unsupported algorithm: {algorithm}")

        # Create encrypted data container
        encrypted_data = EncryptedData(
            ciphertext=ciphertext_str,
            algorithm=algorithm,
            key_version=key_version,
            nonce=nonce_str,
            tag=tag_str,
        )

        return encrypted_data.to_json()

    def _encrypt_fernet(self, plaintext: str, key_version: int) -> dict[str, Any]:
        """Encrypt using Fernet."""
        if key_version not in self._fernets:
            raise EncryptionError(f"Key version {key_version} not available")

        fernet = self._fernets[key_version]
        ciphertext = fernet.encrypt(plaintext.encode())
        return {"ciphertext": ciphertext}

    def _encrypt_aes256_gcm(self, plaintext: str, key_version: int) -> dict[str, Any]:
        """Encrypt using AES-256-GCM."""
        if key_version not in self._keys:
            raise EncryptionError(f"Key version {key_version} not available")

        key = self._keys[key_version]
        aesgcm = AESGCM(key)
        nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM

        # Associated data for integrity (algorithm + version)
        aad = f"aes-256-gcm:v{key_version}".encode()

        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), aad)

        # Split ciphertext and auth tag (last 16 bytes)
        tag = ciphertext[-16:]
        ciphertext = ciphertext[:-16]

        return {"ciphertext": ciphertext, "nonce": nonce, "tag": tag}

    def decrypt(self, encrypted_json: str) -> str:
        """Decrypt an encrypted JSON string.

        Args:
            encrypted_json: JSON string from encrypt()

        Returns:
            Decrypted plaintext string
        """
        if not encrypted_json:
            raise EncryptionError("Cannot decrypt empty string")

        try:
            encrypted_data = EncryptedData.from_json(encrypted_json)
        except (json.JSONDecodeError, KeyError, TypeError):
            # Try legacy format (raw Fernet encrypted string)
            return self._decrypt_legacy(encrypted_json)

        algorithm = encrypted_data.algorithm
        key_version = encrypted_data.key_version
        
        if algorithm == self.ALGORITHM_FERNET:
            # For Fernet, we expect the ciphertext string to be base64.
            # Fernet's decrypt expects base64 bytes.
            try:
                # First try direct encode to bytes (single base64)
                ciphertext = encrypted_data.ciphertext.encode()
                return self._decrypt_fernet(ciphertext, key_version)
            except Exception:
                # If fails, it might be double-encoded from a previous buggy version
                try:
                    ciphertext = base64.urlsafe_b64decode(encrypted_data.ciphertext.encode())
                    return self._decrypt_fernet(ciphertext, key_version)
                except Exception:
                    raise EncryptionError("Failed to decrypt Fernet data") from None
                    
        elif algorithm == self.ALGORITHM_AES256_GCM:
            try:
                ciphertext = base64.urlsafe_b64decode(encrypted_data.ciphertext.encode())
                nonce = base64.urlsafe_b64decode(encrypted_data.nonce.encode())
                tag = base64.urlsafe_b64decode(encrypted_data.tag.encode())
                return self._decrypt_aes256_gcm(ciphertext, nonce, tag, key_version)
            except Exception as e:
                raise EncryptionError(f"AES-GCM decryption failed: {str(e)}") from e
        else:
            raise EncryptionError(f"Unsupported algorithm: {algorithm}")

    def _decrypt_legacy(self, encrypted_str: str) -> str:
        """Decrypt legacy format (raw Fernet string)."""
        if not isinstance(encrypted_str, str):
            raise EncryptionError("Legacy encrypted data must be a string")
            
        # Legacy strings from EncryptionService are double-base64 encoded.
        try:
            # Try double-decode first (most likely for legacy data from EncryptionService)
            decoded1 = base64.urlsafe_b64decode(encrypted_str.encode())
            decoded2 = base64.urlsafe_b64decode(decoded1)
            
            # Try all available keys with double-decoded data
            for _version, fernet in self._fernets.items():
                try:
                    return fernet.decrypt(decoded2).decode()
                except Exception:
                    continue
                    
            # Try single-decode as fallback
            for _version, fernet in self._fernets.items():
                try:
                    return fernet.decrypt(decoded1).decode()
                except Exception:
                    continue
                    
        except Exception:
            # Last resort: try direct decrypt if it's already bytes-like
            for _version, fernet in self._fernets.items():
                try:
                    return fernet.decrypt(encrypted_str.encode()).decode()
                except Exception:
                    continue
            
        raise EncryptionError("Failed to decrypt legacy data with any available key")

    def _decrypt_fernet(self, ciphertext: bytes, key_version: int) -> str:
        """Decrypt using Fernet."""
        if key_version not in self._fernets:
            raise EncryptionError(f"Key version {key_version} not available")

        fernet = self._fernets[key_version]
        return fernet.decrypt(ciphertext).decode()

    def _decrypt_aes256_gcm(
        self, ciphertext: bytes, nonce: bytes, tag: bytes, key_version: int
    ) -> str:
        """Decrypt using AES-256-GCM."""
        if key_version not in self._keys:
            raise EncryptionError(f"Key version {key_version} not available")

        key = self._keys[key_version]
        aesgcm = AESGCM(key)

        # Associated data for integrity verification
        aad = f"aes-256-gcm:v{key_version}".encode()

        # Reconstruct ciphertext with tag
        full_ciphertext = ciphertext + tag

        try:
            plaintext = aesgcm.decrypt(nonce, full_ciphertext, aad)
            return plaintext.decode()
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {str(e)}") from e

    def rotate_key(self, encrypted_json: str) -> str:
        """Re-encrypt data with the current key version.

        Args:
            encrypted_json: Existing encrypted data

        Returns:
            Re-encrypted data with current key
        """
        try:
            # Decrypt with existing key
            plaintext = self.decrypt(encrypted_json)
            # Re-encrypt with current key
            return self.encrypt(plaintext, key_version=self._current_key_version)
        except Exception as e:
            raise KeyRotationError(f"Key rotation failed: {str(e)}") from e

    def get_key_metadata(self, encrypted_json: str) -> dict[str, Any]:
        """Get metadata about encrypted data without decrypting.

        Args:
            encrypted_json: Encrypted data

        Returns:
            Metadata dictionary
        """
        try:
            encrypted_data = EncryptedData.from_json(encrypted_json)
            return {
                "algorithm": encrypted_data.algorithm,
                "key_version": encrypted_data.key_version,
                "encrypted_at": encrypted_data.encrypted_at,
                "needs_rotation": encrypted_data.key_version != self._current_key_version,
            }
        except (json.JSONDecodeError, KeyError):
            # Legacy format
            return {
                "algorithm": "fernet",
                "key_version": "legacy",
                "encrypted_at": None,
                "needs_rotation": True,
            }

    def generate_new_key(self) -> tuple[str, str]:
        """Generate a new encryption key pair.

        Returns:
            Tuple of (key, salt) as base64 strings
        """
        key = secrets.token_bytes(32)
        salt = secrets.token_bytes(16)
        return (base64.urlsafe_b64encode(key).decode(), base64.urlsafe_b64encode(salt).decode())


# Global enhanced encryption service instance
enhanced_encryption_service = EnhancedEncryptionService()
