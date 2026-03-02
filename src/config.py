"""Application configuration."""

import secrets

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # App
    APP_NAME: str = "SpecterDefence"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security - SECURE BY DEFAULT
    # Generate secure defaults if not provided, but validate in production
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_hex(32),
        min_length=32,
        description="Application secret key - auto-generated if not provided"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS - Restrictive by default
    CORS_ORIGINS: list[str] = Field(
        default_factory=list,
        description="Allowed CORS origins - empty means same-origin only"
    )

    # Database (for future use)
    DATABASE_URL: str = "sqlite:///./specterdefence.db"

    # Microsoft Graph
    MS_GRAPH_API_URL: str = "https://graph.microsoft.com/v1.0"
    MS_LOGIN_URL: str = "https://login.microsoftonline.com"

    # Authentication - NO DEFAULT PASSWORD
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str = Field(
        default="",
        description="bcrypt hash of admin password - MUST be set in production"
    )
    JWT_SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_hex(32),
        min_length=32,
        description="JWT signing key - auto-generated if not provided"
    )
    JWT_EXPIRATION_HOURS: int = 24

    # Encryption
    ENCRYPTION_SALT: str = Field(
        default="",
        description="Salt for encryption - should be set in production"
    )

    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate that SECRET_KEY is not using default/weak values."""
        import os
        if os.getenv('TESTING') == 'true' or os.getenv('PYTEST_CURRENT_TEST'):
            return v
        weak_values = [
            "change-me-in-production",
            "your-secret-key-here",
            "",
        ]
        if v in weak_values:
            raise ValueError(
                "SECRET_KEY is using a weak/default value. "
                "Generate a secure key with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    @field_validator('JWT_SECRET_KEY')
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        """Validate that JWT_SECRET_KEY is not using default/weak values."""
        import os
        if os.getenv('TESTING') == 'true' or os.getenv('PYTEST_CURRENT_TEST'):
            return v
        weak_values = [
            "change-me-in-production-specterdefence-secret-key",
            "your-jwt-secret-key",
            "",
        ]
        if v in weak_values:
            raise ValueError(
                "JWT_SECRET_KEY is using a weak/default value. "
                "Generate a secure key with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        return v

    @field_validator('ADMIN_PASSWORD_HASH')
    @classmethod
    def validate_admin_password_hash(cls, v: str) -> str:
        """Validate that admin password hash is not using default values."""
        # Skip validation in test mode
        import os
        if os.getenv('TESTING') == 'true' or os.getenv('PYTEST_CURRENT_TEST'):
            return v

        # This is the hash for "admin123" - commonly attacked
        default_hashes = [
            "$2b$12$qaI.IhS84lIGdfXRFU8aZOhLqJqsZbhJt1UFx8rWSjzlHynm53.kK",
        ]
        if v in default_hashes:
            raise ValueError(
                "ADMIN_PASSWORD_HASH is using a default/weak value. "
                "Generate a new hash with: python -c \"from src.api.auth_local import get_password_hash; print(get_password_hash('your-password'))\""
            )
        return v

    @field_validator('CORS_ORIGINS')
    @classmethod
    def validate_cors_origins(cls, v: list[str]) -> list[str]:
        """Validate CORS origins."""
        import os
        if os.getenv('TESTING') == 'true' or os.getenv('PYTEST_CURRENT_TEST'):
            return v
        if "*" in v:
            raise ValueError(
                'CORS_ORIGINS cannot contain "*" (allow all origins). '
                'Specify explicit origins for security.'
            )
        return v

settings = Settings()
