from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import app.services.users_client as _users_client
from app.config import CORS_ALLOW_ORIGINS, USERS_SERVICE_BASE_URL
from app.db.mongo import lifespan as _db_lifespan
from app.routes.comments import router as comments_router
from app.routes.posts import router as posts_router
from app.utils.images import UPLOAD_DIR

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app_instance):
    _users_client._client = httpx.AsyncClient(
        base_url=USERS_SERVICE_BASE_URL, timeout=5.0
    )
    async with _db_lifespan(app_instance):
        try:
            yield
        finally:
            await _users_client._client.aclose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.include_router(posts_router)
app.include_router(comments_router)
