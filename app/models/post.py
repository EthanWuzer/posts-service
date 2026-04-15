from typing import List, Optional
from pydantic import BaseModel
from app.models.comment import Comment


class Post(BaseModel):
    postId: str
    userId: str
    username: str
    userProfilePictureUrl: str
    imgUrl: str
    caption: str
    timestamp: str
    likedBy: List[str] = []
    comments: List[Comment] = []


class PostCreate(BaseModel):
    username: str
    userProfilePictureUrl: str
    caption: str


class PostUpdate(BaseModel):
    caption: Optional[str] = None
