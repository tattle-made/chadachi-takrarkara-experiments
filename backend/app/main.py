from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.db import engine, init_db
from app.services.queue import run_queue


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    """Startup: set up the DB, then run the email queue until shutdown."""
    with Session(engine) as session:
        init_db(session)
    async with run_queue():
        yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)
if settings.ENVIRONMENT == "production":
    app.frontend("/", directory="dist", fallback="index.html")
