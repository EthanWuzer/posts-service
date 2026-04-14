from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import MONGO_URI

client = None
db = None


@asynccontextmanager
async def lifespan(app):
    global client, db
    client = AsyncIOMotorClient(MONGO_URI)
    db = client["posts_db"]
    yield
    client.close()


def get_db():
    return db["posts"]
