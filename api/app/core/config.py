"""Application configuration."""
import sys
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://mrm_user:mrm_pass@db:5432/mrm_db"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    JWT_ISSUER: str | None = None
    JWT_AUDIENCE: str | None = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Environment configuration
    ENVIRONMENT: str = "development"  # "development" or "production"

    # CORS configuration - comma-separated origins
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174"

    # UAT tools - MUST be explicitly enabled, disabled by default
    ENABLE_UAT_TOOLS: bool = False
    # Production break-glass for UAT tools (must be explicit + audited)
    ALLOW_UAT_TOOLS_IN_PROD: bool = False
    UAT_TOOLS_BREAK_GLASS_TICKET: str | None = None

    class Config:
        env_file = ".env"

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

            if not self.JWT_ISSUER or not self.JWT_ISSUER.strip() or not self.JWT_AUDIENCE or not self.JWT_AUDIENCE.strip():
                print("FATAL: JWT_ISSUER and JWT_AUDIENCE must be set in production!", file=sys.stderr)
                print("Set JWT_ISSUER and JWT_AUDIENCE environment variables.", file=sys.stderr)
                sys.exit(1)

            if self.ENABLE_UAT_TOOLS:
                if not self.ALLOW_UAT_TOOLS_IN_PROD or not self.UAT_TOOLS_BREAK_GLASS_TICKET or not self.UAT_TOOLS_BREAK_GLASS_TICKET.strip():
                    print("FATAL: UAT tools cannot be enabled in production without break-glass approval!", file=sys.stderr)
                    print("Set ALLOW_UAT_TOOLS_IN_PROD=true and UAT_TOOLS_BREAK_GLASS_TICKET=<ticket>", file=sys.stderr)
                    sys.exit(1)
                print(
                    f"WARNING: UAT tools enabled in production under break-glass {self.UAT_TOOLS_BREAK_GLASS_TICKET}.",
                    file=sys.stderr,
                )
        elif env != "development":
            print(f"FATAL: Unsupported ENVIRONMENT value: {self.ENVIRONMENT!r}", file=sys.stderr)
            print("Use ENVIRONMENT=development or ENVIRONMENT=production.", file=sys.stderr)
            sys.exit(1)


settings = Settings()
# Validate on startup
settings.validate_production_settings()
