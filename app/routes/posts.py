from typing import List, Optional
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.auth import get_current_user_id
from app.config import DEFAULT_PROFILE_PICTURE_URL
from app.db.mongo import get_db
from app.models.post import Post, PostUpdate
import app.services.users_client as users_client
from app.utils.images import delete_image, save_image, validate_image

router = APIRouter()


@router.get("/posts", response_model=List[Post], status_code=status.HTTP_200_OK)
async def get_posts(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Retrieve all posts."""
    docs = await db.find().to_list(None)
    for doc in docs:
        doc["postId"] = doc.pop("_id")
    return docs


@router.post("/posts", response_model=Post, status_code=status.HTTP_201_CREATED)
async def create_post(
    request: Request,
    caption: str = Form(...),
    image: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Create a new post attributed to the authenticated user."""
    username = await users_client.get_username(current_user_id)
    ext = validate_image(image)
    post_id = str(uuid4())
    filename = await save_image(image, post_id, ext)
    img_url = f"{request.base_url}uploads/{filename}"
    timestamp = datetime.now(timezone.utc).isoformat()
    document = {
        "_id": post_id,
        "userId": current_user_id,
        "username": username,
        "userProfilePictureUrl": DEFAULT_PROFILE_PICTURE_URL,
        "imgUrl": img_url,
        "caption": caption,
        "timestamp": timestamp,
        "likes": 0,
        "comments": [],
    }
    await db.insert_one(document)
    document["postId"] = document.pop("_id")
    return document


@router.get("/posts/{post_id}", response_model=Post, status_code=status.HTTP_200_OK)
async def get_post(post_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Retrieve a single post by its ID."""
    doc = await db.find_one({"_id": post_id})
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id '{post_id}' not found",
        )
    doc["postId"] = doc.pop("_id")
    return doc


@router.put("/posts/{post_id}", response_model=Post, status_code=status.HTTP_200_OK)
async def update_post(
    post_id: str,
    request: Request,
    caption: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Update caption and/or image of a post. Only the post owner may update it."""
    existing = await db.find_one({"_id": post_id})
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id '{post_id}' not found",
        )
    if existing["userId"] != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post",
        )

    fields: dict = {}

    if caption is not None:
        fields["caption"] = caption

    if image is not None and image.filename:
        ext = validate_image(image)
        old_url = existing.get("imgUrl", "")
        if "/uploads/" in old_url:
            delete_image(old_url.split("/uploads/")[-1])
        filename = await save_image(image, post_id, ext)
        fields["imgUrl"] = f"{request.base_url}uploads/{filename}"

    if not fields:
        existing["postId"] = existing.pop("_id")
        return existing

    doc = await db.find_one_and_update(
        {"_id": post_id},
        {"$set": fields},
        return_document=ReturnDocument.AFTER,
    )
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id '{post_id}' not found",
        )
    doc["postId"] = doc.pop("_id")
    return doc


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Delete a post. Only the post owner may delete it."""
    existing = await db.find_one({"_id": post_id})
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id '{post_id}' not found",
        )
    if existing["userId"] != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this post",
        )
    doc = await db.find_one_and_delete({"_id": post_id})
    if doc is None:
        return
    img_url = doc.get("imgUrl", "")
    if "/uploads/" in img_url:
        delete_image(img_url.split("/uploads/")[-1])


@router.put(
    "/posts/{post_id}/likes", response_model=Post, status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user_id)],
)
async def increment_likes(
    post_id: str, db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Increment the like count of a post by 1. Requires authentication."""
    doc = await db.find_one_and_update(
        {"_id": post_id},
        {"$inc": {"likes": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id '{post_id}' not found",
        )
    doc["postId"] = doc.pop("_id")
    return doc


@router.delete(
    "/posts/{post_id}/likes", response_model=Post, status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user_id)],
)
async def decrement_likes(
    post_id: str, db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Decrement the like count of a post by 1, floored at 0. Requires authentication."""
    doc = await db.find_one_and_update(
        {"_id": post_id, "likes": {"$gt": 0}},
        {"$inc": {"likes": -1}},
        return_document=ReturnDocument.AFTER,
    )
    if doc is None:
        exists = await db.find_one({"_id": post_id})
        if exists is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with id '{post_id}' not found",
            )
        exists["postId"] = exists.pop("_id")
        return exists
    doc["postId"] = doc.pop("_id")
    return doc
