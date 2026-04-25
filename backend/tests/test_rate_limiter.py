"""Tests for Rate Limiter (Async Token Bucket and Jitter Delay)"""

import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from app.core.rate_limiter import (
    AsyncTokenBucket,
    JitterDelayDecorator,
    get_token_bucket,
    jitter_delay,
    reset_token_bucket,
)


class TestAsyncTokenBucket:
    """Test AsyncTokenBucket basic operations"""

    @pytest.mark.asyncio
    async def test_bucket_starts_with_capacity(self):
        """Test that bucket starts with initial tokens equal to capacity"""
        bucket = AsyncTokenBucket(capacity=5, fill_rate=1.0)
        tokens = await bucket.get_available_tokens()
        assert tokens == 5

    @pytest.mark.asyncio
    async def test_consume_reduces_tokens(self):
        """Test that consume reduces available tokens"""
        bucket = AsyncTokenBucket(capacity=5, fill_rate=1.0, initial_tokens=5)
        await bucket.consume(2)
        tokens = await bucket.get_available_tokens()
        assert 2.99 < tokens < 3.01  # Allow small floating point variance

    @pytest.mark.asyncio
    async def test_consume_non_blocking_returns_false(self):
        """Test that non-blocking consume returns False when insufficient tokens"""
        bucket = AsyncTokenBucket(capacity=5, fill_rate=1.0, initial_tokens=2)
        result = await bucket.consume(3, blocking=False)
        assert result is False

    @pytest.mark.asyncio
    async def test_consume_blocking_waits_for_tokens(self):
        """Test that blocking consume waits until tokens available"""
        bucket = AsyncTokenBucket(capacity=5, fill_rate=10.0, initial_tokens=0)
        start = time.monotonic()
        await bucket.consume(3, blocking=True)
        elapsed = time.monotonic() - start
        # Should wait ~0.3s for 3 tokens at rate 10/s
        assert elapsed >= 0.25  # Allow some margin

    @pytest.mark.asyncio
    async def test_refill_adds_tokens_over_time(self):
        """Test that tokens are refilled based on fill rate"""
        bucket = AsyncTokenBucket(capacity=10, fill_rate=10.0, initial_tokens=0)
        await asyncio.sleep(0.1)  # Wait 0.1s
        tokens = await bucket.get_available_tokens()
        # Should have ~1 token (0.1s * 10/s)
        assert 0.5 < tokens < 2.0

    @pytest.mark.asyncio
    async def test_tokens_capped_at_capacity(self):
        """Test that tokens don't exceed capacity"""
        bucket = AsyncTokenBucket(capacity=5, fill_rate=100.0, initial_tokens=5)
        await asyncio.sleep(0.1)  # Wait long enough to add 10 tokens
        tokens = await bucket.get_available_tokens()
        assert tokens <= 5  # Should be capped at capacity

    @pytest.mark.asyncio
    async def test_reset_restores_full_capacity(self):
        """Test that reset restores tokens to full capacity"""
        bucket = AsyncTokenBucket(capacity=5, fill_rate=1.0, initial_tokens=2)
        await bucket.consume(2)  # Use all tokens
        await bucket.reset()
        tokens = await bucket.get_available_tokens()
        assert tokens == 5


class TestJitterDelay:
    """Test jitter delay decorator"""

    @pytest.mark.asyncio
    async def test_jitter_delay_adds_random_delay(self):
        """Test that decorator adds delay between min and max"""
        delays = []

        @jitter_delay(jitter_min=0.05, jitter_max=0.1)
        async def my_func():
            delays.append(time.monotonic())
            return "done"

        start = time.monotonic()
        await my_func()
        elapsed = time.monotonic() - start

        assert 0.04 < elapsed < 0.15

    @pytest.mark.asyncio
    async def test_jitter_delay_with_token_bucket(self):
        """Test jitter delay combined with token bucket"""
        bucket = AsyncTokenBucket(capacity=1, fill_rate=10.0, initial_tokens=1)

        @jitter_delay(jitter_min=0.01, jitter_max=0.02, token_bucket=bucket)
        async def my_func():
            return "done"

        start = time.monotonic()
        await my_func()
        elapsed = time.monotonic() - start

        # Should have some delay from jitter + very small from token
        assert elapsed >= 0.01


