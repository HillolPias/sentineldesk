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

    @property
    def database_url_psycopg(self) -> str:
        # LangGraph's checkpointer uses psycopg, which wants a plain
        # postgresql:// DSN — strip SQLAlchemy's +asyncpg driver suffix.
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")


@lru_cache
def get_settings() -> Settings:
    return Settings()
