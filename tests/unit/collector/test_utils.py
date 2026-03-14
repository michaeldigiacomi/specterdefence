"""Unit tests for collector utility functions."""

from datetime import datetime, timezone, timedelta
import pytest
from src.collector.main import ensure_timezone_aware

def test_ensure_timezone_aware_naive():
    """Test that a naive datetime is correctly assigned the UTC timezone."""
    dt = datetime(2023, 1, 1, 12, 0, 0)
    result = ensure_timezone_aware(dt)
    assert result.tzinfo == timezone.utc
    assert result.year == 2023
    assert result.month == 1
    assert result.day == 1
    assert result.hour == 12

def test_ensure_timezone_aware_utc():
    """Test that a UTC-aware datetime remains unchanged."""
    dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    result = ensure_timezone_aware(dt)
    assert result.tzinfo == timezone.utc
    assert result == dt

def test_ensure_timezone_aware_other_tz():
    """Test that a datetime in another timezone is correctly converted to UTC."""
    # Create a timezone that is UTC-5 (EST)
    est = timezone(timedelta(hours=-5))
    dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=est)

    result = ensure_timezone_aware(dt)

    assert result.tzinfo == timezone.utc
    # 12:00 EST should be 17:00 UTC
    assert result.hour == 17
    assert result.year == 2023
    assert result.month == 1
    assert result.day == 1
