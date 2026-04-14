from pydantic import BaseModel


class Comment(BaseModel):
    commentId: str
    userId: str
    username: str
    userProfilePictureUrl: str
    text: str
    likes: int = 0
    timestamp: str


class CommentCreate(BaseModel):
    userId: str
    username: str
    userProfilePictureUrl: str
    text: str
