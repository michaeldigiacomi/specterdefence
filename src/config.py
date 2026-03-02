"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

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
    
    # Security
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Database (for future use)
    DATABASE_URL: str = "sqlite:///./specterdefence.db"
    
    # Microsoft Graph
    MS_GRAPH_API_URL: str = "https://graph.microsoft.com/v1.0"
    MS_LOGIN_URL: str = "https://login.microsoftonline.com"
    
    # Authentication
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str = "$2b$12$qaI.IhS84lIGdfXRFU8aZOhLqJqsZbhJt1UFx8rWSjzlHynm53.kK"  # Default: "admin123"
    JWT_SECRET_KEY: str = "change-me-in-production-specterdefence-secret-key"
    JWT_EXPIRATION_HOURS: int = 24

settings = Settings()
