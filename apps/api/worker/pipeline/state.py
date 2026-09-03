from typing import TypedDict, Optional


class TriageState(TypedDict):
    ticket_id: str
    subject: str
    body: str

    # populated by classify node
    category: Optional[str]
    urgency: Optional[str]

    # populated by retrieve node
    retrieved_context: Optional[str]

    # populated by draft node
    draft_response: Optional[str]

    # populated by guardrail node
    guardrail_passed: Optional[bool]
    guardrail_reason: Optional[str]
