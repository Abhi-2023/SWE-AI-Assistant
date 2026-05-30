from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache

class Settings(BaseSettings):

    # ── Auth ──────────────────────────────────────────
    anthropic_api_key: str
    secret_key: str
    access_token_expire_minutes: int = 1440
    algorithm: str = "HS256"

    # ── Database ──────────────────────────────────────
    database_url: str

    # ── Redis ─────────────────────────────────────────
    redis_url: str

    # ── Qdrant ────────────────────────────────────────
    qdrant_url: str
    qdrant_collection: str = "repo_path"

    # ── GitHub ────────────────────────────────────────
    github_token: str
    
    github_webhook_secret: str = ""
    
    cohere_api_key: str

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()