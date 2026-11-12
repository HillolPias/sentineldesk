# Design decisions

Each entry: the decision, why, and what it costs.

## 1. Shared tables with a `tenant_id` column

**Why:** Schema-per-tenant and database-per-tenant make migrations and connection pooling painful
beyond a few dozen tenants. A shared schema is what most B2B SaaS runs.
**Cost:** one forgotten `WHERE tenant_id = ...` leaks data. Mitigations: the tenant comes from the signed
JWT, every ticket query is scoped, isolation is covered by tests (a regression fails CI).
Next hardening step: Postgres row-level security.

## 2. Cross-tenant access returns 404, not 403

A 403 confirms the resource exists. A 404 reveals nothing about other tenants' data.

## 3. Arq instead of Celery

**Why:** async-native, small, fits an async FastAPI codebase, Redis-only.
**Cost:** smaller ecosystem and fewer built-in features than Celery.

## 4. Durable approval via the LangGraph Postgres checkpointer

**Why:** the worker pauses the run, and a different process (the API) resumes it later, so an in-memory
`interrupt()` cannot work. State is checkpointed to Postgres, keyed by `thread_id` = ticket id.
**Cost:** a second driver (psycopg) beside asyncpg, and LangGraph owns its tables (excluded from Alembic
autogenerate).

## 5. pgvector instead of a separate vector database

**Why:** one datastore, one backup story, retrieval is a normal SQL query.
**Cost:** embedding calls are explicit (no built-in embedder), and it is not built for very large corpora.

## 6. API and worker in one container on the free tier

**Why:** free web services sleep, and a separate worker would never wake. Same container means the
enqueue request wakes the worker too. Entrypoints stay separate so splitting is a config change.
**Cost:** a crashed worker is not restarted; not how I would run production.

## 7. Idempotent invoicing

`tickets.invoiced_at` marks billed usage; the invoice route locks the rows (`FOR UPDATE`), and Stripe
calls carry idempotency keys derived from the billed ticket ids. A retry after a partial failure cannot
double-bill.

## 8. Cost-aware model use

`gpt-4o-mini` for every step, temperature 0 for classification and the guardrail, grounded drafting that
is told not to invent policy. A bigger model for drafting is a one-line change.
