from app.db.session import async_session_factory
from sqlalchemy import select
from app.db.models import Ticket, TicketStatus
import uuid
from worker.pipeline.checkpointer import get_checkpointer
from worker.pipeline.graph import compile_graph
from worker.pipeline.observability import get_langfuse_handler


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

        config = {"configurable": {"thread_id": ticket_id}}

        async with get_checkpointer() as checkpointer:
            graph = compile_graph(checkpointer)

            initial_state = {
                "ticket_id": ticket_id,
                "subject": ticket.subject,
                "body": ticket.body,
            }

            langfuse_handler = get_langfuse_handler()
            result_state = await graph.ainvoke(
                initial_state,
                config={
                    **config,
                    "callbacks": [langfuse_handler],
                    "metadata": {
                        "langfuse_session_id": ticket_id,
                    },
                },
            )

        # Graph has paused after guardrail (interrupt_after=["guardrail"]).
        # Reflect that in the ticket row so the API/UI can show it.
        ticket.status = TicketStatus.pending_approval
        ticket.category = result_state.get("category")
        ticket.priority = result_state.get("urgency")
        ticket.ai_draft = result_state.get("draft_response")

        await db.commit()
