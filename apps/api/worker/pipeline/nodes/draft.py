from openai import AsyncOpenAI
from app.core.config import get_settings
from worker.pipeline.state import TriageState

settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key)

DRAFT_MODEL = "gpt-4o-mini"

DRAFT_PROMPT = """You are a helpful support agent drafting a reply to a customer ticket.

Ticket subject: {subject}
Ticket body: {body}
Category: {category}

Relevant help-center articles:
{context}

Write a concise, friendly draft reply. Ground your answer in the help-center article above where relevant. If the articles don't cover the issue, say so honestly rather than guessing. Do not make up policies or facts not present in the articles.
"""


async def draft_node(state: TriageState) -> dict:
    prompt = DRAFT_PROMPT.format(
        subject=state["subject"],
        body=state["body"],
        category=state["category"],
        context=state["retrieved_context"],
    )

    response = await client.chat.completions.create(
        model=DRAFT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )

    return {"draft_response": response.choices[0].message.content}
