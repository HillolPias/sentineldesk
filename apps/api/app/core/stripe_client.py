import asyncio

import stripe

from app.core.config import get_settings

settings = get_settings()
stripe.api_key = settings.stripe_secret_key


async def create_customer(tenant_name: str, email: str) -> str:
    customer = await asyncio.to_thread(
        stripe.Customer.create, name=tenant_name, email=email
    )
    return customer.id


async def create_usage_invoice(
    customer_id: str,
    quantity: int,
    unit_amount_cents: int,
    idempotency_key: str,
) -> dict:
    invoice = await asyncio.to_thread(
        stripe.Invoice.create,
        customer=customer_id,
        currency="usd",
        collection_method="send_invoice",
        days_until_due=30,
        pending_invoice_items_behavior="exclude",
        idempotency_key=f"{idempotency_key}-inv",
    )
    await asyncio.to_thread(
        stripe.InvoiceItem.create,
        customer=customer_id,
        invoice=invoice.id,
        currency="usd",
        amount=quantity * unit_amount_cents,
        description=f"SentinelDesk AI triage: {quantity} tickets processed",
        idempotency_key=f"{idempotency_key}-item",
    )
    finalized = await asyncio.to_thread(stripe.Invoice.finalize_invoice, invoice.id)
    return {
        "id": finalized.id,
        "hosted_invoice_url": finalized.hosted_invoice_url,
        "amount_due": finalized.amount_due,
    }
