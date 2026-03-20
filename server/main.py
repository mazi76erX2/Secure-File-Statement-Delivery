"""Description: Main entry point for the FastAPI application."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from api import api_router
from cache import redis_cache
from config import configure_logging, settings
from database import engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    await redis_cache.connect()
    yield
    await redis_cache.close()
    await engine.dispose()


app = FastAPI(
    title="Server API",
    description="An API for Secure File Statement Delivery.",
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=not settings.has_wildcard_cors,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.debug and settings.enable_debug_toolbar:
    from debug_toolbar.middleware import DebugToolbarMiddleware

    # Cast to Any because the third-party middleware has incomplete type hints.
    app.add_middleware(
        DebugToolbarMiddleware,  # type: ignore[arg-type]
        panels=["debug_toolbar.panels.sqlalchemy.SQLAlchemyPanel"],
    )

app.include_router(api_router)


def run() -> None:
    uvicorn.run("main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run()
