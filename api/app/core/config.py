"""Application configuration."""
import sys
from urllib.parse import urlparse
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    JWT_ISSUER: str | None = None
    JWT_AUDIENCE: str | None = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Environment configuration
    ENVIRONMENT: str = "development"  # "development" or "production"

    # CORS configuration - comma-separated origins
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174"

    model_config = SettingsConfigDict(env_file=".env")

    def get_cors_origins(self) -> list[str]:
        """Parse CORS_ORIGINS into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def validate_production_settings(self) -> None:
        """Validate settings for production environment.

        Raises SystemExit if critical security settings are misconfigured.
        """
        env = self.ENVIRONMENT.strip().lower()
        if env in {"production", "prod"}:
            secret = self.SECRET_KEY.strip()
            if not secret or secret == "dev-secret-key-change-in-production":
                print("FATAL: SECRET_KEY must be changed in production!", file=sys.stderr)
                print("Set a secure random SECRET_KEY environment variable.", file=sys.stderr)
                sys.exit(1)

            if len(secret) < 32:
                print("FATAL: SECRET_KEY must be at least 32 characters in production!", file=sys.stderr)
                print("Set a secure random SECRET_KEY environment variable.", file=sys.stderr)
                sys.exit(1)

            db_url = self.DATABASE_URL.strip()
            default_db_url = "postgresql://mrm_user:mrm_pass@db:5432/mrm_db"
            if not db_url or db_url == default_db_url:
                print("FATAL: DATABASE_URL must be set to a non-default value in production!", file=sys.stderr)
                print("Set DATABASE_URL to a production database connection string.", file=sys.stderr)
                sys.exit(1)

            parsed_db_url = urlparse(db_url)
            if parsed_db_url.username == "mrm_user" and parsed_db_url.password == "mrm_pass":
                print("FATAL: DATABASE_URL must not use default dev credentials in production!", file=sys.stderr)
                print("Set DATABASE_URL with production credentials.", file=sys.stderr)
                sys.exit(1)

            if parsed_db_url.hostname in {"localhost", "127.0.0.1"}:
                print(
                    "WARNING: DATABASE_URL points to localhost/127.0.0.1 in production. "
                    "Confirm this is intentional (sidecar/proxy pattern).",
                    file=sys.stderr,
                )

            if not self.JWT_ISSUER or not self.JWT_ISSUER.strip() or not self.JWT_AUDIENCE or not self.JWT_AUDIENCE.strip():
                print("FATAL: JWT_ISSUER and JWT_AUDIENCE must be set in production!", file=sys.stderr)
                print("Set JWT_ISSUER and JWT_AUDIENCE environment variables.", file=sys.stderr)
                sys.exit(1)
        elif env != "development":
            print(f"FATAL: Unsupported ENVIRONMENT value: {self.ENVIRONMENT!r}", file=sys.stderr)
            print("Use ENVIRONMENT=development or ENVIRONMENT=production.", file=sys.stderr)
            sys.exit(1)


settings = Settings()
# Validate on startup
settings.validate_production_settings()
