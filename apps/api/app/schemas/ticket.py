import datetime
from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict
from app.db.models import TicketStatus


class TicketCreate(BaseModel):
    subject: str
    body: str


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject: str
    body: str
    status: TicketStatus
    ai_draft: str | None
    priority: str | None
    created_at: datetime
    updated_at: datetime
