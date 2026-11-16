import math

from fastapi import HTTPException, status


def _human(seconds: int) -> str:
    if seconds >= 3600:
        return f"{math.ceil(seconds / 3600)} h"
    return f"{max(1, math.ceil(seconds / 60))} min"


async def hit(redis, key: str, limit: int, window_seconds: int, message: str) -> None:
    """Fixed-window counter in Redis. Raises HTTP 429 once `limit` is exceeded."""
    # SET NX EX creates the key together with its TTL, so a crash between two
    # separate commands can never leave a counter that never expires.
    await redis.set(key, 0, ex=window_seconds, nx=True)
    count = await redis.incr(key)
    if count > limit:
        retry_after = await redis.ttl(key)
        if retry_after < 1:
            retry_after = window_seconds
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"{message} Try again in about {_human(retry_after)}.",
            headers={"Retry-After": str(retry_after)},
        )
