from __future__ import annotations

import httpx
import jwt
from fastapi import HTTPException, Request, status

import app.services.users_client as users_client
from app.config import JWT_AUDIENCE, JWT_ISSUER, USERS_SERVICE_API_KEY

_public_key: str | None = None


async def _fetch_public_key() -> str:
    global _public_key
    if _public_key is not None:
        return _public_key
    client = users_client._client
    if client is None:
        raise RuntimeError("Users service client not initialized")
    if not USERS_SERVICE_API_KEY:
        raise RuntimeError("USERS_SERVICE_API_KEY is not configured")
    response = await client.get(
        "/api/auth/jwt-key",
        headers={"X-Api-Key": USERS_SERVICE_API_KEY},
    )
    response.raise_for_status()
    _public_key = response.json()["jwtKey"]
    return _public_key


async def get_optional_user_id(request: Request) -> str | None:
    has_creds = (
        request.headers.get("Authorization", "").startswith("Bearer ")
        or "jwt" in request.cookies
    )
    if not has_creds:
        return None
    return await get_current_user_id(request)


async def get_current_user_id(request: Request) -> str:
    token: str | None = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
    if not token:
        token = request.cookies.get("jwt")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        public_key = await _fetch_public_key()
    except (RuntimeError, httpx.HTTPError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication configuration error",
        )
    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identity claim",
        )
    return user_id
