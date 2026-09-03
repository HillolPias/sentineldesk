import json
from openai import AsyncOpenAI
from app.core.config import get_settings
from worker.pipeline.state import TriageState

settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key)

GUARDRAIL_MODEL = "gpt-4o-mini"

GUARDRAIL_PROMPT = """You are a safety reviewer checking an AI-drafted customer support reply
before it's sent. Check for:
- Made-up policies, prices, or facts not grounded in the provided context
- Inappropriate tone, promises the company can't guarantee, or leaked internal info
- Anything a human should double-check before sending

Original ticket: {subject} — {body}
Context the draft was supposed to be grounded in:
{context}

Draft reply to review:
{draft}

Respond with ONLY valid JSON, no other text:
{{"passed": <true or false>, "reason": "<brief explanation, especially if failed>"}}"""


async def guardrail_node(state: TriageState) -> dict:
    prompt = GUARDRAIL_PROMPT.format(
        subject=state["subject"],
        body=state["body"],
        context=state["retrieved_context"],
        draft=state["draft_response"],
    )

    response = await client.chat.completions.create(
        model=GUARDRAIL_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)

    return {
        "guardrail_passed": result["passed"],
        "guardrail_reason": result["reason"],
    }
