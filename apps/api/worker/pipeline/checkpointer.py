from contextlib import asynccontextmanager
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def get_checkpointer():
    async with AsyncPostgresSaver.from_conn_string(
        settings.database_url_psycopg
    ) as checkpointer:
        yield checkpointer
