import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_tenant
from app.core.stripe_client import create_usage_invoice
from app.db.models import Ticket, Tenant, TicketStatus
from app.db.session import get_db

router = APIRouter(prefix="/billing", tags=["billing"])

# Hardcoded for the demo. A production setup would use Stripe Products/Prices
# and metered subscriptions instead of computing the amount ourselves.
PRICE_PER_TICKET_CENTS = 10


class BillingSummary(BaseModel):
    unbilled_tickets: int
    price_per_ticket_cents: int
    amount_due_cents: int


class InvoiceResponse(BaseModel):
    invoice_id: str
    hosted_invoice_url: str | None
    tickets_billed: int
    amount_due_cents: int


def _billable(tenant_id: uuid.UUID):
    return (
        Ticket.tenant_id == tenant_id,
        Ticket.invoiced_at.is_(None),
        Ticket.status == TicketStatus.pending,
    )


@router.get("/summary", response_model=BillingSummary)
async def billing_summary(
    current: dict = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current["tenant_id"])
    result = await db.execute(
        select(func.count()).select_from(Ticket).where(*_billable(tenant_id))
    )
    count = result.scalar_one()
    return BillingSummary(
        unbilled_tickets=count,
        price_per_ticket_cents=PRICE_PER_TICKET_CENTS,
        amount_due_cents=count * PRICE_PER_TICKET_CENTS,
    )


@router.post("/invoice", response_model=InvoiceResponse)
async def generate_invoice(
    current: dict = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current["tenant_id"])

    tenant = await db.get(Tenant, tenant_id)
    if tenant is None or not tenant.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This workspace has no Stripe customer (create before billing was ahead)",
        )

    # Lock the rows so two concurrent invoice requests can't bill the same tickets.
    result = await db.execute(
        select(Ticket).where(*_billable(tenant_id)).with_for_update()
    )
    tickets = result.scalars().all()

    if not tickets:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Nothing to invoice"
        )

    key = hashlib.sha256(
        ",".join(sorted(str(t.id) for t in tickets)).encode()
    ).hexdigest()[:32]

    invoice = await create_usage_invoice(
        customer_id=tenant.stripe_customer_id,
        quantity=len(tickets),
        unit_amount_cents=PRICE_PER_TICKET_CENTS,
        idempotency_key=f"sentineldesk-{key}",
    )

    now = datetime.now(timezone.utc)
    for t in tickets:
        t.invoiced_at = now
    await db.commit()

    return InvoiceResponse(
        invoice_id=invoice["id"],
        hosted_invoice_url=invoice.get("hosted_invoice_url"),
        tickets_billed=len(tickets),
        amount_due_cents=invoice["amount_due"],
    )
