"""FastAPI application entrypoint.

Run locally:
    uvicorn gravekeeper.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import get_settings

app = FastAPI(
    title="GraveKeeper Scanner",
    description="Read-only inventory of non-human identities, with zombie scoring.",
    version="0.1.0",
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root() -> dict:
    return {
        "name": "GraveKeeper Scanner",
        "status": "ok",
        "docs": "/docs",
    }
