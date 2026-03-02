"""Kubernetes secrets storage backend for tenant credentials."""

import base64
import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Audit logger for credential access
audit_logger = logging.getLogger('specterdefence.audit')
if not audit_logger.handlers:
    audit_handler = logging.StreamHandler()
    audit_handler.setFormatter(logging.Formatter(
        '%(asctime)s - AUDIT - %(message)s'
    ))
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.WARNING)


class K8sSecretError(Exception):
    """Raised when Kubernetes secret operations fail."""
    pass


class K8sSecretNotFoundError(K8sSecretError):
    """Raised when a Kubernetes secret is not found."""
    pass


class K8sSecretAlreadyExistsError(K8sSecretError):
    """Raised when trying to create a secret that already exists."""
    pass


@dataclass
class CredentialData:
    """Container for credential data."""
    client_id: str
    client_secret: str
    tenant_id: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for secret storage."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        if self.tenant_id:
            data["tenant_id"] = self.tenant_id
        if self.metadata:
            data["metadata"] = json.dumps(self.metadata)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "CredentialData":
        """Create from dictionary."""
        metadata = None
        if "metadata" in data:
            try:
                metadata = json.loads(data["metadata"])
            except json.JSONDecodeError:
                pass

        return cls(
            client_id=data.get("client_id", ""),
            client_secret=data.get("client_secret", ""),
            tenant_id=data.get("tenant_id"),
            metadata=metadata
        )


