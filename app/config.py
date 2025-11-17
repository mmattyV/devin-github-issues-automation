"""
Configuration management for the Devin GitHub Issues Automation system.
Loads and validates environment variables using Pydantic Settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Devin API Configuration
    devin_api_key: str = Field(..., description="Devin API authentication key")
    devin_api_url: str = Field(
        default="https://api.devin.ai/v1",
        description="Devin API base URL"
    )
    
    # GitHub API Configuration
    github_token: str = Field(..., description="GitHub Personal Access Token")
    
    # Orchestrator Configuration
    orchestrator_host: str = Field(default="0.0.0.0", description="Orchestrator host")
    orchestrator_port: int = Field(default=8000, description="Orchestrator port")
    database_url: str = Field(
        default="sqlite:///./devin_orchestrator.db",
        description="Database connection URL"
    )
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Polling Configuration
    devin_poll_interval: int = Field(
        default=15,
        description="Initial polling interval in seconds"
    )
    devin_poll_timeout: int = Field(
        default=1800,
        description="Maximum polling timeout in seconds (30 minutes)"
    )
    devin_poll_max_interval: int = Field(
        default=30,
        description="Maximum polling interval in seconds"
    )
    
    # GitHub Rate Limiting
    github_rate_limit_buffer: int = Field(
        default=100,
        description="Number of API calls to keep in reserve"
    )
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the standard levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v_upper
    
    @field_validator("devin_poll_interval", "devin_poll_max_interval")
    @classmethod
    def validate_positive(cls, v: int) -> int:
        """Validate that polling intervals are positive."""
        if v <= 0:
            raise ValueError("Polling interval must be positive")
        return v
    
    @field_validator("devin_poll_timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout is reasonable (at least 60 seconds)."""
        if v < 60:
            raise ValueError("Timeout must be at least 60 seconds")
        return v


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance.
    Creates a new instance if one doesn't exist.
    
    Returns:
        Settings: The application settings
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """
    Force reload settings from environment.
    Useful for testing or configuration changes.
    
    Returns:
        Settings: Freshly loaded settings
    """
    global _settings
    _settings = Settings()
    return _settings
