"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """AegisCloud configuration — loaded from .env file."""
    
    # App
    app_name: str = "AegisCloud DevSecOps Sentinel"
    app_version: str = "0.1.0"
    debug: bool = False
    app_secret_key: str  # REQUIRED — must be set via APP_SECRET_KEY env var
    
    # Auth0
    auth0_domain: str = ""
    auth0_client_id: str = ""
    auth0_client_secret: str = ""
    auth0_audience: str = "https://api.aegiscloud.dev"
    auth0_m2m_client_id: str = ""
    auth0_m2m_client_secret: str = ""
    auth0_user_id: str = ""
    # Token Vault Custom API Client (resource server) — required for RFC 8693 exchange
    auth0_token_vault_client_id: str = ""
    auth0_token_vault_client_secret: str = ""
    
    # Google Gemini (Pivoted from OpenAI)
    google_api_key: str = ""
    
    # Database
    database_url: str = "sqlite:///./aegiscloud.db"
    
    # URLs
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    
    # Feature Flags
    aws_mock_mode: bool = True
    
    model_config = {
        "env_file": "../.env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
