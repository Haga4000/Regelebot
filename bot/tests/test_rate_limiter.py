import time
from unittest.mock import patch

from core.rate_limiter import RateLimiter


def test_under_limit():
    rl = RateLimiter()
    for _ in range(10):
        assert rl.is_allowed("group1") is True


def test_over_limit():
    rl = RateLimiter()
    for _ in range(10):
        rl.is_allowed("group1")
    assert rl.is_allowed("group1") is False


def test_independent_keys():
    rl = RateLimiter()
    for _ in range(10):
        rl.is_allowed("group1")
    assert rl.is_allowed("group1") is False
    assert rl.is_allowed("group2") is True


def test_window_expiry():
    rl = RateLimiter()
    base = time.monotonic()

    with patch("core.rate_limiter.time") as mock_time:
        mock_time.monotonic.return_value = base
        for _ in range(10):
            rl.is_allowed("group1")
        assert rl.is_allowed("group1") is False

        # Advance past the 60s window
        mock_time.monotonic.return_value = base + 61
        assert rl.is_allowed("group1") is True


def test_reset():
    rl = RateLimiter()
    for _ in range(10):
        rl.is_allowed("group1")
    assert rl.is_allowed("group1") is False
    rl.reset()
    assert rl.is_allowed("group1") is True
