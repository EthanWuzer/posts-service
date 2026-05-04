from __future__ import annotations

import asyncio

import httpx
from fastapi import HTTPException, status

from app.config import DEFAULT_PROFILE_PICTURE_URL, USERS_SERVICE_API_KEY

# Populated by the app lifespan; None until then.
_client: httpx.AsyncClient | None = None


async def get_user(user_id: str) -> dict | None:
    """Returns {username, profilePicUrl} or None on 404. Raises on transport/auth errors."""
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
        return None
    if not response.is_success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Users service error",
        )
    body = response.json()
    return {
        "username": body.get("username", ""),
        "profilePicUrl": body.get("profilePicUrl") or DEFAULT_PROFILE_PICTURE_URL,
    }


async def get_users(user_ids: list[str]) -> dict[str, dict]:
    """Parallel deduped batch lookup. Returns {user_id: {username, profilePicUrl}}.
    Missing users (404) and fetch errors get a placeholder dict so responses always serialize."""
    unique = list({uid for uid in user_ids if uid})
    if not unique:
        return {}
    results = await asyncio.gather(*(get_user(uid) for uid in unique), return_exceptions=True)
    placeholder = {"username": "[unknown user]", "profilePicUrl": DEFAULT_PROFILE_PICTURE_URL}
    return {
        uid: (r if isinstance(r, dict) else placeholder)
        for uid, r in zip(unique, results)
    }


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
