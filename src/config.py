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

settings = Settings()
