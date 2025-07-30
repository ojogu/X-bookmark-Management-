# redis_client.py
import json
import redis.asyncio as redis
from typing import Optional
from src.utils.config import config
REDIS_HOST = config.REDIS_HOST
REDIS_PORT = config.REDIS_PORT
CACHE_TTL = 3600  # 1 hour
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"

_redis: Optional[redis.Redis] = None

async def setup_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis

async def get_redis() -> redis.Redis:
    if _redis is None:
        raise RuntimeError("Redis has not been initialized. Call setup_redis() first.")
    return _redis


async def get_or_fetch_cache(
    key: str,
    ttl: int,
    fetch_callback: callable  # async function to fetch fresh data
):
    redis = await get_redis()

    cached = await redis.get(key)
    if cached:
        return json.loads(cached)

    # If not found or expired, fetch new data
    fresh = await fetch_callback()
    await redis.set(key, json.dumps(fresh), ex=ttl)
    return fresh