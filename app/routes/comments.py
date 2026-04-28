from typing import List
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user_id
from app.config import DEFAULT_PROFILE_PICTURE_URL
from app.db.mongo import get_db
from app.models.comment import Comment, CommentCreate
import app.services.users_client as users_client

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
    current_user_id: str = Depends(get_current_user_id),
):
    """Add a new comment attributed to the authenticated user."""
    post = await collection.find_one({"_id": post_id})
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id '{post_id}' not found",
        )

    username = await users_client.get_username(current_user_id)

    new_comment = {
        "commentId": str(uuid4()),
        "userId": current_user_id,
        "username": username,
        "userProfilePictureUrl": DEFAULT_PROFILE_PICTURE_URL,
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
    current_user_id: str = Depends(get_current_user_id),
):
    """Remove a comment. Only the comment author may delete it."""
    post = await collection.find_one({"_id": post_id})
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id '{post_id}' not found",
        )

    comment = next(
        (c for c in post.get("comments", []) if c["commentId"] == comment_id),
        None,
    )
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comment with id '{comment_id}' not found",
        )
    if comment["userId"] != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this comment",
        )

    await collection.update_one(
        {"_id": post_id},
        {"$pull": {"comments": {"commentId": comment_id}}},
    )


@router.put(
    "/posts/{post_id}/comments/{comment_id}/likes",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user_id)],
)
async def like_comment(
    post_id: str,
    comment_id: str,
    collection=Depends(get_db),
):
    """Increment the like count on a comment by 1. Requires authentication."""
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
    dependencies=[Depends(get_current_user_id)],
)
async def unlike_comment(
    post_id: str,
    comment_id: str,
    collection=Depends(get_db),
):
    """Decrement the like count on a comment by 1, floored at 0. Requires authentication."""
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
        # likes already 0, no-op is correct
