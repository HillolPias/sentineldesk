from sqlalchemy import func, select

from app.db.models import Tenant
from app.db.session import async_session_factory


async def test_signup_returns_token_and_creates_stripe_customer(client):
    resp = await client.post(
        "/auth/signup",
        json={"tenant_name": "Acme", "email": "a@acme.com", "password": "testpass123"},
    )
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"


async def test_login_succeeds_with_correct_password(client, make_tenant):
    await make_tenant("Acme", "a@acme.com")
    resp = await client.post(
        "/auth/login", json={"email": "a@acme.com", "password": "testpass123"}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_fails_with_wrong_password(client, make_tenant):
    await make_tenant("Acme", "a@acme.com")
    resp = await client.post(
        "/auth/login", json={"email": "a@acme.com", "password": "wrongpass"}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"


async def test_login_error_does_not_reveal_whether_email_exists(client, make_tenant):
    await make_tenant("Acme", "a@acme.com")
    wrong_password = await client.post(
        "/auth/login", json={"email": "a@acme.com", "password": "nope"}
    )
    unknown_email = await client.post(
        "/auth/login", json={"email": "ghost@acme.com", "password": "nope"}
    )
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


async def test_protected_routes_reject_missing_token(client):
    assert (await client.get("/tickets")).status_code == 401
    assert (await client.get("/billing/summary")).status_code == 401


async def test_protected_routes_reject_garbage_token(client):
    resp = await client.get("/tickets", headers={"Authorization": "Bearer not.a.jwt"})
    assert resp.status_code == 401


async def test_very_long_password_does_not_crash(client):
    resp = await client.post(
        "/auth/signup",
        json={"tenant_name": "Acme", "email": "long@acme.com", "password": "x" * 200},
    )
    assert resp.status_code == 200


async def test_signup_with_an_existing_email_returns_409_without_creating_a_tenant(
    client, make_tenant
):
    await make_tenant("Acme", "a@acme.com")

    resp = await client.post(
        "/auth/signup",
        json={"tenant_name": "Other", "email": "a@acme.com", "password": "testpass123"},
    )

    assert resp.status_code == 409
    async with async_session_factory() as db:
        count = (
            await db.execute(select(func.count()).select_from(Tenant))
        ).scalar_one()
    assert count == 1


async def test_emails_are_case_insensitive(client, make_tenant):
    await make_tenant("Acme", "a@acme.com")

    duplicate = await client.post(
        "/auth/signup",
        json={"tenant_name": "Other", "email": "A@Acme.com", "password": "testpass123"},
    )
    login = await client.post(
        "/auth/login", json={"email": "A@ACME.COM", "password": "testpass123"}
    )

    assert duplicate.status_code == 409
    assert login.status_code == 200
