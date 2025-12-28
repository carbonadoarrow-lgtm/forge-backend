"""
Configuration settings for the Forge Backend application.
"""

import os
import json
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, PrivateAttr, ConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    # API Settings
    APP_NAME: str = "Forge Backend"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    DEBUG: bool = False
    
    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False
    
    # CORS Settings - stored as a private attribute
    _cors_origins: Optional[List[str]] = PrivateAttr(default=None)
    
    # Data Storage
    DATA_DIR: str = "data"
    FORGE_BACKEND_MODE: str = "file"  # "file" or "database"
    
    # Database
    DATABASE_URL: str = Field(default="sqlite:///./forge.db")
    FORGE_DB_PATH: Optional[str] = None  # Override database path if specified
    DB_TYPE: str = "sqlite"  # "sqlite" or "postgresql"

    # Build/provenance (optional; safe defaults)
    BUILD_SHA: str = "unknown"
    BUILD_TIME_UTC: str = "unknown"

    # Background worker gates (stabilization-only)
    # Default OFF. Must be explicitly enabled.
    AUTONOMY_V2_WORKER_ENABLED: bool = False
    # Uvicorn/Gunicorn can spawn multiple processes. Only one should run the background worker.
    # If set, worker will run only in the process where os.getpid() == AUTONOMY_V2_WORKER_PID.
    AUTONOMY_V2_WORKER_PID: int = 0
    # Interval between background ticks (seconds)
    AUTONOMY_V2_WORKER_TICK_INTERVAL_SECONDS: int = 3

    # Which lane/env the background worker should service (stabilization default)
    AUTONOMY_V2_WORKER_ENV: str = "local"
    AUTONOMY_V2_WORKER_LANE: str = "default"

    # Admin auth (stabilization-only): required for manual tick endpoints
    ADMIN_TOKEN: str = ""
    
    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    def __init__(self, **kwargs):
        # First, let Pydantic do its normal initialization
        super().__init__(**kwargs)

        # Override DATABASE_URL if FORGE_DB_PATH is specified
        if self.FORGE_DB_PATH:
            self.DATABASE_URL = f"sqlite:///{self.FORGE_DB_PATH}"

        # Validate SECRET_KEY was changed in production
        self._validate_secret_key()

        # Parse CORS origins from environment variables
        self._parse_cors_origins()

    def _validate_secret_key(self):
        """Ensure SECRET_KEY was changed from default value."""
        if self.SECRET_KEY == "your-secret-key-here-change-in-production":
            import os
            if os.getenv("FORGE_ENV", "development") == "production":
                raise ValueError(
                    "SECRET_KEY must be changed in production! "
                    "Set SECRET_KEY environment variable to a secure random value."
                )
            # In development, warn but don't fail
            print("WARNING: Using default SECRET_KEY. This is insecure for production!")
    
    def _parse_cors_origins(self):
        """Parse CORS origins from environment variables."""
        # Check for FORGE_CORS_ORIGINS first (takes precedence)
        forge_cors = os.getenv('FORGE_CORS_ORIGINS')
        if forge_cors is not None:
            self._cors_origins = self._parse_cors_value(forge_cors)
            return
        
        # Check for CORS_ORIGINS
        cors_env = os.getenv('CORS_ORIGINS')
        if cors_env is not None:
            self._cors_origins = self._parse_cors_value(cors_env)
            return
        
        # Default to ["*"]
        self._cors_origins = ["*"]
    
    def _parse_cors_value(self, value: str) -> List[str]:
        """Parse CORS value from environment variable.
        
        Supports:
        1. JSON format: '["http://localhost:3000", "https://example.com"]'
        2. Comma-separated string: 'http://localhost:3000,https://example.com'
        3. Empty string: defaults to ["*"]
        """
        if not value or value.strip() == "":
            return ["*"]
        
        # Try to parse as JSON first
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
            else:
                # If it's not a list, wrap it in a list
                return [str(parsed)]
        except json.JSONDecodeError:
            # If JSON parsing fails, try as comma-separated string
            return [origin.strip() for origin in value.split(',')]
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Get CORS origins."""
        if self._cors_origins is None:
            self._parse_cors_origins()
        return self._cors_origins
    
    @CORS_ORIGINS.setter
    def CORS_ORIGINS(self, value: List[str]):
        """Set CORS origins."""
        self._cors_origins = value

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # Allow extra env vars without raising validation errors
    )


# Create global settings instance
settings = Settings()
