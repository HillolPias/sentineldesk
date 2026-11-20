"""Load test for SentinelDesk. Local benchmark stack only; see docs/benchmarks.md.

python -m benchmarks.loadtest throughput --tickets 100 --concurrency 25 --tenants 4
python -m benchmarks.loadtest limits --attempts 40 --expected-limit 10
"""

import argparse
import asyncio
import os
import sys
import time
from collections import Counter
from urllib.parse import urlparse

import httpx

TICKET = {"subject": "Load test", "body": "I forgot my password and need to reset it."}


def pct(values: list[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[round(p / 100 * (len(ordered) - 1))]


def refuse_remote(base: str) -> None:
    host = urlparse(base).hostname
    if host not in {"localhost", "127.0.0.1"} and os.environ.get("ALLOW_REMOTE") != "1":
        sys.exit(
            f"Refusing to load-test {host}: this tool is for the local benchmark stack only."
        )


async def signup(client: httpx.AsyncClient, i: int) -> dict:
    resp = await client.post(
        "/auth/signup",
        json={
            "tenant_name": f"Bench {i}",
            "email": f"bench{i}-{time.time_ns()}@example.com",
            "password": "bench-pass-123",
        },
    )
    resp.raise_for_status()
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def throughput(
    base: str, tickets: int, concurrency: int, tenants: int, drain_timeout: float
):
    limits = httpx.Limits(max_connections=concurrency + 10)
    async with httpx.AsyncClient(base_url=base, timeout=120, limits=limits) as client:
        heads = [await signup(client, i) for i in range(tenants)]
        sem = asyncio.Semaphore(concurrency)
        latencies: list[float] = []
        statuses: Counter = Counter()
        accepted: dict[str, float] = {}

        async def one(n: int) -> None:
            async with sem:
                t0 = time.perf_counter()
                resp = await client.post(
                    "/tickets", json=TICKET, headers=heads[n % tenants]
                )
                elapsed_ms = (time.perf_counter() - t0) * 1000
            statuses[resp.status_code] += 1
            if resp.status_code == 201:
                latencies.append(elapsed_ms)
                accepted[resp.json()["id"]] = time.perf_counter()

        start = time.perf_counter()
        await asyncio.gather(*(one(n) for n in range(tickets)))
        burst_seconds = time.perf_counter() - start
        if not latencies:
            sys.exit(f"No ticket was accepted: {dict(statuses)}")

        done: dict[str, float] = {}
        deadline = time.perf_counter() + drain_timeout
        while len(done) < len(accepted) and time.perf_counter() < deadline:
            for head in heads:
                resp = await client.get("/tickets", headers=head)
                now = time.perf_counter()
                for ticket in resp.json():
                    tid = ticket["id"]
                    if (
                        tid in accepted
                        and tid not in done
                        and ticket["status"] != "pending"
                    ):
                        done[tid] = now
            await asyncio.sleep(0.5)

    waits = [done[t] - accepted[t] for t in done]
    drain__seconds = max(done.values()) - start if done else float("nan")
    ok = statuses[201]
    rows = [
        ("Tickets sent / accepted", f"{tickets} / {ok}"),
        ("Concurrent clients", concurrency),
        ("Ingest throughput", f"{ok / burst_seconds:.1f} req/s"),
        (
            "Ingest latency p50 / p95 / p99",
            f"{pct(latencies, 50):.0f} / {pct(latencies, 95):.0f} / {pct(latencies, 99):.0f} ms",
        ),
        ("Errors (non-201)", tickets - ok),
        ("Processed by the worker", f"{len(done)} / {ok}"),
    ]
    if waits:
        rows += [
            (
                "Time to completion p50 / p95 / max",
                f"{pct(waits, 50):.0f} / {pct(waits, 95):.0f} / {max(waits):.0f} s",
            ),
            ("Time to drain the whole burst", f"{drain__seconds:.0f} s"),
            ("Worker throughput", f"{len(done) / drain__seconds * 60:.1f} tickets/min"),
        ]
    print("\n| Metric | Value |\n|-------|-------|")
    for name, value in rows:
        print(f"| {name} | {value} |")
    print(f"\nStatus codes: {dict(statuses)}")


async def limits_scenario(base: str, attempts: int, expected: int) -> None:
    async with httpx.AsyncClient(base_url=base, timeout=60) as client:
        head = await signup(client, 0)
        responses = await asyncio.gather(
            *(
                client.post("/tickets", json=TICKET, headers=head)
                for _ in range(attempts)
            )
        )
    codes = Counter(r.status_code for r in responses)
    accepted, limited = codes[201], codes[429]
    print(
        f"{attempts} concurrent requests from one workspace -> "
        f"{accepted} accepted, {limited} rate limited, {attempts - accepted - limited} others"
    )
    if accepted != expected or accepted + limited != attempts:
        sys.exit(f"FAIL: expected exactly {expected} accepted")
    print(f"PASS: the limit held exactly under concurrency (limit = {expected})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=["throughput", "limits"])
    parser.add_argument("--base", default="http://localhost:8001")
    parser.add_argument("--tickets", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=25)
    parser.add_argument("--tenants", type=int, default=4)
    parser.add_argument("--drain-timeout", type=float, default=600)
    parser.add_argument("--attempts", type=int, default=10)
    parser.add_argument("--expected-limit", type=int, default=10)
    args = parser.parse_args()
    refuse_remote(args.base)
    if args.scenario == "throughput":
        asyncio.run(
            throughput(
                args.base,
                args.tickets,
                args.concurrency,
                args.tenants,
                args.drain_timeout,
            )
        )
    else:
        asyncio.run(limits_scenario(args.base, args.attempts, args.expected_limit))


if __name__ == "__main__":
    main()
