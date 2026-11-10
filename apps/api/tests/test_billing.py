from sqlalchemy import update

from app.db.models import Tenant, TicketStatus
from app.db.session import async_session_factory


async def _three_tickets(make_ticket, set_status, headers):
    t1 = await make_ticket(headers, subject="One")
    t2 = await make_ticket(headers, subject="Two")
    t3 = await make_ticket(headers, subject="Three")

    await set_status(t1["id"], TicketStatus.pending_approval)
    await set_status(t2["id"], TicketStatus.sent)
    # t3 stays "pending": the AI hasn't processed it, so it isn't billable
    return t1, t2, t3


async def test_summary_counts_only_processed_unbilled_tickets(
    client, make_tenant, make_ticket, set_status
):
    headers = await make_tenant("Acme")
    await _three_tickets(make_ticket, set_status, headers)

    resp = await client.get("/billing/summary", headers=headers)

    assert resp.json() == {
        "unbilled_tickets": 2,
        "price_per_ticket_cents": 10,
        "amount_due_cents": 20,
    }


async def test_invoice_bills_each_ticket_exactly_once(
    client, make_tenant, make_ticket, set_status, stripe_invoice_calls
):
    headers = await make_tenant("Acme")
    await _three_tickets(make_ticket, set_status, headers)

    resp = await client.post("/billing/invoice", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["tickets_billed"] == 2
    assert body["amount_due_cents"] == 20
    assert body["hosted_invoice_url"]
    assert len(stripe_invoice_calls) == 1
    assert stripe_invoice_calls[0]["quantity"] == 2
    assert stripe_invoice_calls[0]["customer_id"].startswith("cus_test_")

    summary = await client.get("/billing/summary", headers=headers)
    assert summary.json()["unbilled_tickets"] == 0

    again = await client.post("/billing/invoice", headers=headers)
    assert again.status_code == 409
    assert len(stripe_invoice_calls) == 1  # Stripe was not called a second time


async def test_invoice_with_nothing_to_bill_returns_409(
    client, make_tenant, stripe_invoice_calls
):
    headers = await make_tenant("Acme")
    resp = await client.post("/billing/invoice", headers=headers)
    assert resp.status_code == 409
    assert stripe_invoice_calls == []


async def test_one_tenants_usage_never_leaks_into_another_tenants_bill(
    client, make_tenant, make_ticket, set_status, stripe_invoice_calls
):
    a = await make_tenant("Acme")
    b = await make_tenant("Globex")
    await _three_tickets(make_ticket, set_status, a)

    b_summary = await client.get("/billing/summary", headers=b)
    b_invoice = await client.post("/billing/invoice", headers=b)

    assert b_summary.json()["unbilled_tickets"] == 0
    assert b_invoice.status_code == 409
    a_summary = await client.get("/billing/summary", headers=a)
    assert (
        a_summary.json()["unbilled_tickets"] == 2
    )  # B's attempt didn't consume A's tickets


async def test_invoice_requires_a_stripe_customer(
    client, make_tenant, stripe_invoice_calls
):
    headers = await make_tenant("Acme")
    async with async_session_factory() as db:
        await db.execute(update(Tenant).values(stripe_customer_id=None))
        await db.commit()

    resp = await client.post("/billing/invoice", headers=headers)

    assert resp.status_code == 400
    assert stripe_invoice_calls == []
