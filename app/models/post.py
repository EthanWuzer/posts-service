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
    likes: int = 0
    comments: List[Comment] = []


class PostCreate(BaseModel):
    caption: str


class PostUpdate(BaseModel):
    caption: Optional[str] = None
