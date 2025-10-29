"""
Core configuration module using Pydantic Settings.

This module defines all application settings loaded from environment variables.
All configuration must go through this Settings class - NO hardcoded values.
"""

from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings are loaded from .env file or environment variables.
    Settings are validated using Pydantic with type hints.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Application Settings
    # -------------------------------------------------------------------------
    app_name: str = Field(default="Emerald Finance Platform")
    version: str = Field(default="0.1.0")
    environment: Literal["development", "staging", "production"] = Field(default="development")
    debug: bool = Field(default=False)

    # -------------------------------------------------------------------------
    # Server Configuration
    # -------------------------------------------------------------------------
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    reload: bool = Field(default=False)

    # -------------------------------------------------------------------------
    # Security Settings
    # -------------------------------------------------------------------------
    secret_key: str = Field(
        ...,
        min_length=32,
        description="Secret key for JWT signing. Must be at least 32 characters."
    )

    # JWT Token Configuration
    access_token_expire_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=30)

    # Argon2id Password Hashing Configuration
    argon2_time_cost: int = Field(default=2, ge=1, le=10)
    argon2_memory_cost: int = Field(default=65536, ge=8192)  # 64 MB
    argon2_parallelism: int = Field(default=4, ge=1, le=16)

    # -------------------------------------------------------------------------
    # Database Configuration
    # -------------------------------------------------------------------------
    database_url: PostgresDsn = Field(
        ...,
        description="PostgreSQL connection string with asyncpg driver"
    )

    # Connection Pool Settings
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_max_overflow: int = Field(default=10, ge=0, le=100)
    db_pool_recycle: int = Field(default=3600, ge=300)  # Seconds
    db_pool_pre_ping: bool = Field(default=True)

    # -------------------------------------------------------------------------
    # Redis Configuration
    # -------------------------------------------------------------------------
    redis_url: RedisDsn = Field(
        ...,
        description="Redis connection string for rate limiting and caching"
    )
    redis_max_connections: int = Field(default=10, ge=1, le=100)

    # -------------------------------------------------------------------------
    # CORS Settings
    # -------------------------------------------------------------------------
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Comma-separated list of allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(default=True)

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, v: str) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_login: str = Field(default="5/15minute")
    rate_limit_register: str = Field(default="3/hour")
    rate_limit_password_change: str = Field(default="3/hour")
    rate_limit_token_refresh: str = Field(default="10/hour")
    rate_limit_api: str = Field(default="100/minute")

    # -------------------------------------------------------------------------
    # Logging Configuration
    # -------------------------------------------------------------------------
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )
    log_format: Literal["json", "console"] = Field(default="console")
    log_file_enabled: bool = Field(default=True)
    log_file_path: str = Field(default="logs/app.log")
    log_file_max_bytes: int = Field(default=10485760)  # 10 MB
    log_file_backup_count: int = Field(default=5)

    # -------------------------------------------------------------------------
    # Audit Logging
    # -------------------------------------------------------------------------
    audit_log_enabled: bool = Field(default=True)
    audit_log_retention_days: int = Field(default=2555)  # 7 years

    # -------------------------------------------------------------------------
    # Testing Configuration
    # -------------------------------------------------------------------------
    test_database_url: PostgresDsn | None = Field(
        default=None,
        description="Separate database for testing"
    )

    # -------------------------------------------------------------------------
    # Computed Properties
    # -------------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.environment == "staging"

    @property
    def cors_origins_list(self) -> list[str]:
        """Get parsed CORS origins as list."""
        if isinstance(self.cors_origins, list):
            return self.cors_origins
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def database_url_str(self) -> str:
        """Get database URL as string."""
        return str(self.database_url)

    @property
    def redis_url_str(self) -> str:
        """Get Redis URL as string."""
        return str(self.redis_url)


# Singleton instance of settings
# Import this instance throughout the application
settings = Settings()
