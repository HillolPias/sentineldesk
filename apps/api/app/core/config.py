from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str
    openai_api_key: str
    langfuse_public_key: str
    langfuse_secret_key: str
    langfuse_host: str
    jwt_secret: str
    stripe_secret_key: str
    cors_origins: str = "http://localhost:3000"

    @property
    def database_url_psycopg(self) -> str:
        # LangGraph's checkpointer uses psycopg, which wants a plain
        # postgresql:// DSN — strip SQLAlchemy's +asyncpg driver suffix.
        url = self.database_url.replace("postgresql+asyncpg://", "postgresql://")

        # asyncpg spells it ssl=require, psycopg spells it sslmode=require
        return url.replace("ssl=require", "sslmode=require")


@lru_cache
def get_settings() -> Settings:
    return Settings()
