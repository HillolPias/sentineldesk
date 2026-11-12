"""
Run once (and again after any langgraph-checkpoint-postgres upgrade) to create/
update the checkpointer's own tables. Not an alembic migration - LangGraph
owns this schema.
"""

import asyncio
import sys

from worker.pipeline.checkpointer import get_checkpointer


async def setup():
    async with get_checkpointer() as checkpointer:
        await checkpointer.setup()
    print("Checkpointer tables ready.")


def main():
    kwargs = (
        {"loop_factory": asyncio.SelectorEventLoop} if sys.platform == "win32" else {}
    )
    asyncio.run(setup(), **kwargs)


if __name__ == "__main__":
    main()
