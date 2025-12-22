"""Application configuration."""
import sys
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://mrm_user:mrm_pass@db:5432/mrm_db"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Environment configuration
    ENVIRONMENT: str = "development"  # "development" or "production"

    # CORS configuration - comma-separated origins
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174"

    # UAT tools - MUST be explicitly enabled, disabled by default
    ENABLE_UAT_TOOLS: bool = False

    class Config:
        env_file = ".env"

    def get_cors_origins(self) -> list[str]:
        """Parse CORS_ORIGINS into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def validate_production_settings(self) -> None:
        """Validate settings for production environment.

        Raises SystemExit if critical security settings are misconfigured.
        """
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == "dev-secret-key-change-in-production":
                print("FATAL: SECRET_KEY must be changed in production!", file=sys.stderr)
                print("Set a secure random SECRET_KEY environment variable.", file=sys.stderr)
                sys.exit(1)

            if self.ENABLE_UAT_TOOLS:
                print("WARNING: UAT tools are enabled in production!", file=sys.stderr)
                print("This allows data destruction endpoints. Set ENABLE_UAT_TOOLS=false", file=sys.stderr)


settings = Settings()
# Validate on startup
settings.validate_production_settings()
