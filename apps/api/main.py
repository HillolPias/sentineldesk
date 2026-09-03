from contextlib import asynccontextmanager
from fastapi import FastAPI
from arq import create_pool
from worker.settings import get_redis_settings
from app.routers import auth, tickets


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = await create_pool(get_redis_settings())
    yield
    await app.state.redis.close()


app = FastAPI(title="SentinelDesk API", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(tickets.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
