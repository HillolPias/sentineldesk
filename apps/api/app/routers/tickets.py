import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Ticket
from app.auth.dependencies import get_current_tenant
from app.db.session import get_db
from app.schemas.ticket import TicketCreate, TicketResponse

from arq import create_pool
from worker.settings import get_redis_settings

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate,
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

    redis = await create_pool(get_redis_settings())
    await redis.enqueue_job("triage_ticket", str(ticket.id))
    await redis.close()

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
