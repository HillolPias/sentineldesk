from worker.settings import get_redis_settings
from worker.tasks.triage_job import triage_ticket


class WorkerSettings:
    functions = [triage_ticket]
    redis_settings = get_redis_settings()
