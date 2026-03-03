"""Unified credential storage manager supporting multiple backends."""

import contextlib
import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.db import TenantModel
from src.services.enhanced_encryption import EnhancedEncryptionService, enhanced_encryption_service
from src.services.k8s_secrets_storage import (
    CredentialData,
    K8sSecretNotFoundError,
    K8sSecretsStorage,
    get_k8s_storage,
)

# Audit logger for credential access
audit_logger = logging.getLogger('specterdefence.audit')
if not audit_logger.handlers:
    audit_handler = logging.StreamHandler()
    audit_handler.setFormatter(logging.Formatter(
        '%(asctime)s - AUDIT - %(message)s'
    ))
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.WARNING)


class StorageBackend(Enum):
    """Storage backend types."""
    DATABASE = "database"
    K8S_SECRETS = "k8s_secrets"
    HYBRID = "hybrid"  # Metadata in DB, secrets in K8s


class CredentialStorageError(Exception):
    """Raised when credential storage operations fail."""
    pass


class CredentialNotFoundError(CredentialStorageError):
    """Raised when credentials are not found."""
    pass


@dataclass
class StoredCredential:
    """Container for stored credential with metadata."""
    tenant_id: str
    client_id: str
    client_secret: str
    backend: StorageBackend
    encrypted: bool
    key_version: int | None = None
    k8s_secret_name: str | None = None


