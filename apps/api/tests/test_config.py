from app.core.config import Settings


def _settings(**overrides):
    base = dict(
        database_url="postgresql+asyncpg://u:p@h/db",
        redis_url="redis://x",
        openai_api_key="x",
        langfuse_public_key="x",
        langfuse_secret_key="x",
        langfuse_host="x",
        jwt_secret="x",
        stripe_secret_key="x",
    )
    return Settings(**{**base, **overrides})


def test_psycopg_url_translates_driver_and_ssl_param():
    s = _settings(database_url="postgresql+asyncpg://u:p@h/db?ssl=require")
    assert s.database_url_psycopg == "postgresql://u:p@h/db?sslmode=require"


def test_psycopg_url_without_ssl_is_just_the_driver_swap():
    assert _settings().database_url_psycopg == "postgresql://u:p@h/db"


def test_cors_default_to_local_frontend():
    assert _settings().cors_origins == "http://localhost:3000"
