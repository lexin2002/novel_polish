import asyncio
import time
import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class AsyncTokenBucket:
    """
    An asynchronous token bucket for rate limiting.
    Implements the token bucket algorithm to control request rates.
    """
    def __init__(self, capacity: float, fill_rate: float):
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.tokens = capacity
        self.last_fill = time.monotonic()
        self._lock = asyncio.Lock()

    async def consume(self, tokens: float = 1.0):
        """
        Consume tokens from the bucket. If not enough tokens, wait until they are available.
        """
        async with self._lock:
            while True:
                now = time.monotonic()
                # Fill tokens based on elapsed time
                elapsed = now - self.last_fill
                self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
                self.last_fill = now

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
                
                # Wait for enough tokens to be filled
                wait_time = (tokens - self.tokens) / self.fill_rate
                await asyncio.sleep(wait_time)

class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.
    States: CLOSED (normal), OPEN (blocked), HALF_OPEN (testing recovery).
    """
    def __init__(self, threshold: int = 3, recovery_timeout: float = 30.0):
        self.threshold = threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"
        self._lock = asyncio.Lock()

    async def call(self, func, *args, **kwargs):
        """
        Execute a function wrapped in the circuit breaker.
        """
        async with self._lock:
            if self.state == "OPEN":
                if time.monotonic() - self.last_failure_time >= self.recovery_timeout:
                    logger.info("[CircuitBreaker] Transitioning to HALF_OPEN to test recovery.")
                    self.state = "HALF_OPEN"
                else:
                    raise Exception("Circuit breaker is OPEN. Requests are blocked to allow recovery.")

            try:
                result = await func(*args, **kwargs)
                # Success: Reset circuit
                if self.state == "HALF_OPEN":
                    logger.info("[CircuitBreaker] Recovery successful. Transitioning to CLOSED.")
                self.state = "CLOSED"
                self.failure_count = 0
                return result
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.monotonic()
                logger.warning(f"[CircuitBreaker] Failure {self.failure_count}/{self.threshold}: {e}")
                
                if self.failure_count >= self.threshold:
                    logger.error("[CircuitBreaker] Threshold reached. Transitioning to OPEN state.")
                    self.state = "OPEN"
                
                raise e
