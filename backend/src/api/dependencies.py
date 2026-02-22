"""FastAPI dependency injection — provides a shared MemBlocksClient instance."""

from functools import lru_cache
from memblocks import MemBlocksClient, MemBlocksConfig


@lru_cache(maxsize=1)
def get_config() -> MemBlocksConfig:
    """Return (and cache) the MemBlocksConfig instance read from .env."""
    return MemBlocksConfig()


@lru_cache(maxsize=1)
def get_client() -> MemBlocksClient:
    """Return (and cache) the shared MemBlocksClient instance."""
    config = get_config()
    return MemBlocksClient(config)


__all__ = ["get_config", "get_client"]
