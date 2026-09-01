from app.db.session import async_session_factory
from sqlalchemy import select
from app.db.models import Ticket, TicketStatus
import uuid
import asyncio


async def triage_ticket(ctx, ticket_id: str) -> None:
    """
    Arq job: picks up a newly created ticket and processes it.
    'ctx' is Arq's context dict (injected automatically) - holds things
    like the Redis pool; we don't need it yet, but every Arq job function
    must accept it as first parameter.
    """

    async with async_session_factory() as db:
        result = await db.execute(
            select(Ticket).where(Ticket.id == uuid.UUID(ticket_id))
        )
        ticket = result.scalar_one_or_none()

        if ticket is None:
            # Job could theoretically run after the ticket was deleted; don't crash the worker.
            return

        # --- Stub for now; Step 9 replaces this with the real LangGraph pipeline ---
        await asyncio.sleep(2)  # simulate work, prove the async decoupling visibly
        ticket.status = TicketStatus.pending_appoval
        ticket.priority = "medium"
        ticket.ai_draft = "This is a placeholder AI-generated draft response."
        # ---------------------------------------------------------------------------

        await db.commit()
