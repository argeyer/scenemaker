"""Application settings loaded from environment variables or a .env file."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SCENEMAKER_", extra="ignore")

    environment: Literal["dev", "test", "prod"] = "dev"
    api_base_url: str = "http://localhost:8000"

    database_url: str = "sqlite:///./scenemaker.db"

    jwt_secret: str = "change-me-in-production-use-32-plus-random-bytes"
    jwt_expire_minutes: int = 60 * 24 * 30

    queue_backend: Literal["memory", "redis"] = "memory"
    redis_url: str = "redis://localhost:6379/0"
    queue_name: str = "scenemaker:render"
    job_max_attempts: int = 3

    storage_backend: Literal["local", "s3"] = "local"
    storage_local_dir: str = "./data"
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_endpoint_url: str | None = None
    download_url_ttl_seconds: int = 3600

    ai_backend: Literal["fake", "huggingface"] = "fake"
    hf_api_token: str = ""
    hf_face_swap_endpoint: str = ""
    hf_avatar_endpoint: str = ""
    hf_timeout_seconds: float = 600.0

    max_selfie_bytes: int = 10 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
