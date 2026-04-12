from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = "InsightX AI"
    version: str = "1.0.0"
    environment: str = Field(default="dev")

    # DuckDB — single source of truth for everything
    duckdb_path: str = Field(default="data/insightx.duckdb")
    uploads_dir: str = Field(default="data/uploads")

    # JWT auth
    secret_key: str = Field(default="insightx-dev-secret-change-in-prod")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=1440)  # 24h

    # CORS — set to your frontend domain(s) in production
    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://127.0.0.1:3000"])

    # Anthropic
    anthropic_api_key: str = Field(default="")
    claude_model: str = Field(default="claude-sonnet-4-6")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
