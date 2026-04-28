from __future__ import annotations

import jwt
from fastapi import HTTPException, Request, status

from app.config import JWT_AUDIENCE, JWT_ISSUER, JWT_PUBLIC_KEY_PATH

_public_key: str | None = None


def _load_public_key() -> str:
    global _public_key
    if _public_key is None:
        if not JWT_PUBLIC_KEY_PATH:
            raise RuntimeError("JWT_PUBLIC_KEY_PATH is not configured")
        with open(JWT_PUBLIC_KEY_PATH) as f:
            _public_key = f.read()
    return _public_key


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
        public_key = _load_public_key()
    except (RuntimeError, OSError):
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
    user_id: str | None = payload.get("nameid")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identity claim",
        )
    return user_id
