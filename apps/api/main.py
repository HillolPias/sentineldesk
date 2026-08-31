from fastapi import FastAPI
from app.routers import auth, tickets

app = FastAPI(title="SentinelDesk API")

app.include_router(auth.router)
app.include_router(tickets.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
