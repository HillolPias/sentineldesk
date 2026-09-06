from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from app.core.config import get_settings

settings = get_settings()

# Configure the singleton Langfuse client once, at import time.
# CallbackHandler() reads from this singleton — it takes no constructor args in v3.
Langfuse(
    public_key=settings.langfuse_public_key,
    secret_key=settings.langfuse_secret_key,
    host=settings.langfuse_host,
)


def get_langfuse_handler() -> CallbackHandler:
    return CallbackHandler()