class TestJitterDelayDecoratorClass:
    """Test JitterDelayDecorator class"""

    def test_delay_generates_value_in_range(self):
        """Test that delay() generates value in correct range"""
        decorator = JitterDelayDecorator(jitter_min=0.1, jitter_max=0.2)
        delays = [decorator.delay() for _ in range(100)]

        assert all(0.1 <= d <= 0.2 for d in delays)

    def test_delay_has_some_variance(self):
        """Test that delay generates varying values"""
        decorator = JitterDelayDecorator(jitter_min=0.1, jitter_max=0.3)
        delays = [decorator.delay() for _ in range(50)]

        # At least some should be different
        unique_delays = set(delays)
        assert len(unique_delays) > 1


class TestConcurrentRateLimiting:
    """Test concurrent rate limiting behavior"""

    @pytest.mark.asyncio
    async def test_concurrent_requests_are_rate_limited(self):
        """Test that concurrent requests respect rate limiting"""
        # Create bucket with capacity 2, fill rate 2/s
        bucket = AsyncTokenBucket(capacity=2, fill_rate=2.0, initial_tokens=2)
        results = []
        start = time.monotonic()

        async def my_task(task_id: int):
            await bucket.consume()
            results.append(task_id)
            return task_id

        # Start 5 concurrent tasks
        tasks = [my_task(i) for i in range(5)]
        await asyncio.gather(*tasks)

        elapsed = time.monotonic() - start

        # First 2 should be immediate (bucket had 2 tokens)
        # Next 3 should wait ~0.5s each (2s fill rate = 0.5s per token)
        # Total should be at least 1.5s (3 tokens * 0.5s)
        assert elapsed >= 1.4  # Allow some margin

    @pytest.mark.asyncio
    async def test_token_bucket_handles_burst(self):
        """Test that bucket handles burst of requests"""
        bucket = AsyncTokenBucket(capacity=5, fill_rate=1.0, initial_tokens=5)

        # All 5 should complete quickly (burst capacity)
        start = time.monotonic()
        tasks = [bucket.consume(1, blocking=True) for _ in range(5)]
        await asyncio.gather(*tasks)
        elapsed = time.monotonic() - start

        # All 5 tokens available immediately, so should be fast
        assert elapsed < 0.1  # Negligible time for burst

    @pytest.mark.asyncio
    async def test_token_bucket_sustained_rate(self):
        """Test that bucket enforces sustained rate over time"""
        bucket = AsyncTokenBucket(capacity=3, fill_rate=3.0, initial_tokens=3)
        start = time.monotonic()

        # Make 6 requests (3 immediately available, 3 must wait for refill)
        for i in range(6):
            await bucket.consume()
            # Each consumes 1 token, refill adds 3/s = 1 token per 0.333s
            # After 3 initial tokens, should wait ~0.333s for each remaining

        elapsed = time.monotonic() - start

        # 3 initial tokens used immediately
        # 3 more need to wait for refill: 3 * 0.333s = 1s total
        # Plus some overhead, should be roughly 1s+
        assert elapsed >= 0.9


class TestGlobalTokenBucket:
    """Test global token bucket singleton"""

    @pytest.mark.asyncio
    async def test_get_token_bucket_creates_singleton(self):
        """Test that get_token_bucket returns same instance"""
        await reset_token_bucket()
        bucket1 = get_token_bucket(capacity=5, fill_rate=2.0)
        bucket2 = get_token_bucket(capacity=5, fill_rate=2.0)
        assert bucket1 is bucket2

    @pytest.mark.asyncio
    async def test_get_token_bucket_reset(self):
        """Test that reset parameter creates new instance"""
        await reset_token_bucket()
        bucket1 = get_token_bucket(capacity=5, fill_rate=2.0)
        bucket2 = get_token_bucket(capacity=5, fill_rate=2.0, reset=True)
        assert bucket1 is not bucket2


