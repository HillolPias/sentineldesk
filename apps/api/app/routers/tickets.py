import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Ticket, TicketStatus
from app.auth.dependencies import get_current_tenant
from app.db.session import get_db
from app.schemas.ticket import TicketCreate, TicketResponse

from worker.pipeline.checkpointer import get_checkpointer
from worker.pipeline.graph import compile_graph

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate,
    request: Request,
    current: dict = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    ticket = Ticket(
        tenant_id=uuid.UUID(current["tenant_id"]),
        subject=payload.subject,
        body=payload.body,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    await request.app.state.redis.enqueue_job("triage_ticket", str(ticket.id))

    return ticket


@router.get("", response_model=list[TicketResponse])
async def list_tickets(
    current: dict = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Ticket).where(Ticket.tenant_id == uuid.UUID(current["tenant_id"]))
    )
    return result.scalars().all()


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: uuid.UUID,
    current: dict = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Ticket).where(
            Ticket.id == ticket_id,
            Ticket.tenant_id == uuid.UUID(current["tenant_id"]),
        )
    )
    ticket = result.scalar_one_or_none()
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )
    return ticket


@router.post("/{ticket_id}/approve", response_model=TicketResponse)
async def approve_ticket(
    ticket_id: uuid.UUID,
    current: dict = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Ticket).where(
            Ticket.id == ticket_id,
            Ticket.tenant_id == uuid.UUID(current["tenant_id"]),
        )
    )
    ticket = result.scalar_one_or_none()
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )

    if ticket.status != TicketStatus.pending_approval:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ticket is not awaiting approval (current status: {ticket.status})",
        )

    config = {"configurable": {"thread_id": str(ticket.id)}}

    async with get_checkpointer() as checkpointer:
        graph = compile_graph(checkpointer)

        snapshot = await graph.aget_state(config)
        if not snapshot.next:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No paused graph run found for this ticket",
            )

        await graph.ainvoke(None, config=config)

    ticket.status = TicketStatus.sent
    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/reject", response_model=TicketResponse)
async def reject_ticket(
    ticket_id: uuid.UUID,
    current: dict = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Ticket).where(
            Ticket.id == ticket_id,
            Ticket.tenant_id == uuid.UUID(current["tenant_id"]),
        )
    )
    ticket = result.scalar_one_or_none()
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )

    if ticket.status != TicketStatus.pending_approval:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ticket is not awaiting approval (current status: {ticket.status})",
        )

    ticket.status = TicketStatus.rejected
    await db.commit()
    await db.refresh(ticket)
    return ticket
