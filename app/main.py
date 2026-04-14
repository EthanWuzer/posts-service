from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.db.mongo import lifespan
from app.routes.posts import router as posts_router
from app.routes.comments import router as comments_router
from app.utils.images import UPLOAD_DIR

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.include_router(posts_router)
app.include_router(comments_router)