class CredentialStorageManager:
    """Unified manager for tenant credential storage.

    Supports multiple storage backends:
    - DATABASE: Credentials encrypted and stored in PostgreSQL/SQLite
    - K8S_SECRETS: Credentials stored in Kubernetes secrets
    - HYBRID: Tenant metadata in DB, credentials in K8s secrets
    """

    def __init__(
        self,
        db: AsyncSession,
        default_backend: StorageBackend = StorageBackend.DATABASE,
        encryption_service: EnhancedEncryptionService | None = None,
        k8s_storage: K8sSecretsStorage | None = None
    ) -> None:
        """Initialize credential storage manager.

        Args:
            db: Database session
            default_backend: Default storage backend
            encryption_service: Encryption service instance
            k8s_storage: K8s secrets storage instance
        """
        self.db = db
        self.default_backend = default_backend
        self.encryption = encryption_service or enhanced_encryption_service
        self.k8s_storage = k8s_storage or get_k8s_storage()

    async def store_credentials(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        name: str,
        backend: StorageBackend | None = None,
        encrypt: bool = True
    ) -> StoredCredential:
        """Store credentials using specified backend.

        Args:
            tenant_id: Azure AD tenant ID
            client_id: Azure AD application ID
            client_secret: Azure AD client secret
            name: Tenant display name
            backend: Storage backend to use (default: manager default)
            encrypt: Whether to encrypt secrets (for DB backend)

        Returns:
            Stored credential information
        """
        backend = backend or self.default_backend

        # Privacy-preserving tenant hash for audit logs
        tenant_hash = hashlib.sha256(tenant_id.encode()).hexdigest()[:16]

        audit_logger.warning(
            f"CREDENTIAL_STORE: tenant_hash={tenant_hash} "
            f"backend={backend.value} encrypt={encrypt} "
            f"timestamp={datetime.now(UTC).isoformat()}"
        )

        if backend == StorageBackend.DATABASE:
            return await self._store_in_database(
                tenant_id, client_id, client_secret, name, encrypt
            )
        elif backend == StorageBackend.K8S_SECRETS:
            return await self._store_in_k8s(
                tenant_id, client_id, client_secret, name
            )
        elif backend == StorageBackend.HYBRID:
            return await self._store_hybrid(
                tenant_id, client_id, client_secret, name
            )
        else:
            raise CredentialStorageError(f"Unsupported backend: {backend}")

    async def _store_in_database(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        name: str,
        encrypt: bool
    ) -> StoredCredential:
        """Store credentials in database with encryption."""
        if encrypt:
            # Use AES-256-GCM for new credentials
            encrypted_secret = self.encryption.encrypt(
                client_secret,
                algorithm=EnhancedEncryptionService.ALGORITHM_AES256_GCM
            )
            key_version = self.encryption._current_key_version
        else:
            # Store plaintext (not recommended)
            encrypted_secret = client_secret
            key_version = None

        # Check if tenant exists
        result = await self.db.execute(
            select(TenantModel).where(TenantModel.tenant_id == tenant_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing tenant
            existing.client_id = client_id
            existing.client_secret = encrypted_secret
            existing.name = name
        else:
            # Create new tenant
            tenant = TenantModel(
                name=name,
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=encrypted_secret
            )
            self.db.add(tenant)

        await self.db.commit()

        return StoredCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,  # Return original for immediate use
            backend=StorageBackend.DATABASE,
            encrypted=encrypt,
            key_version=key_version
        )

    async def _store_in_k8s(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        name: str
    ) -> StoredCredential:
        """Store credentials in Kubernetes secrets."""
        credentials = CredentialData(
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            metadata={"name": name, "created_at": datetime.now(UTC).isoformat()}
        )

        secret_name = self.k8s_storage.store_credentials(tenant_id, credentials)

        return StoredCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            backend=StorageBackend.K8S_SECRETS,
            encrypted=False,  # K8s handles encryption at rest
            k8s_secret_name=secret_name
        )

    async def _store_hybrid(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        name: str
    ) -> StoredCredential:
        """Store using hybrid approach: metadata in DB, secrets in K8s."""
        # Store credentials in K8s
        credentials = CredentialData(
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            metadata={"name": name}
        )

        secret_name = self.k8s_storage.store_credentials(tenant_id, credentials)

        # Store metadata in DB
        result = await self.db.execute(
            select(TenantModel).where(TenantModel.tenant_id == tenant_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.name = name
            existing.client_id = client_id  # Store client_id for reference
            existing.client_secret = f"k8s:{secret_name}"  # Reference to K8s secret
        else:
            tenant = TenantModel(
                name=name,
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=f"k8s:{secret_name}"
            )
            self.db.add(tenant)

        await self.db.commit()

        return StoredCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            backend=StorageBackend.HYBRID,
            encrypted=True,
            k8s_secret_name=secret_name
        )

    async def get_credentials(
        self,
        tenant_id: str,
        user_id: str = "system"
    ) -> StoredCredential:
        """Retrieve credentials from storage.

        Args:
            tenant_id: Azure AD tenant ID
            user_id: Identifier of user/system accessing the credential

        Returns:
            Stored credential with decrypted secret

        Raises:
            CredentialNotFoundError: If credentials not found
        """
        # Privacy-preserving tenant hash for audit logs
        tenant_hash = hashlib.sha256(tenant_id.encode()).hexdigest()[:16]

        audit_logger.warning(
            f"CREDENTIAL_ACCESS: user={user_id} tenant_hash={tenant_hash} "
            f"timestamp={datetime.now(UTC).isoformat()}"
        )

        # First, try to determine backend from DB
        result = await self.db.execute(
            select(TenantModel).where(TenantModel.tenant_id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise CredentialNotFoundError(f"Tenant {tenant_id} not found")

        # Determine storage backend from client_secret format
        if tenant.client_secret.startswith("k8s:"):
            # Hybrid storage
            secret_name = tenant.client_secret[4:]  # Remove "k8s:" prefix
            return await self._get_from_k8s(tenant_id, tenant, secret_name, user_id)
        else:
            # Database storage (check if encrypted)
            return await self._get_from_database(tenant_id, tenant, user_id)

    async def _get_from_database(
        self,
        tenant_id: str,
        tenant: TenantModel,
        user_id: str
    ) -> StoredCredential:
        """Retrieve credentials from database."""
        client_secret = tenant.client_secret

        # Check if encrypted (JSON format)
        if client_secret.startswith('{'):
            # Encrypted with metadata
            try:
                metadata = self.encryption.get_key_metadata(client_secret)
                client_secret = self.encryption.decrypt(client_secret)
                key_version = metadata.get("key_version")
            except Exception as e:
                raise CredentialStorageError(f"Failed to decrypt credentials: {e}") from e
        else:
            # Legacy format or unencrypted
            try:
                client_secret = self.encryption.decrypt(client_secret)
                key_version = "legacy"
            except Exception:
                # Assume plaintext
                key_version = None

        return StoredCredential(
            tenant_id=tenant_id,
            client_id=tenant.client_id,
            client_secret=client_secret,
            backend=StorageBackend.DATABASE,
            encrypted=True,
            key_version=key_version
        )

    async def _get_from_k8s(
        self,
        tenant_id: str,
        tenant: TenantModel,
        secret_name: str,
        user_id: str
    ) -> StoredCredential:
        """Retrieve credentials from Kubernetes secrets."""
        try:
            credentials = self.k8s_storage.get_credentials(tenant_id, user_id)
        except K8sSecretNotFoundError:
            raise CredentialNotFoundError(
                f"Credentials for tenant {tenant_id} not found in K8s secrets"
            ) from None

        return StoredCredential(
            tenant_id=tenant_id,
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            backend=StorageBackend.K8S_SECRETS,
            encrypted=True,
            k8s_secret_name=secret_name
        )

    async def rotate_encryption_key(
        self,
        tenant_id: str,
        user_id: str = "system"
    ) -> StoredCredential:
        """Rotate encryption key for stored credentials.

        Args:
            tenant_id: Azure AD tenant ID
            user_id: Identifier of user performing rotation

        Returns:
            Stored credential with new encryption
        """
        # Privacy-preserving tenant hash for audit logs
        tenant_hash = hashlib.sha256(tenant_id.encode()).hexdigest()[:16]

        audit_logger.warning(
            f"CREDENTIAL_KEY_ROTATION: user={user_id} tenant_hash={tenant_hash} "
            f"timestamp={datetime.now(UTC).isoformat()}"
        )

        # Get current credentials
        current = await self.get_credentials(tenant_id, user_id)

        if current.backend == StorageBackend.DATABASE:
            # Re-encrypt with current key
            result = await self.db.execute(
                select(TenantModel).where(TenantModel.tenant_id == tenant_id)
            )
            tenant = result.scalar_one()

            # Encrypt with current key
            encrypted_secret = self.encryption.encrypt(
                current.client_secret,
                algorithm=EnhancedEncryptionService.ALGORITHM_AES256_GCM
            )

            tenant.client_secret = encrypted_secret
            await self.db.commit()

            # Return updated credential
            new_credential = await self.get_credentials(tenant_id, user_id)
            return new_credential

        elif current.backend == StorageBackend.K8S_SECRETS:
            # K8s secrets handle their own encryption at rest
            # Just update the metadata to indicate rotation
            credentials = CredentialData(
                client_id=current.client_id,
                client_secret=current.client_secret,
                tenant_id=tenant_id,
                metadata={
                    "key_rotated_at": datetime.now(UTC).isoformat(),
                    "rotated_by": user_id
                }
            )
            self.k8s_storage.update_credentials(tenant_id, credentials, user_id)
            return current

        else:
            raise CredentialStorageError(
                f"Key rotation not supported for backend: {current.backend}"
            )

    async def migrate_backend(
        self,
        tenant_id: str,
        target_backend: StorageBackend,
        user_id: str = "system"
    ) -> StoredCredential:
        """Migrate credentials to a different storage backend.

        Args:
            tenant_id: Azure AD tenant ID
            target_backend: Target storage backend
            user_id: Identifier of user performing migration

        Returns:
            Stored credential in new backend
        """
        # Privacy-preserving tenant hash for audit logs
        tenant_hash = hashlib.sha256(tenant_id.encode()).hexdigest()[:16]

        audit_logger.warning(
            f"CREDENTIAL_MIGRATION: user={user_id} tenant_hash={tenant_hash} "
            f"target_backend={target_backend.value} "
            f"timestamp={datetime.now(UTC).isoformat()}"
        )

        # Get current credentials
        current = await self.get_credentials(tenant_id, user_id)

        if current.backend == target_backend:
            return current  # Already on target backend

        result = await self.db.execute(
            select(TenantModel).where(TenantModel.tenant_id == tenant_id)
        )
        tenant = result.scalar_one()

        # Store in new backend
        new_credential = await self.store_credentials(
            tenant_id=tenant_id,
            client_id=current.client_id,
            client_secret=current.client_secret,
            name=tenant.name,
            backend=target_backend
        )

        # Clean up old backend if needed
        if current.backend == StorageBackend.K8S_SECRETS and current.k8s_secret_name:
            with contextlib.suppress(Exception):
                self.k8s_storage.delete_credentials(tenant_id, user_id)  # Best effort cleanup

        return new_credential

    async def delete_credentials(
        self,
        tenant_id: str,
        user_id: str = "system"
    ) -> bool:
        """Delete credentials from all storage backends.

        Args:
            tenant_id: Azure AD tenant ID
            user_id: Identifier of user performing deletion

        Returns:
            True if deleted, False if not found
        """
        # Privacy-preserving tenant hash for audit logs
        tenant_hash = hashlib.sha256(tenant_id.encode()).hexdigest()[:16]

        audit_logger.warning(
            f"CREDENTIAL_DELETE: user={user_id} tenant_hash={tenant_hash} "
            f"timestamp={datetime.now(UTC).isoformat()}"
        )

        result = await self.db.execute(
            select(TenantModel).where(TenantModel.tenant_id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            return False

        deleted = False

        # Check for K8s secrets
        if tenant.client_secret.startswith("k8s:"):
            try:
                self.k8s_storage.delete_credentials(tenant_id, user_id)
                deleted = True
            except Exception:
                pass

        # Delete from database
        await self.db.delete(tenant)
        await self.db.commit()
        deleted = True

        return deleted

    def get_key_metadata(self, tenant_id: str, encrypted_data: str) -> dict[str, Any]:
        """Get encryption key metadata for credentials.

        Args:
            tenant_id: Tenant ID
            encrypted_data: Encrypted credential data

        Returns:
            Key metadata
        """
        return self.encryption.get_key_metadata(encrypted_data)

    async def health_check(self) -> dict[str, Any]:
        """Check storage backend health.

        Returns:
            Health check results for all backends
        """
        return {
            "database": {"status": "healthy"},  # Assume healthy if we got here
            "k8s_secrets": self.k8s_storage.health_check()
        }
