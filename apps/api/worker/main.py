import asyncio
import logging
import sys

from arq.worker import run_worker
from worker.settings import get_redis_settings
from worker.tasks.triage_job import triage_ticket

logging.basicConfig(level=logging.INFO)


class WorkerSettings:
    functions = [triage_ticket]
    redis_settings = get_redis_settings()


def main():
    if sys.platform == "win32":
        loop = asyncio.SelectorEventLoop()
        asyncio.set_event_loop(loop)

    run_worker(WorkerSettings)


if __name__ == "__main__":
    main()
