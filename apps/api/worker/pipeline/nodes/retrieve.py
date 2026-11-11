from sqlalchemy import select

from app.db.models_kb import KnowledgeArticle
from app.db.session import async_session_factory
from worker.pipeline.seed_kb import get_embedding
from worker.pipeline.state import TriageState


async def retrieve_node(state: TriageState) -> dict:
    query_text = f"{state['subject']} {state['body']}"
    query_embedding = await get_embedding(query_text)

    async with async_session_factory() as db:
        result = await db.execute(
            select(KnowledgeArticle)
            .order_by(KnowledgeArticle.embedding.l2_distance(query_embedding))
            .limit(2)
        )
        articles = result.scalars().all()

    context = "\n\n".join(f"[{a.title}]\n{a.content}" for a in articles)

    return {"retrieved_context": context}
