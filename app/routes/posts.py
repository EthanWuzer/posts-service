from typing import List, Optional
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.db.mongo import get_db
from app.dependencies.auth import get_current_user_id
from app.models.post import Post, PostUpdate
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
    username: str = Form(...),
    userProfilePictureUrl: str = Form(...),
    caption: str = Form(...),
    image: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Create a new post. userId is taken from the JWT; accepts a JPEG or PNG image."""
    ext = validate_image(image)
    post_id = str(uuid4())
    img_url = await save_image(image, post_id, ext)
    timestamp = datetime.now(timezone.utc).isoformat()
    document = {
        "_id": post_id,
        "userId": current_user_id,
        "username": username,
        "userProfilePictureUrl": userProfilePictureUrl,
        "imgUrl": img_url,
        "caption": caption,
        "timestamp": timestamp,
        "likedBy": [],
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
    caption: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Update caption and/or image of a post. Only the post owner may update."""
    existing = await db.find_one({"_id": post_id})
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id '{post_id}' not found",
        )
    if existing["userId"] != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this post",
        )

    fields: dict = {}

    if caption is not None:
        fields["caption"] = caption

    if image is not None and image.filename:
        ext = validate_image(image)
        old_url = existing.get("imgUrl", "")
        if old_url:
            delete_image(old_url)
        fields["imgUrl"] = await save_image(image, post_id, ext)

    if not fields:
        existing["postId"] = existing.pop("_id")
        return existing

    doc = await db.find_one_and_update(
        {"_id": post_id},
        {"$set": fields},
        return_document=ReturnDocument.AFTER,
    )
    doc["postId"] = doc.pop("_id")
    return doc


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Delete a post by its ID. Only the post owner may delete."""
    doc = await db.find_one({"_id": post_id})
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id '{post_id}' not found",
        )
    if doc["userId"] != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this post",
        )
    await db.find_one_and_delete({"_id": post_id})
    img_url = doc.get("imgUrl", "")
    if img_url:
        delete_image(img_url)


@router.put(
    "/posts/{post_id}/likes", response_model=Post, status_code=status.HTTP_200_OK
)
async def like_post(
    post_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Add the current user to the post's likedBy list. Idempotent."""
    doc = await db.find_one_and_update(
        {"_id": post_id},
        {"$addToSet": {"likedBy": current_user_id}},
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
    "/posts/{post_id}/likes", response_model=Post, status_code=status.HTTP_200_OK
)
async def unlike_post(
    post_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Remove the current user from the post's likedBy list. Idempotent."""
    doc = await db.find_one_and_update(
        {"_id": post_id},
        {"$pull": {"likedBy": current_user_id}},
        return_document=ReturnDocument.AFTER,
    )
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id '{post_id}' not found",
        )
    doc["postId"] = doc.pop("_id")
    return doc
