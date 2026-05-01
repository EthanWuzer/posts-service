from __future__ import annotations

import httpx
from fastapi import HTTPException, status

from app.config import USERS_SERVICE_API_KEY

# Populated by the app lifespan; None until then.
_client: httpx.AsyncClient | None = None


async def get_username(user_id: str) -> str:
    if _client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Users service client not initialized",
        )
    try:
        response = await _client.get(
            f"/api/user/{user_id}",
            headers={"X-Api-Key": USERS_SERVICE_API_KEY},
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Users service unavailable",
        )
    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )
    if not response.is_success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Users service error",
        )
    return response.json()["username"]


async def get_friends(user_id: str) -> list:
    if _client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Users service client not initialized",
        )
    try:
        response = await _client.get(
            f"/api/user/{user_id}/friends",
            headers={"X-Api-Key": USERS_SERVICE_API_KEY},
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Users service unavailable",
        )
    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )
    if not response.is_success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Users service error",
        )
    return response.json()
