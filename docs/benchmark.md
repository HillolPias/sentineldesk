# Benchmarks

What these numbers are, and what they are not: the **real application** (FastAPI, Redis/Arq queue,
Postgres) running in a Linux container with a CPU and memory limit on a development machine. Two things
are faked so the test is free and repeatable: **Stripe**, and the **LLM pipeline** (the worker waits 10 s
per ticket, close to the ~10 s measured on real runs). They are not production numbers; the free hosting
tier is slower than this.

## Environment

|                  |                                                                                               |
| ---------------- | --------------------------------------------------------------------------------------------- |
| Machine          | AMD Ryzen 5 3400G with Radeon Vega Graphics, 14 GB RAM, Windows + Docker Desktop 29.9.2(WSL2) |
| Container        | [0.5 CPU / 512 MB] (a second run at 0.1 CPU approximates Render's free tier)                  |
| Postgres / Redis | local containers on the same machine                                                          |
| Worker           | Arq defaults (10 concurrent jobs), fake LLM 10 s per ticket                                   |
| Load generator   | `apps/api/benchmarks/loadtest.py`, 4 workspaces, 25 concurrent clients                        |

## Results: ingestion and worker throughput (100 tickets)

| Metric                             | Value                 |
| ---------------------------------- | --------------------- |
| Tickets sent / accepted            | 100 / 100             |
| Concurrent clients                 | 25                    |
| Ingest throughput                  | 12.3 req/s            |
| Ingest latency p50 / p95 / p99     | 1678 / 3017 / 3125 ms |
| Errors (non-201)                   | 0                     |
| Processed by the worker            | 100 / 100             |
| Time to completion p50 / p95 / max | 60 / 101 / 101 s      |
| Time to drain the whole burst      | 109 s                 |
| Worker throughput                  | 54.9 tickets/min      |

| Metric                             | Value                   |
| ---------------------------------- | ----------------------- |
| Tickets sent / accepted            | 100 / 100               |
| Concurrent clients                 | 25                      |
| Ingest throughput                  | 2.3 req/s               |
| Ingest latency p50 / p95 / p99     | 9200 / 14401 / 15397 ms |
| Errors (non-201)                   | 0                       |
| Processed by the worker            | 100 / 100               |
| Time to completion p50 / p95 / max | 51 / 83 / 86 s          |
| Time to drain the whole burst      | 130 s                   |
| Worker throughput                  | 46.3 tickets/min        |

## Results: rate limit under a concurrent burst

40 concurrent requests from one workspace against a limit of 10 per hour: 10 accepted, 30 rejected with 429, 0 other.
PASS: the limit held exactly under concurrency.

## What this shows

- **The queue decouples acceptance from processing.** 100 tickets were accepted in about 8 s with zero
  errors and fully processed in 109 s. A synchronous design would hold each request open for the whole
  pipeline (10 s here, the injected delay), so the client-visible cost of a ticket excludes the LLM work.
- **The worker runs at its configured ceiling.** Arq runs 10 jobs at a time and each takes 10 s, so the
  ceiling is 60 tickets/min; the measurement was 54.9/min (about 91%). Time to completion grows with
  queue position (p50 60 s, max 101 s), as a FIFO queue with 10 workers should. Scaling processing
  means raising `max_jobs` or adding worker instances; the LLM provider's rate limits become the
  next constraint.
- **Ingest latency at 25 clients is queueing, not the cost of one request.** The API sustained about
  12 req/s on this container; with 25 clients in flight, Little's law gives 25 / 12.3 ≈ 2 s average
  latency, matching the measured p50 of 1.7 s and p95 of 3.0 s. These figures describe a saturated
  server under a closed-loop load.
- **The rate limiter is exact under concurrency.** The counter is created with `SET NX EX` and
  incremented with `INCR`, both atomic in Redis, so 40 simultaneous requests produced exactly 10
  acceptances. This was tested against a single API process; further instances would share the same
  Redis counter, but that was not tested.

## What this does not show

- Per-request latency at low load, or why throughput plateaus near 12 req/s. A CPU limit shared with
  the worker, round trips to Postgres and Redis across Docker Desktop's host bridge, and the default
  database pool (5 + 10 connections) are all candidates; none has been isolated yet.
- Variance: this is a single run.
- Production behaviour: free-tier CPU, network distance to Neon, and the real LLM's latency and rate limits.

## Reproduce

docker run commands:

docker run --rm --name sd-bench -p 8001:8000 --cpus=0.5 --memory=512m \
 -e DATABASE_URL="postgresql+asyncpg://sentinel:sentinel@host.docker.internal:5432/sentineldesk_test" \
 -e REDIS_URL="redis://host.docker.internal:6379" \
 -e OPENAI_API_KEY=sk-bench -e LANGFUSE_PUBLIC_KEY=pk-bench -e LANGFUSE_SECRET_KEY=sk-bench \
 -e LANGFUSE_HOST=https://cloud.langfuse.com -e LANGFUSE_TRACING_ENABLED=false \
 -e JWT_SECRET=bench -e STRIPE_SECRET_KEY=sk_test_bench \
 -e RATE_LIMIT_TICKETS_PER_HOUR=100000 -e RATE_LIMIT_DAILY_TICKET_CAP=100000 \
 -e RATE_LIMIT_SIGNUPS_PER_HOUR_PER_IP=1000 -e FAKE_LLM_SECONDS=10 \
 sentineldesk-bench sh -c "python -m benchmarks.bench_worker & exec python -m benchmarks.bench_api"

docker run --rm --name sd-bench -p 8001:8000 --cpus=0.5 --memory=512m \
 -e DATABASE_URL="postgresql+asyncpg://sentinel:sentinel@host.docker.internal:5432/sentineldesk_test" \
 -e REDIS_URL="redis://host.docker.internal:6379" \
 -e OPENAI_API_KEY=sk-bench -e LANGFUSE_PUBLIC_KEY=pk-bench -e LANGFUSE_SECRET_KEY=sk-bench \
 -e LANGFUSE_HOST=https://cloud.langfuse.com -e LANGFUSE_TRACING_ENABLED=false \
 -e JWT_SECRET=bench -e STRIPE_SECRET_KEY=sk_test_bench \
 -e RATE_LIMIT_SIGNUPS_PER_HOUR_PER_IP=1000 -e FAKE_LLM_SECONDS=10 \
 sentineldesk-bench sh -c "python -m benchmarks.bench_worker & exec python -m benchmarks.bench_api"

the two loadtest commands:

uv run python -m benchmarks.loadtest throughput --tickets 100 --concurrency 25 --tenants 4

uv run python -m benchmarks.loadtest limits --attempts 40 --expected-limit 10
