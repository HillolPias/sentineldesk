"""API entrypoint for benchmarks: the real app, with Stripe faked so signups stay local."""

import asyncio
import sys

import uvicorn

import app.routers.auth as auth_router


async def _fake_create_customer(tenant_name: str, email: str) -> str:
    return "cus_benchmark"


auth_router.create_customer = _fake_create_customer


async def _serve() -> None:
    config = uvicorn.Config(
        "main:app", host="0.0.0.0", port=8000, log_level="warning", access_log=False
    )
    await uvicorn.Server(config).serve()


def main() -> None:
    if sys.platform == "win32":
        asyncio.run(_serve(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(_serve())


if __name__ == "__main__":
    main()
