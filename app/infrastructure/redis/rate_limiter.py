# app/infrastructure/redis/rate_limiter.py
import time

import redis.asyncio as redis


class RedisRateLimiter:
    """Rate limiter using Redis for distributed rate limiting"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.prefix = "ratelimit:"

    async def is_rate_limited(
        self, key: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, dict]:
        """
        Check if request is rate limited using Redis.
        Returns: (is_limited, rate_limit_info)
        No HTTP exceptions - pure infrastructure logic.
        """
        redis_key = f"{self.prefix}{key}"
        current_time = int(time.time())
        window_start = current_time - window_seconds

        # Use Redis transaction for atomic operations
        async with self.redis.pipeline() as pipe:
            # Remove old entries
            await pipe.zremrangebyscore(redis_key, 0, window_start)
            # Count current requests
            await pipe.zcard(redis_key)
            # Add current request
            await pipe.zadd(redis_key, {str(current_time): current_time})
            # Set expiry on the key
            await pipe.expire(redis_key, window_seconds)

            results = await pipe.execute()
            current_count = results[1]  # zcard result

        is_limited = current_count >= max_requests
        remaining = max(0, max_requests - current_count)

        info = {
            "limit": max_requests,
            "remaining": remaining,
            "reset": window_start + window_seconds,
            "window": window_seconds,
            "current_usage": current_count,
        }

        return is_limited, info

    async def reset_limit(self, key: str):
        """Reset rate limit for a specific key"""
        redis_key = f"{self.prefix}{key}"
        await self.redis.delete(redis_key)
