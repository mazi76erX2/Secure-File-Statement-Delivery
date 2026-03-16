"""
Description: This file contains the RedisCache class which is used to
interact with the Redis cache.
"""

import redis.asyncio as redis
from config import settings


class RedisCache:
    """Redis cache class"""

    def __init__(self, url: str):
        self.url = url
        self.redis: redis.Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis"""
        self.redis = redis.from_url(self.url, encoding="utf-8", decode_responses=True)

    async def close(self) -> None:
        """Close the Redis connection"""
        if self.redis:
            await self.redis.close()

    async def get(self, key: str) -> str | None:
        """Get value from Redis cache"""
        if self.redis:
            return await self.redis.get(key)
        return None

    async def set(self, key: str, value: str, expire: int = 3600) -> None:
        """Set value in Redis cache"""
        if self.redis:
            await self.redis.set(key, value, ex=expire)

    async def delete(self, key: str) -> None:
        """Delete value from Redis cache"""
        if self.redis:
            await self.redis.delete(key)


redis_cache = RedisCache(settings.redis_url)
