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
