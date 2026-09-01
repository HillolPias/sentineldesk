from arq.connections import RedisSettings
from app.core.config import get_settings

settings = get_settings()


# Arq wants host/port broken out, not a full connection URL
def get_redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(settings.redis_url)
