import uuid
from contextlib import asynccontextmanager

import pytest


@pytest.fixture
def worker_graph(monkeypatch, fake_graph):
    import worker.tasks.triage_job as triage_job

    @asynccontextmanager
    async def fake_checkpointer():
        yield object()

    monkeypatch.setattr(triage_job, "get_checkpointer", fake_checkpointer)
    monkeypatch.setattr(triage_job, "compile_graph", lambda checkpointer: fake_graph)
    monkeypatch.setattr(triage_job, "get_langfuse_handler", lambda: "fake-handler")
    return fake_graph


async def test_triage_job_persists_pipeline_output(
    client, make_tenant, make_ticket, worker_graph
):
    from worker.tasks.triage_job import triage_ticket

    headers = await make_tenant("Acme")
    ticket = await make_ticket(headers)
    worker_graph.result = {
        "category": "account",
        "urgency": "high",
        "draft_response": "Reset it under Settings > Account.",
    }

    await triage_ticket({}, ticket["id"])

    body = (await client.get(f"/tickets/{ticket['id']}", headers=headers)).json()
    assert body["status"] == "pending_approval"
    assert body["category"] == "account"
    assert body["priority"] == "high"
    assert body["ai_draft"] == "Reset it under Settings > Account."

    state, config = worker_graph.invocations[0]
    assert state["ticket_id"] == ticket["id"]
    assert (
        config["configurable"]["thread_id"] == ticket["id"]
    )  # same id the approve endpoint resumes
    assert config["callbacks"] == ["fake-handler"]


async def test_triage_job_ignores_a_ticket_that_no_longer_exists(worker_graph):
    from worker.tasks.triage_job import triage_ticket

    await triage_ticket({}, str(uuid.uuid4()))

    assert worker_graph.invocations == []
