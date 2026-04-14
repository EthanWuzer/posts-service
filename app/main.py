from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.mongo import lifespan
from app.routes.posts import router as posts_router
from app.routes.comments import router as comments_router

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(posts_router)
app.include_router(comments_router)
