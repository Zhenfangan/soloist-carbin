"""Soloist Cabin Pro — FastAPI 后端入口"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.routes.review_routes import router as review_router
from server.routes.sync_routes import router as sync_router

app = FastAPI(title="Soloist Cabin Pro Server", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sync_router, prefix="/api/v1")
app.include_router(review_router, prefix="/api/v1")
