from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = Field(..., alias="DATABASE_URL")
    TEST_DATABASE_URL: str | None = Field(None, alias="TEST_DATABASE_URL")

    # Redis
    REDIS_URL: str = Field(..., alias="REDIS_URL")

    # JWT
    JWT_SECRET: str = Field(..., alias="JWT_SECRET")

    # Service URLs
    ERP_BASE_URL: str = Field(..., alias="ERP_BASE_URL")
    FORENSICS_URL: str = Field(..., alias="FORENSICS_URL")
    LITELLM_URL: str = Field(..., alias="LITELLM_URL")

    # Queue
    QUEUE_PREFIX: str = Field(default="dev-", alias="QUEUE_PREFIX")

    # Storage
    STORAGE_DIR: str = Field(..., alias="STORAGE_DIR")

    # LLM
    LLM_MODE: str = Field(default="stub", alias="LLM_MODE")

    # Domain
    DOMAIN: str = Field(..., alias="DOMAIN")

    # API
    API_V1_PREFIX: str = "/v1"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )


# Global settings instance
settings = Settings()  # type: ignore[call-arg]
