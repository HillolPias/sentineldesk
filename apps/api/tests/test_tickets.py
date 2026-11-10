import uuid

from app.db.models import TicketStatus


async def test_create_ticket_starts_pending_and_enqueues_triage_job(
    client, make_tenant, fake_redis
):
    headers = await make_tenant("Acme")

    resp = await client.post(
        "/tickets",
        json={"subject": "Can't log in", "body": "Error on login"},
        headers=headers,
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["ai_draft"] is None
    assert fake_redis.enqueued == [("triage_ticket", (body["id"],))]


async def test_approve_resumes_paused_graph_and_marks_sent(
    client, make_tenant, make_ticket, set_status, fake_graph
):
    headers = await make_tenant("Acme")
    ticket = await make_ticket(headers)
    await set_status(ticket["id"], TicketStatus.pending_approval)

    resp = await client.post(f"/tickets/{ticket['id']}/approve", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"
    assert len(fake_graph.invocations) == 1
    state, config = fake_graph.invocations[0]
    assert state is None
    assert config == {"configurable": {"thread_id": ticket["id"]}}


async def test_approve_twice_is_rejected(
    client, make_tenant, make_ticket, set_status, fake_graph
):
    headers = await make_tenant("Acme")
    ticket = await make_ticket(headers)
    await set_status(ticket["id"], TicketStatus.pending_approval)

    first = await client.post(f"/tickets/{ticket['id']}/approve", headers=headers)
    second = await client.post(f"/tickets/{ticket['id']}/approve", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 409
    assert len(fake_graph.invocations) == 1


async def test_cannot_approve_ticket_still_being_processed(
    client, make_tenant, make_ticket, fake_graph
):
    headers = await make_tenant("Acme")
    ticket = await make_ticket(headers)  # status stays "pending"

    resp = await client.post(f"/tickets/{ticket['id']}/approve", headers=headers)

    assert resp.status_code == 409
    assert fake_graph.invocations == []


async def test_approve_fails_cleanly_when_no_paused_graph_exists(
    client, make_tenant, make_ticket, set_status, fake_graph
):
    headers = await make_tenant("Acme")
    ticket = await make_ticket(headers)
    await set_status(ticket["id"], TicketStatus.pending_approval)
    fake_graph.paused = False  # DB says "pending_approval", checkpoint disagrees

    resp = await client.post(f"/tickets/{ticket['id']}/approve", headers=headers)

    assert resp.status_code == 409
    assert fake_graph.invocations == []
    after = await client.get(f"/tickets/{ticket['id']}", headers=headers)
    assert after.json()["status"] == "pending_approval"  # not marked "sent"


async def test_reject_marks_rejected_without_touching_the_graph(
    client, make_tenant, make_ticket, set_status, fake_graph
):
    headers = await make_tenant("Acme")
    ticket = await make_ticket(headers)
    await set_status(ticket["id"], TicketStatus.pending_approval)

    resp = await client.post(f"/tickets/{ticket['id']}/reject", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert fake_graph.invocations == []


async def test_cannot_reject_ticket_that_is_not_awaiting_approval(
    client, make_tenant, make_ticket
):
    headers = await make_tenant("Acme")
    ticket = await make_ticket(headers)  # still "pending"

    resp = await client.post(f"/tickets/{ticket['id']}/reject", headers=headers)

    assert resp.status_code == 409


async def test_approve_unknown_ticket_return_404(client, make_tenant, fake_graph):
    headers = await make_tenant("Acme")
    resp = await client.post(f"/tickets/{uuid.uuid4()}/approve", headers=headers)
    assert resp.status_code == 404
    assert fake_graph.invocations == []
