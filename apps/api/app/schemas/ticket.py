import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import TicketStatus


class TicketCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=4000)


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject: str
    body: str
    status: TicketStatus
    category: str | None  # NEW
    ai_draft: str | None
    priority: str | None
    created_at: datetime
    updated_at: datetime