class TestRateLimiterIntegration:
    """Integration tests for rate limiter with mock API"""

    @pytest.mark.asyncio
    async def test_concurrent_10_tasks_completion_time(self):
        """Test that 10 concurrent tasks complete with correct timing"""
        # Create bucket: capacity 3, fill rate 3/s
        bucket = AsyncTokenBucket(capacity=3, fill_rate=3.0, initial_tokens=3)
        task_times = []
        start = time.monotonic()

        async def mock_api_call(task_id: int):
            """Mock API call that respects token bucket"""
            await bucket.consume()
            task_start = time.monotonic()
            await asyncio.sleep(0.01)  # Simulate API call
            task_times.append(time.monotonic() - task_start)
            return f"task_{task_id}_done"

        # Launch 10 concurrent tasks
        tasks = [mock_api_call(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        elapsed = time.monotonic() - start

        # Verify all tasks completed
        assert len(results) == 10
        assert all("task_" in r for r in results)

        # Verify timing is consistent with rate limiting
        # With capacity 3 and rate 3/s, first 3 are immediate,
        # then each subsequent task waits ~0.333s
        # For 10 tasks: 3 immediate + 7 * 0.333 = ~2.33s minimum
        assert elapsed >= 2.0

    @pytest.mark.asyncio
    async def test_jitter_produces_varying_delays(self):
        """Test that jitter delay produces varying intervals between requests"""
        intervals = []
        last_time = None

        @jitter_delay(jitter_min=0.02, jitter_max=0.05)
        async def mock_call():
            nonlocal last_time
            current = time.monotonic()
            if last_time is not None:
                intervals.append(current - last_time)
            last_time = current
            return "done"

        # Make 10 calls and measure intervals
        for _ in range(10):
            await mock_call()

        # Should have 9 intervals (between 10 calls)
        assert len(intervals) == 9

        # All intervals should be in jitter range (with some tolerance)
        assert all(0.015 < i < 0.06 for i in intervals)

        # Intervals should vary (not all the same)
        unique_intervals = set(round(i, 4) for i in intervals)
        assert len(unique_intervals) > 3  # At least some variation


class TestRateLimiterEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_zero_capacity_bucket(self):
        """Test bucket with zero capacity"""
        bucket = AsyncTokenBucket(capacity=0, fill_rate=1.0, initial_tokens=0)
        # Should wait indefinitely or return immediately
        start = time.monotonic()
        result = await bucket.consume(1, blocking=False)
        elapsed = time.monotonic() - start
        assert result is False
        assert elapsed < 0.1  # Should be non-blocking

    @pytest.mark.asyncio
    async def test_consume_exactly_capacity(self):
        """Test consuming exactly the bucket capacity"""
        bucket = AsyncTokenBucket(capacity=5, fill_rate=10.0, initial_tokens=5)
        result = await bucket.consume(5)
        assert result is True
        tokens = await bucket.get_available_tokens()
        assert 0 <= tokens < 0.001  # Should be essentially 0

    @pytest.mark.asyncio
    async def test_multiple_consume_calls(self):
        """Test multiple sequential consume calls"""
        bucket = AsyncTokenBucket(capacity=5, fill_rate=2.0, initial_tokens=5)

        await bucket.consume(2)
        tokens = await bucket.get_available_tokens()
        assert 2.99 < tokens < 3.01  # Allow small floating point variance

        await bucket.consume(1)
        tokens = await bucket.get_available_tokens()
        assert 1.99 < tokens < 2.01

        await bucket.consume(2)
        tokens = await bucket.get_available_tokens()
        assert 0 <= tokens < 0.001
