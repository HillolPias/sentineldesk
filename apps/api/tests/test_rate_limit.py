from app.core.config import get_settings

SIGNUP = {"tenant_name": "T", "password": "testpass123"}
TICKET = {"subject": "S", "body": "b"}


async def test_ticket_cretaion_is_limited_per_workspace(
    client, make_tenant, make_ticket
):
    limit = get_settings().rate_limit_tickets_per_hour
    a = await make_tenant("Acme")
    b = await make_tenant("Globex")
    for _ in range(limit):
        await make_ticket(a)

    blocked = await client.post("/tickets", json=TICKET, headers=a)

    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0
    other = await client.post("/tickets", json=TICKET, headers=b)
    assert other.status_code == 201  # one workspace's burst doesn't affect another


async def test_limit_resets_after_the_window(
    client, make_tenant, make_ticket, fake_redis
):
    limit = get_settings().rate_limit_tickets_per_hour
    a = await make_tenant("Acme")
    for _ in range(limit):
        await make_ticket(a)
    assert (await client.post("/tickets", json=TICKET, headers=a)).status_code == 429

    fake_redis.advance(3601)

    assert (await client.post("/tickets", json=TICKET, headers=a)).status_code == 201


async def test_daily_cap_protects_the_llm_budget_accross_workspace(
    client, make_tenant, make_ticket, monkeypatch
):
    monkeypatch.setattr(get_settings(), "rate_limit_daily_ticket_cap", 2)
    a = await make_tenant("Acme")
    b = await make_tenant("Globex")
    await make_ticket(a)
    await make_ticket(b)

    resp = await client.post("/tickets", json=TICKET, headers=a)

    assert resp.status_code == 429
    assert "daily" in resp.json()["detail"]


async def test_signups_are_limited_per_ip(client):
    limit = get_settings().rate_limit_signups_per_hour_per_ip
    for i in range(limit):
        resp = await client.post(
            "/auth/signup", json={**SIGNUP, "email": f"u{i}@example.com"}
        )
        assert resp.status_code == 200

    resp = await client.post(
        "/auth/signup", json={**SIGNUP, "email": "extra@example.com"}
    )

    assert resp.status_code == 429


async def test_logins_are_limited_per_ip(client, make_tenant, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_logins_per_hour_per_ip", 3)
    await make_tenant("Acme", "a@acme.com")
    bad = {"email": "a@acme.com", "password": "wrong-password"}
    for _ in range(3):
        assert (await client.post("/auth/login", json=bad)).status_code == 401

    resp = await client.post("/auth/login", json=bad)

    assert resp.status_code == 429


async def test_oversized_ticket_is_rejected_before_any_llm_work(
    client, make_tenant, fake_redis
):
    headers = await make_tenant("Acme")

    resp = await client.post(
        "/tickets", json={"subject": "s", "body": "x" * 4001}, headers=headers
    )

    assert resp.status_code == 422
    assert fake_redis.enqueued == []
