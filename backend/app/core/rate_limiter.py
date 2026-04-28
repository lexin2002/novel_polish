"""Async Token Bucket and Jitter Delay for API Rate Limiting"""

import asyncio
import logging
import random
import time
from typing import Optional

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
        while True:
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

                # Log at INFO if significant delay (> 3 seconds)
                if wait_time > 3:
                    logger.info(f"Rate limiter: waiting {wait_time:.2f}s for tokens")
                else:
                    logger.debug(f"Token bucket waiting {wait_time:.2f}s for tokens")

            # Sleep outside the lock so other coroutines can proceed
            await asyncio.sleep(wait_time)
            # Loop back: re-acquire lock, refill, and try again

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


