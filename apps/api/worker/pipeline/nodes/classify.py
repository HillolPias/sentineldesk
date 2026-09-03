import json
from openai import AsyncOpenAI
from app.core.config import get_settings
from worker.pipeline.state import TriageState

settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key)

CLASSIFY_MODEL = "gpt-4o-mini"

CLASSIFY_PROMPT = """You are a suppert ticket triage assistant. Classify this ticket.

Subject: {subject}
Body: {body}

Respond with ONLY valid JSON, no extra text:
{{"category": "<one of: account, billing, technical, other>", "urgency": "<one of: low, medium, high>"}}
"""


async def classify_node(state: TriageState) -> dict:
    prompt = CLASSIFY_PROMPT.format(subject=state["subject"], body=state["body"])

    response = await client.chat.completions.create(
        model=CLASSIFY_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)

    return {
        "category": result["category"],
        "urgency": result["urgency"],
    }
