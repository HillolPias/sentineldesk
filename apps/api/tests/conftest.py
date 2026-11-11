import os
import subprocess
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio

API_ROOT = Path(__file__).resolve().parents[1]

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentineldesk_test",
)

# Safety: the fixtures below TRUNCATE tables. Refuse to run against anything
# that isn't clearly a test database.
_db_name = TEST_DATABASE_URL.rsplit("/", 1)[-1].split("?")[0]
if not _db_name.endswith("_test"):
    raise RuntimeError(f"Refusing to run tests against non-test database: {_db_name}")

# Must happen before any app module is imported: get_settings() is cached and
# app.db.session builds its engine at import time. Environment variables take
# priority over .env, so a developer's real keys can never leak into tests.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["OPENAI_API_KEY"] = "sk-test-not-real"
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-test"
os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-test"
os.environ["LANGFUSE_HOST"] = "https://cloud.lanngfuse.com"
os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["STRIPE_SECRET_KEY"] = "sk_test_not_real"

from sqlalchemy import text  # noqa: E402

from app.db.models import Ticket  # noqa: E402
from app.db.session import async_session_factory, engine  # noqa: E402
from main import app as fastapi_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    """Build the schema by running the real migration, once per test session."""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=API_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.exit(
            f"alembic upgrade failed:\n{result.stdout}\n{result.stderr}", returncode=1
        )


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


async def _truncate():
    async with engine.begin() as conn:
        await conn.execute(
            text("TRUNCATE tenants, users, tickets RESTART IDENTITY CASCADE")
        )


@pytest_asyncio.fixture(autouse=True)
async def clean_db():
    await _truncate()
    yield
    await _truncate()


# ---------- fakes ----------


class FakeRedis:
    """Stands in for the Arq pool: records jobs instead of queueing them."""

    def __init__(self):
        self.enqueued = []

    async def enqueue_job(self, function, *args, **kwargs):
        self.enqueued.append((function, args))


class FakeGraph:
    """Stands in for the compiled LangGraph graph: no LLM, no checkpointer."""

    def __init__(self):
        self.paused = True
        self.invocations = []
        self.result = {"finalized": True}

    async def aget_state(self, config):
        return SimpleNamespace(next=("finalize",) if self.paused else ())

    async def ainvoke(self, state, config=None):
        self.invocations.append((state, config))
        return self.result


@pytest.fixture(autouse=True)
def fake_redis():
    redis = FakeRedis()
    fastapi_app.state.redis = redis
    return redis


@pytest.fixture
def fake_graph(monkeypatch):
    graph = FakeGraph()

    @asynccontextmanager
    async def fake_checkpointer():
        yield object()

    monkeypatch.setattr("app.routers.tickets.get_checkpointer", fake_checkpointer)
    monkeypatch.setattr("app.routers.tickets.compile_graph", lambda checkpointer: graph)
    return graph


@pytest.fixture(autouse=True)
def stub_stripe_customer(monkeypatch):
    counter = {"n": 0}

    async def fake_create_customer(tenant_name, email):
        counter["n"] += 1
        return f"cus_test_{counter['n']}"

    monkeypatch.setattr("app.routers.auth.create_customer", fake_create_customer)


@pytest.fixture
def stripe_invoice_calls(monkeypatch):
    calls = []

    async def fake_create_usage_invoice(
        customer_id, quantity, unit_amount_cents, idempotency_key
    ):
        calls.append(
            {
                "customer_id": customer_id,
                "quantity": quantity,
                "unit_amount_cents": unit_amount_cents,
                "idempotency_key": idempotency_key,
            }
        )
        return {
            "id": f"in_test_{len(calls)}",
            "hosted_invoice_url": "https://invoice.test/in_test",
            "amount_due": quantity * unit_amount_cents,
        }

    monkeypatch.setattr(
        "app.routers.billing.create_usage_invoice", fake_create_usage_invoice
    )

    return calls


# ---------- helpers ----------


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def make_tenant(client):
    async def _make(name="Acme", email=None):
        email = email or f"{name.lower().replace(' ', '')}@example.com"
        resp = await client.post(
            "/auth/signup",
            json={"tenant_name": name, "email": email, "password": "testpass123"},
        )
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _make


@pytest_asyncio.fixture
async def make_ticket(client):
    async def _make(headers, subject="Help", body="Something broke"):
        resp = await client.post(
            "/tickets", json={"subject": subject, "body": body}, headers=headers
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make


@pytest_asyncio.fixture
async def set_status():
    """Simulate what the worker does, without running it."""

    async def _set(ticket_id, status):
        async with async_session_factory() as db:
            ticket = await db.get(Ticket, uuid.UUID(ticket_id))
            ticket.status = status
            await db.commit()

    return _set
