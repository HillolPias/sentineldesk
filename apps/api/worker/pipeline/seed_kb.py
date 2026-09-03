"""
Run manually to populate the knowledge_articles table with embeddings.
Safe to re-run — upserts by external_id rather than duplicating rows.
"""

import asyncio
from openai import AsyncOpenAI
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.db.models_kb import KnowledgeArticle
from worker.pipeline.kb_seed_data import KB_ARTICLES

EMBEDDING_MODEL = "text-embedding-3-small"

settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key)


async def get_embedding(text: str) -> list[float]:
    response = await client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


async def seed():
    async with async_session_factory() as db:
        for article in KB_ARTICLES:
            result = await db.execute(
                select(KnowledgeArticle).where(
                    KnowledgeArticle.external_id == article["id"]
                )
            )
            existing = result.scalar_one_or_none()

            embedding = await get_embedding(article["content"])

            if existing:
                existing.title = article["title"]
                existing.content = article["content"]
                existing.category = article["category"]
                existing.embedding = embedding
                print(f"Updated {article['id']}")
            else:
                db.add(
                    KnowledgeArticle(
                        external_id=article["id"],
                        title=article["title"],
                        content=article["content"],
                        category=article["category"],
                        embedding=embedding,
                    )
                )
                print(f"Inserted {article['id']}")

        await db.commit()

    print(f"Done — seeded {len(KB_ARTICLES)} articles")


if __name__ == "__main__":
    asyncio.run(seed())
