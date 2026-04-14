from typing import List
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.mongo import get_db
from app.models.comment import Comment, CommentCreate

router = APIRouter()


@router.post(
    "/posts/{post_id}/comments",
    response_model=Comment,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    post_id: str,
    body: CommentCreate,
    collection=Depends(get_db),
):
    """Add a new comment to a post and return the created comment."""
    post = await collection.find_one({"_id": post_id})
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id '{post_id}' not found",
        )

    new_comment = {
        "commentId": str(uuid4()),
        "userId": body.userId,
        "username": body.username,
        "userProfilePictureUrl": body.userProfilePictureUrl,
        "text": body.text,
        "likes": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    await collection.update_one(
        {"_id": post_id},
        {"$push": {"comments": new_comment}},
    )

    return new_comment


@router.delete(
    "/posts/{post_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment(
    post_id: str,
    comment_id: str,
    collection=Depends(get_db),
):
    """Remove a comment from a post by commentId."""
    post = await collection.find_one({"_id": post_id})
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id '{post_id}' not found",
        )

    result = await collection.update_one(
        {"_id": post_id},
        {"$pull": {"comments": {"commentId": comment_id}}},
    )
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comment with id '{comment_id}' not found",
        )


@router.put(
    "/posts/{post_id}/comments/{comment_id}/likes",
    status_code=status.HTTP_200_OK,
)
async def like_comment(
    post_id: str,
    comment_id: str,
    collection=Depends(get_db),
):
    """Increment the like count on a comment by 1."""
    post = await collection.find_one({"_id": post_id})
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id '{post_id}' not found",
        )

    result = await collection.update_one(
        {"_id": post_id},
        {"$inc": {"comments.$[elem].likes": 1}},
        array_filters=[{"elem.commentId": comment_id}],
    )
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comment with id '{comment_id}' not found",
        )


@router.delete(
    "/posts/{post_id}/comments/{comment_id}/likes",
    status_code=status.HTTP_200_OK,
)
async def unlike_comment(
    post_id: str,
    comment_id: str,
    collection=Depends(get_db),
):
    """Decrement the like count on a comment by 1, floored at 0."""
    post = await collection.find_one({"_id": post_id})
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id '{post_id}' not found",
        )

    result = await collection.update_one(
        {"_id": post_id},
        {"$inc": {"comments.$[elem].likes": -1}},
        array_filters=[{"elem.commentId": comment_id, "elem.likes": {"$gt": 0}}],
    )
    if result.modified_count == 0:
        exists = await collection.find_one(
            {"_id": post_id, "comments.commentId": comment_id}
        )
        if exists is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comment with id '{comment_id}' not found",
            )
        # modified_count == 0 but comment exists: likes is already at 0, no-op is correct
