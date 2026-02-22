"""FastAPI application factory for the memBlocks backend."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from backend.src.api.routers import blocks, chat, memory, users
from backend.src.api.dependencies import get_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan: startup and graceful shutdown."""
    # Eagerly initialise the client so connection errors surface at startup.
    get_client()
    yield
    # Graceful shutdown — close MongoDB connections.
    client = get_client()
    await client.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="memBlocks API",
        description="Intelligent memory management system for LLMs",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(users.router)
    app.include_router(blocks.router)
    app.include_router(chat.router)
    app.include_router(memory.router)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.src.api.main:app", host="0.0.0.0", port=8001, reload=True)
