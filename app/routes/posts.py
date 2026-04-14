from typing import List, Optional
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.db.mongo import get_db
from app.models.post import Post, PostUpdate
from app.utils.images import delete_image, get_image_url, save_image, validate_image

router = APIRouter()


@router.get("/posts", response_model=List[Post], status_code=status.HTTP_200_OK)
async def get_posts(
    userId: Optional[List[str]] = Query(default=None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Retrieve all posts. Pass one or more `userId` query params to filter by user(s)."""
    query = {"userId": {"$in": userId}} if userId else {}
    docs = await db.find(query).to_list(None)
    for doc in docs:
        doc["postId"] = doc.pop("_id")
    return docs


@router.post("/posts", response_model=Post, status_code=status.HTTP_201_CREATED)
async def create_post(
    userId: str = Form(...),
    username: str = Form(...),
    userProfilePictureUrl: str = Form(...),
    caption: str = Form(...),
    image: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Create a new post with a server-generated postId and timestamp. Accepts a JPEG or PNG image."""
    ext = validate_image(image)
    post_id = str(uuid4())
    filename = await save_image(image, post_id, ext)
    img_url = get_image_url(filename)
    timestamp = datetime.now(timezone.utc).isoformat()
    document = {
        "_id": post_id,
        "userId": userId,
        "username": username,
        "userProfilePictureUrl": userProfilePictureUrl,
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
    caption: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Update caption and/or image of a post. Supply only the fields to change."""
    fields: dict = {}

    if caption is not None:
        fields["caption"] = caption

    if image is not None and image.filename:
        ext = validate_image(image)
        existing = await db.find_one({"_id": post_id})
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with id '{post_id}' not found",
            )
        old_url = existing.get("imgUrl", "")
        if "/uploads/" in old_url:
            delete_image(old_url.split("/uploads/")[-1])
        filename = await save_image(image, post_id, ext)
        fields["imgUrl"] = get_image_url(filename)

    if not fields:
        doc = await db.find_one({"_id": post_id})
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with id '{post_id}' not found",
            )
        doc["postId"] = doc.pop("_id")
        return doc

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
async def delete_post(post_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Delete a post by its ID and remove the associated image from disk."""
    doc = await db.find_one_and_delete({"_id": post_id})
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id '{post_id}' not found",
        )
    img_url = doc.get("imgUrl", "")
    if "/uploads/" in img_url:
        delete_image(img_url.split("/uploads/")[-1])


@router.put(
    "/posts/{post_id}/likes", response_model=Post, status_code=status.HTTP_200_OK
)
async def increment_likes(
    post_id: str, db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Increment the like count of a post by 1."""
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
    "/posts/{post_id}/likes", response_model=Post, status_code=status.HTTP_200_OK
)
async def decrement_likes(
    post_id: str, db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Decrement the like count of a post by 1, floored at 0."""
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
