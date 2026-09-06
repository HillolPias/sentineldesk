import asyncio
import sys
import uvicorn


async def _serve():
    config = uvicorn.Config("main:app", host="127.0.0.1", log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


def main():
    if sys.platform == "win32":
        asyncio.run(_serve(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(_serve())


if __name__ == "__main__":
    main()
