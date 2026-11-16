from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import create_access_token, hash_password, verify_password
from app.core.config import get_settings
from app.core.rate_limit import hit
from app.core.stripe_client import create_customer
from app.db.models import Tenant, User
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    tenant_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/signup", response_model=TokenResponse)
async def signup(
    payload: SignupRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    settings = get_settings()
    ip = request.client.host if request.client else "unknown"
    await hit(
        request.app.state.redis,
        f"rl:signup:{ip}",
        settings.rate_limit_signups_per_hour_per_ip,
        3600,
        "Too many sign-ups from this IP address.",
    )

    taken = await db.execute(select(User.id).where(User.email == payload.email))
    if taken.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    tenant = Tenant(name=payload.tenant_name)
    db.add(tenant)
    await db.flush()  # assigns tenant.id without committing yet

    stripe_customer_id = await create_customer(payload.tenant_name, payload.email)
    tenant.stripe_customer_id = stripe_customer_id

    user = User(
        tenant_id=tenant.id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from None
    await db.refresh(user)

    token = create_access_token(user_id=str(user.id), tenant_id=str(tenant.id))
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    settings = get_settings()
    ip = request.client.host if request.client else "unknown"
    await hit(
        request.app.state.redis,
        f"rl:login:{ip}",
        settings.rate_limit_logins_per_hour_per_ip,
        3600,
        "Too many login attempts from this IP address.",
    )

    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user_id=str(user.id), tenant_id=str(user.tenant_id))
    return TokenResponse(access_token=token)
