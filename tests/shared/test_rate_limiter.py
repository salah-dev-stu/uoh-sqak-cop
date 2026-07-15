"""Token-bucket rate limiter (NFR-4). Config-driven, injectable clock."""

from __future__ import annotations

from cipherchase.shared.rate_limiter import RateLimiter, TokenBucket


def test_bucket_allows_up_to_capacity_then_refuses() -> None:
    clock = [0.0]
    bucket = TokenBucket(capacity=2, refill_per_minute=60, now=lambda: clock[0])
    assert bucket.allow()
    assert bucket.allow()
    assert not bucket.allow()  # empty, no time passed


def test_bucket_refills_over_time() -> None:
    clock = [0.0]
    bucket = TokenBucket(capacity=1, refill_per_minute=60, now=lambda: clock[0])  # 1 token/sec
    assert bucket.allow()
    assert not bucket.allow()
    clock[0] = 1.0
    assert bucket.allow()


def test_rate_limiter_is_per_service() -> None:
    clock = [0.0]
    limits = {
        "gmail": {"capacity": 1, "requests_per_minute": 60},
        "mcp": {"capacity": 5, "requests_per_minute": 120},
    }
    limiter = RateLimiter(limits, now=lambda: clock[0])
    assert limiter.allow("gmail")
    assert not limiter.allow("gmail")
    assert limiter.allow("mcp")  # separate bucket unaffected
