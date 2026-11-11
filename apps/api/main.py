from contextlib import asynccontextmanager

from arq import create_pool
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import auth, billing, tickets
from worker.settings import get_redis_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = await create_pool(get_redis_settings())
    yield
    await app.state.redis.close()


app = FastAPI(title="SentinelDesk API", lifespan=lifespan)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(billing.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
