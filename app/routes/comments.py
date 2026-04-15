from uuid import uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.mongo import get_db
from app.dependencies.auth import get_current_user_id
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
    current_user_id: str = Depends(get_current_user_id),
):
    """Add a new comment to a post. userId is taken from the JWT."""
    post = await collection.find_one({"_id": post_id})
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id '{post_id}' not found",
        )

    new_comment = {
        "commentId": str(uuid4()),
        "userId": current_user_id,
        "username": body.username,
        "userProfilePictureUrl": body.userProfilePictureUrl,
        "text": body.text,
        "likedBy": [],
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
    """Remove a comment from a post. Only the comment author may delete."""
    post = await collection.find_one({"_id": post_id})
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id '{post_id}' not found",
        )

    comment = next(
        (c for c in post.get("comments", []) if c["commentId"] == comment_id), None
    )
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comment with id '{comment_id}' not found",
        )
    if comment["userId"] != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this comment",
        )

    await collection.update_one(
        {"_id": post_id},
        {"$pull": {"comments": {"commentId": comment_id}}},
    )


@router.put(
    "/posts/{post_id}/comments/{comment_id}/likes",
    status_code=status.HTTP_200_OK,
)
async def like_comment(
    post_id: str,
    comment_id: str,
    collection=Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Add the current user to a comment's likedBy list. Idempotent."""
    post = await collection.find_one({"_id": post_id})
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id '{post_id}' not found",
        )

    comment = next(
        (c for c in post.get("comments", []) if c["commentId"] == comment_id), None
    )
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comment with id '{comment_id}' not found",
        )

    await collection.update_one(
        {"_id": post_id},
        {"$addToSet": {"comments.$[elem].likedBy": current_user_id}},
        array_filters=[{"elem.commentId": comment_id}],
    )


@router.delete(
    "/posts/{post_id}/comments/{comment_id}/likes",
    status_code=status.HTTP_200_OK,
)
async def unlike_comment(
    post_id: str,
    comment_id: str,
    collection=Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Remove the current user from a comment's likedBy list. Idempotent."""
    post = await collection.find_one({"_id": post_id})
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id '{post_id}' not found",
        )

    comment = next(
        (c for c in post.get("comments", []) if c["commentId"] == comment_id), None
    )
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comment with id '{comment_id}' not found",
        )

    await collection.update_one(
        {"_id": post_id},
        {"$pull": {"comments.$[elem].likedBy": current_user_id}},
        array_filters=[{"elem.commentId": comment_id}],
    )
