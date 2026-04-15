from typing import List

from pydantic import BaseModel


class Comment(BaseModel):
    commentId: str
    userId: str
    username: str
    userProfilePictureUrl: str
    text: str
    likedBy: List[str] = []
    timestamp: str


class CommentCreate(BaseModel):
    username: str
    userProfilePictureUrl: str
    text: str
