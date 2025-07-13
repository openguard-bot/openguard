"""Asynchronous Redis cache utilities for the database layer."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional
from datetime import datetime

import redis.asyncio as redis

log = logging.getLogger(__name__)

# Global Redis client
_redis: Optional[redis.Redis] = None
_redis_unavailable: bool = False


class RedisConfig:
    """Configuration for connecting to Redis from environment variables."""

    def __init__(self) -> None:
        self.url = os.getenv("REDIS_URL")
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", "6379"))
        self.password = os.getenv("REDIS_PASSWORD")

    def get_connection_kwargs(self) -> dict[str, Any]:
        if self.url:
            return {"url": self.url}
        return {
            "host": self.host,
            "port": self.port,
            "password": self.password,
        }


async def get_redis() -> Optional[redis.Redis]:
    """
    Get the global Redis connection.
    If the connection fails, it will log a warning and return None.
    Subsequent calls will not attempt to reconnect.
    """
    global _redis, _redis_unavailable

    if _redis_unavailable:
        return None

    if _redis is None:
        config = RedisConfig()
        try:
            # Add a timeout to the connection attempt to avoid long hangs
            log.info("Attempting to connect to Redis...")
            _redis = redis.Redis(
                **config.get_connection_kwargs(), socket_connect_timeout=1
            )
            await _redis.ping()
            log.info("Successfully connected to Redis.")
        except Exception as exc:
            log.warning(
                "Could not connect to Redis: %s. The bot will run without caching.",
                exc,
            )
            _redis = None
            _redis_unavailable = True

    return _redis


async def close_redis() -> None:
    """Close the global Redis connection and reset the unavailable flag."""
    global _redis, _redis_unavailable

    if _redis:
        await _redis.close()
        _redis = None
        log.info("Redis connection closed.")
    _redis_unavailable = False


async def get_cache(key: str) -> Any:
    """Retrieve a value from Redis and decode JSON if applicable."""
    client = await get_redis()
    if client is None:
        return None
    raw = await client.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


async def set_cache(key: str, value: Any, expire: int | None = None) -> None:
    """Set a value in Redis, encoding it as JSON if needed."""
    client = await get_redis()
    if client is None:
        return
    def datetime_converter(o):
        if isinstance(o, datetime):
            return o.isoformat()
    data = json.dumps(value, default=datetime_converter)
    await client.set(key, data, ex=expire)


async def delete_cache(key: str) -> None:
    """Delete a cached value from Redis."""
    client = await get_redis()
    if client is None:
        return
    await client.delete(key)


async def get_redis_client() -> Optional[redis.Redis]:
    """Returns the raw Redis client."""
    return await get_redis()
