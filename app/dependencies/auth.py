from typing import Optional

import jwt
import httpx
from fastapi import Header, HTTPException, status

from app.config import AUTH_SERVICE_URL

_public_key_cache: str | None = None


async def _get_public_key() -> str:
    global _public_key_cache
    if _public_key_cache is None:
        if not AUTH_SERVICE_URL:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AUTH_SERVICE_URL is not configured",
            )
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{AUTH_SERVICE_URL}/public-key")
            r.raise_for_status()
            _public_key_cache = r.text
    return _public_key_cache


async def get_current_user_id(authorization: Optional[str] = Header(default=None)) -> str:
    """Extract and verify the JWT from the Authorization header. Returns the userId (sub claim)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = authorization.removeprefix("Bearer ")
    try:
        public_key = await _get_public_key()
        payload = jwt.decode(token, public_key, algorithms=["RS256"])
        return payload["sub"]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
