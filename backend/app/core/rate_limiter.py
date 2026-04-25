"""Async Token Bucket and Jitter Delay for API Rate Limiting"""

import asyncio
import logging
import random
import time
from functools import wraps
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class AsyncTokenBucket:
    """
    Async token bucket for rate limiting.

    Attributes:
        capacity: Maximum number of tokens in the bucket
        fill_rate: Number of tokens added per second
        tokens: Current number of available tokens
        last_fill: Last time tokens were calculated (timestamp)
    """

    def __init__(
        self,
        capacity: int = 10,
        fill_rate: float = 2.0,
        initial_tokens: Optional[float] = None,
    ):
        """
        Initialize the async token bucket.

        Args:
            capacity: Maximum tokens in bucket (default 10)
            fill_rate: Tokens added per second (default 2.0)
            initial_tokens: Starting tokens (default: capacity)
        """
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.tokens = (
            initial_tokens if initial_tokens is not None else capacity
        )
        self.last_fill = time.monotonic()
        self._lock = asyncio.Lock()

    async def _refill(self) -> None:
        """Refill tokens based on elapsed time"""
        now = time.monotonic()
        elapsed = now - self.last_fill
        new_tokens = elapsed * self.fill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_fill = now

    async def consume(
        self, tokens: float = 1.0, blocking: bool = True
    ) -> bool:
        """
        Consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume (default 1.0)
            blocking: If True, wait for tokens to become available.
                      If False, return immediately.

        Returns:
            True if tokens were consumed, False if not enough tokens
            and blocking=False
        """
        async with self._lock:
            await self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            if not blocking:
                return False

            # Calculate wait time for tokens to become available
            needed = tokens - self.tokens
            wait_time = needed / self.fill_rate

            # Wait for tokens
            logger.debug(f"Token bucket waiting {wait_time:.2f}s for tokens")
            await asyncio.sleep(wait_time)

            # Refill and consume
            await self._refill()
            self.tokens = max(0, self.tokens - tokens)
            return True

    async def get_available_tokens(self) -> float:
        """Get current number of available tokens"""
        async with self._lock:
            await self._refill()
            return self.tokens

    async def reset(self) -> None:
        """Reset the bucket to full capacity"""
        async with self._lock:
            self.tokens = self.capacity
            self.last_fill = time.monotonic()


def jitter_delay(
    jitter_min: float = 0.2,
    jitter_max: float = 1.5,
    token_bucket: Optional[AsyncTokenBucket] = None,
):
    """
    Decorator that adds random jitter delay to an async function.

    Optionally integrates with a token bucket for combined rate limiting.

    Args:
        jitter_min: Minimum delay in seconds (default 0.2)
        jitter_max: Maximum delay in seconds (default 1.5)
        token_bucket: Optional AsyncTokenBucket for rate limiting

    Usage:
        @jitter_delay(jitter_min=0.5, jitter_max=2.0)
        async def my_api_call():
            ...
    """
    if jitter_min > jitter_max:
        jitter_min, jitter_max = jitter_max, jitter_min

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Acquire token if bucket is provided
            if token_bucket is not None:
                await token_bucket.consume()

            # Add jitter delay
            delay = random.uniform(jitter_min, jitter_max)
            logger.debug(f"Jitter delay: {delay:.3f}s")
            await asyncio.sleep(delay)

            # Execute the function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


class JitterDelayDecorator:
    """
    Class-based jitter delay decorator for cleaner integration.
    Can be used as a dependency in FastAPI.
    """

    def __init__(
        self,
        jitter_min: float = 0.2,
        jitter_max: float = 1.5,
    ):
        self.jitter_min = jitter_min
        self.jitter_max = jitter_max

    def delay(self) -> float:
        """Generate a random delay"""
        return random.uniform(self.jitter_min, self.jitter_max)

    async def __call__(self, func: Callable) -> Callable:
        """Apply jitter delay to the decorated function"""

        @wraps(func)
        async def wrapper(*args, **kwargs):
            await asyncio.sleep(self.delay())
            return await func(*args, **kwargs)

        return wrapper


# Global token bucket for API rate limiting
_global_token_bucket: Optional[AsyncTokenBucket] = None


def get_token_bucket(
    capacity: int = 10,
    fill_rate: float = 2.0,
    reset: bool = False,
) -> AsyncTokenBucket:
    """
    Get or create the global token bucket instance.

    Args:
        capacity: Maximum tokens (requests per second * burst)
        fill_rate: Tokens per second
        reset: If True, reset the existing bucket

    Returns:
        The global AsyncTokenBucket instance
    """
    global _global_token_bucket
    if _global_token_bucket is None or reset:
        _global_token_bucket = AsyncTokenBucket(
            capacity=capacity,
            fill_rate=fill_rate,
        )
    return _global_token_bucket


async def reset_token_bucket() -> None:
    """Reset the global token bucket"""
    if _global_token_bucket is not None:
        await _global_token_bucket.reset()
