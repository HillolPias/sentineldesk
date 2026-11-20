"""Worker entrypoint for benchmarks: the real Arq worker and job, with the LLM graph faked."""

import asyncio
import os
from contextlib import asynccontextmanager

import worker.tasks.triage_job as triage_job
from worker.main import main

FAKE_LLM_SECONDS = float(os.environ.get("FAKE_LLM_SECONDS", "10"))


class _FakeGraph:
    async def ainvoke(self, state, config=None):
        await asyncio.sleep(
            FAKE_LLM_SECONDS
        )  # stands in for classify + RAG + draft + guardrail
        return {
            "category": "account",
            "urgency": "medium",
            "draft_response": "benchmark draft",
        }


@asynccontextmanager
async def _fake_checkpointer():
    yield object()


def _fake_compile_graph(checkpointer):
    return _FakeGraph()


def _fake_langfuse_handler():
    return None


triage_job.get_checkpointer = _fake_checkpointer
triage_job.compile_graph = _fake_compile_graph
triage_job.get_langfuse_handler = _fake_langfuse_handler

if __name__ == "__main__":
    main()
