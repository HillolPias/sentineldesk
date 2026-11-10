import uuid

from app.db.models import TicketStatus


async def test_tenant_cannot_read_another_tenants_ticket(
    client, make_tenant, make_ticket
):
    a = await make_tenant("Acme")
    b = await make_tenant("Globex")
    ticket = await make_ticket(a)

    resp = await client.get(f"/tickets/{ticket['id']}", headers=b)

    # 404, not 403: a 403 would confirm the ticket exists.
    assert resp.status_code == 404


async def test_ticket_lists_are_scoped_per_tenant(client, make_tenant, make_ticket):
    a = await make_tenant("Acme")
    b = await make_tenant("Globex")
    await make_ticket(a, subject="A1")
    await make_ticket(a, subject="A2")
    await make_ticket(b, subject="B1")

    a_subjects = {
        t["subject"] for t in (await client.get("/tickets", headers=a)).json()
    }
    b_subjects = {
        t["subject"] for t in (await client.get("/tickets", headers=b)).json()
    }

    assert a_subjects == {"A1", "A2"}
    assert b_subjects == {"B1"}


async def test_tenant_cannot_approve_or_reject_another_tenants_ticket(
    client, make_tenant, make_ticket, set_status, fake_graph
):
    a = await make_tenant("Acme")
    b = await make_tenant("Globex")
    ticket = await make_ticket(a)
    await set_status(ticket["id"], TicketStatus.pending_approval)

    approve = await client.post(f"/tickets/{ticket['id']}/approve", headers=b)
    reject = await client.post(f"/tickets/{ticket['id']}/reject", headers=b)

    assert approve.status_code == 404
    assert reject.status_code == 404
    assert fake_graph.invocations == []  # the paused graph was never resumed

    still_there = await client.get(f"/tickets/{ticket['id']}", headers=a)
    assert still_there.json()["status"] == "pending_approval"


async def test_unknown_ticket_id_returns_404(client, make_tenant):
    a = await make_tenant("Acme")
    resp = await client.get(f"/tickets/{uuid.uuid4()}", headers=a)
    assert resp.status_code == 404
