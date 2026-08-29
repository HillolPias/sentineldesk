from functools import lru_cache
from re import S
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
