from typing import TypedDict


class TriageState(TypedDict):
    ticket_id: str
    subject: str
    body: str

    # populated by classify node
    category: str | None
    urgency: str | None

    # populated by retrieve node
    retrieved_context: str | None

    # populated by draft node
    draft_response: str | None

    # populated by guardrail node
    guardrail_passed: bool | None
    guardrail_reason: str | None

    # populated by finalize node, after human approval resumes the graph
    finalized: bool | None