class K8sSecretsStorage:
    """Kubernetes secrets storage backend for tenant credentials.
    
    This class provides an interface to store and retrieve tenant credentials
    from Kubernetes secrets, with support for both in-cluster and external
    Kubernetes API access.
    
    Credentials are mounted as files in a volume when running in Kubernetes,
    or accessed via the Kubernetes API when running externally.
    """

    # Default namespace for secrets
    DEFAULT_NAMESPACE = "specterdefence"

    # Default secret name prefix
    SECRET_PREFIX = "tenant-credentials"

    # Volume mount path for secrets (when running in-cluster)
    VOLUME_MOUNT_PATH = "/etc/secrets/tenants"

    def __init__(
        self,
        namespace: str | None = None,
        use_k8s_api: bool = False,
        kubeconfig_path: str | None = None
    ) -> None:
        """Initialize K8s secrets storage.
        
        Args:
            namespace: Kubernetes namespace for secrets
            use_k8s_api: Whether to use Kubernetes API instead of volume mounts
            kubeconfig_path: Path to kubeconfig file (for external access)
        """
        self.namespace = namespace or os.getenv('K8S_NAMESPACE', self.DEFAULT_NAMESPACE)
        self.use_k8s_api = use_k8s_api or os.getenv('K8S_USE_API', 'false').lower() == 'true'
        self.kubeconfig_path = kubeconfig_path or os.getenv('KUBECONFIG')
        self._k8s_client = None

        # Check if running in Kubernetes (secrets volume available)
        self._in_cluster = self._detect_in_cluster()

        if self.use_k8s_api:
            self._init_k8s_client()

    def _detect_in_cluster(self) -> bool:
        """Detect if running inside a Kubernetes cluster.
        
        Returns:
            True if running in-cluster, False otherwise
        """
        # Check for service account token
        service_account_token = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")
        return service_account_token.exists()

    def _init_k8s_client(self) -> None:
        """Initialize Kubernetes client."""
        try:
            from kubernetes import client, config

            if self._in_cluster:
                # Use in-cluster config
                config.load_incluster_config()
                audit_logger.info("K8S_CLIENT: Using in-cluster configuration")
            elif self.kubeconfig_path and Path(self.kubeconfig_path).exists():
                # Use kubeconfig file
                config.load_kube_config(config_file=self.kubeconfig_path)
                audit_logger.info(f"K8S_CLIENT: Using kubeconfig from {self.kubeconfig_path}")
            else:
                # Try default kubeconfig
                config.load_kube_config()
                audit_logger.info("K8S_CLIENT: Using default kubeconfig")

            self._k8s_client = client.CoreV1Api()

        except ImportError:
            raise K8sSecretError(
                "Kubernetes client library not installed. "
                "Install with: pip install kubernetes"
            )
        except Exception as e:
            raise K8sSecretError(f"Failed to initialize Kubernetes client: {str(e)}")

    def _sanitize_secret_name(self, name: str) -> str:
        """Sanitize a name for use as a Kubernetes secret name.
        
        Kubernetes secret names must:
        - Be lowercase alphanumeric, '-', or '.'
        - Start and end with alphanumeric
        - Max 253 characters
        
        Args:
            name: Original name
            
        Returns:
            Sanitized name
        """
        # Convert to lowercase and replace invalid chars
        sanitized = re.sub(r'[^a-z0-9.-]', '-', name.lower())
        # Remove leading/trailing non-alphanumeric
        sanitized = sanitized.strip('-.')
        # Limit length
        if len(sanitized) > 253:
            sanitized = sanitized[:253]
        return sanitized or "unnamed"

    def _get_secret_name(self, tenant_id: str) -> str:
        """Generate secret name for a tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Secret name
        """
        # Use hash of tenant_id to avoid exposing it in secret name
        tenant_hash = hashlib.sha256(tenant_id.encode()).hexdigest()[:16]
        return f"{self.SECRET_PREFIX}-{tenant_hash}"

    def store_credentials(
        self,
        tenant_id: str,
        credentials: CredentialData,
        labels: dict[str, str] | None = None
    ) -> str:
        """Store credentials in Kubernetes secret.
        
        Args:
            tenant_id: Tenant identifier
            credentials: Credential data to store
            labels: Optional labels for the secret
            
        Returns:
            Secret name
            
        Raises:
            K8sSecretAlreadyExistsError: If secret already exists
            K8sSecretError: If storage operation fails
        """
        secret_name = self._get_secret_name(tenant_id)

        # Log operation (without sensitive data)
        audit_logger.warning(
            f"K8S_SECRET_STORE: tenant_hash={tenant_id[:16]}... "
            f"secret_name={secret_name} namespace={self.namespace} "
            f"timestamp={datetime.now(UTC).isoformat()}"
        )

        if self.use_k8s_api:
            return self._store_via_api(secret_name, credentials, labels)
        else:
            return self._store_via_volume(secret_name, credentials)

    def _store_via_api(
        self,
        secret_name: str,
        credentials: CredentialData,
        labels: dict[str, str] | None = None
    ) -> str:
        """Store credentials via Kubernetes API."""
        if not self._k8s_client:
            raise K8sSecretError("Kubernetes client not initialized")

        from kubernetes.client import V1ObjectMeta, V1Secret

        # Check if secret already exists
        try:
            self._k8s_client.read_namespaced_secret(secret_name, self.namespace)
            raise K8sSecretAlreadyExistsError(
                f"Secret {secret_name} already exists in namespace {self.namespace}"
            )
        except Exception as e:
            if "AlreadyExists" in str(e) or "already exists" in str(e).lower():
                raise K8sSecretAlreadyExistsError(
                    f"Secret {secret_name} already exists in namespace {self.namespace}"
                )
            # Secret doesn't exist, continue with creation

        # Prepare secret data (base64 encoded)
        secret_data = {
            key: base64.b64encode(value.encode()).decode()
            for key, value in credentials.to_dict().items()
        }

        # Default labels
        default_labels = {
            "app": "specterdefence",
            "component": "tenant-credentials",
            "managed-by": "specterdefence-api"
        }
        if labels:
            default_labels.update(labels)

        # Create secret
        secret = V1Secret(
            api_version="v1",
            kind="Secret",
            metadata=V1ObjectMeta(
                name=secret_name,
                namespace=self.namespace,
                labels=default_labels,
                annotations={
                    "specterdefence.io/created-at": datetime.now(UTC).isoformat(),
                    "specterdefence.io/credential-type": "microsoft-graph"
                }
            ),
            type="Opaque",
            data=secret_data
        )

        try:
            self._k8s_client.create_namespaced_secret(self.namespace, secret)
            return secret_name
        except Exception as e:
            raise K8sSecretError(f"Failed to create secret: {str(e)}")

    def _store_via_volume(self, secret_name: str, credentials: CredentialData) -> str:
        """Store credentials via volume mount (for testing/development)."""
        mount_path = Path(self.VOLUME_MOUNT_PATH)

        # Create directory if it doesn't exist
        mount_path.mkdir(parents=True, exist_ok=True)

        secret_path = mount_path / secret_name

        if secret_path.exists():
            raise K8sSecretAlreadyExistsError(
                f"Secret file {secret_path} already exists"
            )

        # Write credentials as JSON (in real K8s, this would be mounted by K8s)
        # For development, we simulate the structure
        secret_data = credentials.to_dict()

        # Write each field as a separate file (matching K8s secret volume mount behavior)
        secret_path.mkdir(parents=True, exist_ok=True)
        for key, value in secret_data.items():
            (secret_path / key).write_text(value)

        return secret_name

    def get_credentials(self, tenant_id: str, user_id: str = "system") -> CredentialData:
        """Retrieve credentials from Kubernetes secret.
        
        Args:
            tenant_id: Tenant identifier
            user_id: Identifier of user/system accessing the credential
            
        Returns:
            Credential data
            
        Raises:
            K8sSecretNotFoundError: If secret not found
            K8sSecretError: If retrieval fails
        """
        secret_name = self._get_secret_name(tenant_id)

        # Log access (privacy-preserving)
        audit_logger.warning(
            f"K8S_SECRET_ACCESS: user={user_id} tenant_hash={tenant_id[:16]}... "
            f"secret_name={secret_name} namespace={self.namespace} "
            f"timestamp={datetime.now(UTC).isoformat()}"
        )

        if self.use_k8s_api:
            return self._get_via_api(secret_name)
        else:
            return self._get_via_volume(secret_name)

    def _get_via_api(self, secret_name: str) -> CredentialData:
        """Get credentials via Kubernetes API."""
        if not self._k8s_client:
            raise K8sSecretError("Kubernetes client not initialized")

        try:
            secret = self._k8s_client.read_namespaced_secret(secret_name, self.namespace)
        except Exception as e:
            if "NotFound" in str(e) or "not found" in str(e).lower():
                raise K8sSecretNotFoundError(
                    f"Secret {secret_name} not found in namespace {self.namespace}"
                )
            raise K8sSecretError(f"Failed to read secret: {str(e)}")

        # Decode base64 data
        secret_data = {
            key: base64.b64decode(value).decode()
            for key, value in secret.data.items()
        }

        return CredentialData.from_dict(secret_data)

    def _get_via_volume(self, secret_name: str) -> CredentialData:
        """Get credentials via volume mount."""
        mount_path = Path(self.VOLUME_MOUNT_PATH)
        secret_path = mount_path / secret_name

        if not secret_path.exists():
            raise K8sSecretNotFoundError(f"Secret file {secret_path} not found")

        # Read each field from separate file
        secret_data = {}
        for field in ["client_id", "client_secret", "tenant_id", "metadata"]:
            field_path = secret_path / field
            if field_path.exists():
                secret_data[field] = field_path.read_text()

        return CredentialData.from_dict(secret_data)

    def update_credentials(
        self,
        tenant_id: str,
        credentials: CredentialData,
        user_id: str = "system"
    ) -> str:
        """Update existing credentials in Kubernetes secret.
        
        Args:
            tenant_id: Tenant identifier
            credentials: New credential data
            user_id: Identifier of user/system updating the credential
            
        Returns:
            Secret name
        """
        secret_name = self._get_secret_name(tenant_id)

        # Log operation
        audit_logger.warning(
            f"K8S_SECRET_UPDATE: user={user_id} tenant_hash={tenant_id[:16]}... "
            f"secret_name={secret_name} namespace={self.namespace} "
            f"timestamp={datetime.now(UTC).isoformat()}"
        )

        if self.use_k8s_api:
            return self._update_via_api(secret_name, credentials)
        else:
            # Delete and recreate for volume-based storage
            self.delete_credentials(tenant_id, user_id)
            return self._store_via_volume(secret_name, credentials)

    def _update_via_api(self, secret_name: str, credentials: CredentialData) -> str:
        """Update credentials via Kubernetes API."""
        if not self._k8s_client:
            raise K8sSecretError("Kubernetes client not initialized")

        # Prepare secret data (base64 encoded)
        secret_data = {
            key: base64.b64encode(value.encode()).decode()
            for key, value in credentials.to_dict().items()
        }

        try:
            # Get existing secret to preserve metadata
            existing = self._k8s_client.read_namespaced_secret(secret_name, self.namespace)

            # Update annotation
            existing.metadata.annotations = existing.metadata.annotations or {}
            existing.metadata.annotations["specterdefence.io/updated-at"] = datetime.now(UTC).isoformat()
            existing.data = secret_data

            self._k8s_client.replace_namespaced_secret(secret_name, self.namespace, existing)
            return secret_name
        except Exception as e:
            if "NotFound" in str(e) or "not found" in str(e).lower():
                raise K8sSecretNotFoundError(
                    f"Secret {secret_name} not found in namespace {self.namespace}"
                )
            raise K8sSecretError(f"Failed to update secret: {str(e)}")

    def delete_credentials(self, tenant_id: str, user_id: str = "system") -> bool:
        """Delete credentials from Kubernetes secret.
        
        Args:
            tenant_id: Tenant identifier
            user_id: Identifier of user/system deleting the credential
            
        Returns:
            True if deleted, False if not found
        """
        secret_name = self._get_secret_name(tenant_id)

        # Log operation
        audit_logger.warning(
            f"K8S_SECRET_DELETE: user={user_id} tenant_hash={tenant_id[:16]}... "
            f"secret_name={secret_name} namespace={self.namespace} "
            f"timestamp={datetime.now(UTC).isoformat()}"
        )

        if self.use_k8s_api:
            return self._delete_via_api(secret_name)
        else:
            return self._delete_via_volume(secret_name)

    def _delete_via_api(self, secret_name: str) -> bool:
        """Delete credentials via Kubernetes API."""
        if not self._k8s_client:
            raise K8sSecretError("Kubernetes client not initialized")

        try:
            self._k8s_client.delete_namespaced_secret(secret_name, self.namespace)
            return True
        except Exception as e:
            if "NotFound" in str(e) or "not found" in str(e).lower():
                return False
            raise K8sSecretError(f"Failed to delete secret: {str(e)}")

    def _delete_via_volume(self, secret_name: str) -> bool:
        """Delete credentials via volume mount."""
        mount_path = Path(self.VOLUME_MOUNT_PATH)
        secret_path = mount_path / secret_name

        if not secret_path.exists():
            return False

        # Remove directory and all files
        import shutil
        shutil.rmtree(secret_path)
        return True

    def list_secrets(self) -> list[dict[str, Any]]:
        """List all tenant credential secrets.
        
        Returns:
            List of secret metadata (without credential values)
        """
        if self.use_k8s_api:
            return self._list_via_api()
        else:
            return self._list_via_volume()

    def _list_via_api(self) -> list[dict[str, Any]]:
        """List secrets via Kubernetes API."""
        if not self._k8s_client:
            raise K8sSecretError("Kubernetes client not initialized")

        try:
            secrets = self._k8s_client.list_namespaced_secret(
                self.namespace,
                label_selector="component=tenant-credentials"
            )

            result = []
            for secret in secrets.items:
                result.append({
                    "name": secret.metadata.name,
                    "namespace": secret.metadata.namespace,
                    "created_at": secret.metadata.annotations.get(
                        "specterdefence.io/created-at"
                    ) if secret.metadata.annotations else None,
                    "labels": secret.metadata.labels,
                    "keys": list(secret.data.keys()) if secret.data else []
                })
            return result
        except Exception as e:
            raise K8sSecretError(f"Failed to list secrets: {str(e)}")

    def _list_via_volume(self) -> list[dict[str, Any]]:
        """List secrets via volume mount."""
        mount_path = Path(self.VOLUME_MOUNT_PATH)

        if not mount_path.exists():
            return []

        result = []
        for secret_dir in mount_path.iterdir():
            if secret_dir.is_dir() and secret_dir.name.startswith(self.SECRET_PREFIX):
                # Get keys (files) in the secret directory
                keys = [f.name for f in secret_dir.iterdir() if f.is_file()]
                result.append({
                    "name": secret_dir.name,
                    "namespace": "local",
                    "created_at": None,
                    "labels": {},
                    "keys": keys
                })
        return result

    def health_check(self) -> dict[str, Any]:
        """Check storage backend health.
        
        Returns:
            Health check result
        """
        result = {
            "backend": "k8s-secrets",
            "in_cluster": self._in_cluster,
            "use_k8s_api": self.use_k8s_api,
            "namespace": self.namespace,
            "status": "unknown",
            "error": None
        }

        try:
            if self.use_k8s_api:
                if not self._k8s_client:
                    result["status"] = "error"
                    result["error"] = "Kubernetes client not initialized"
                else:
                    # Try to list secrets to verify connectivity
                    self._k8s_client.list_namespaced_secret(
                        self.namespace,
                        limit=1
                    )
                    result["status"] = "healthy"
            else:
                # Check if volume mount exists
                mount_path = Path(self.VOLUME_MOUNT_PATH)
                if mount_path.exists():
                    result["status"] = "healthy"
                else:
                    result["status"] = "warning"
                    result["error"] = f"Volume mount path {mount_path} does not exist"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result


# Global K8s secrets storage instance (lazy initialization)
_k8s_storage_instance: K8sSecretsStorage | None = None


def get_k8s_storage() -> K8sSecretsStorage:
    """Get or create K8s secrets storage instance."""
    global _k8s_storage_instance
    if _k8s_storage_instance is None:
        _k8s_storage_instance = K8sSecretsStorage()
    return _k8s_storage_instance
