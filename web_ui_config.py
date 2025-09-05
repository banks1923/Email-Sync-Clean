"""Web UI Configuration - Centralized settings for expansion."""

from pydantic import BaseSettings, Field
from typing import Optional

class WebUISettings(BaseSettings):
    """Configuration for Web UI with future expansion in mind."""
    
    # Server settings
    host: str = Field(default="127.0.0.1", env="WEB_UI_HOST")
    port: int = Field(default=5000, env="WEB_UI_PORT")
    debug: bool = Field(default=True, env="WEB_UI_DEBUG")
    
    # API settings
    api_version: str = Field(default="v1", env="API_VERSION")
    api_timeout: int = Field(default=30, env="API_TIMEOUT")
    max_results: int = Field(default=200, env="MAX_RESULTS")
    
    # Search defaults
    default_search_mode: str = Field(default="hybrid", env="DEFAULT_SEARCH_MODE")
    default_limit: int = Field(default=10, env="DEFAULT_LIMIT")
    
    # Feature flags
    enable_caching: bool = Field(default=False, env="ENABLE_CACHING")
    enable_pagination: bool = Field(default=True, env="ENABLE_PAGINATION")
    enable_export: bool = Field(default=False, env="ENABLE_EXPORT")
    enable_analytics: bool = Field(default=False, env="ENABLE_ANALYTICS")
    
    # UI customization
    theme: str = Field(default="light", env="UI_THEME")
    brand_name: str = Field(default="Litigator Search", env="BRAND_NAME")
    
    # Security
    enable_auth: bool = Field(default=False, env="ENABLE_AUTH")
    api_key: Optional[str] = Field(default=None, env="API_KEY")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5000"],
        env="CORS_ORIGINS"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Singleton instance
web_config = WebUISettings()