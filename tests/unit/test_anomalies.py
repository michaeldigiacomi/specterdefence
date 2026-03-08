import pytest
from datetime import datetime, timezone, timedelta
from src.analytics.anomalies import AnomalyDetector, Location, AnomalyType


def test_impossible_travel():
    detector = AnomalyDetector()
    
    # New York
    loc1 = Location(latitude=40.7128, longitude=-74.0060, city="New York", country="US")
    time1 = datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
    
    # London
    loc2 = Location(latitude=51.5074, longitude=-0.1278, city="London", country="GB")
    # Only 30 minutes later - impossible! (NY to London is ~5500km, takes ~7 hours)
    time2 = time1 + timedelta(minutes=30)
    
    result = detector.detect_impossible_travel(
        prev_location=loc1,
        prev_time=time1,
        curr_location=loc2,
        curr_time=time2,
        prev_country="US",
        curr_country="GB"
    )
    
    assert result.detected is True
    assert result.type == AnomalyType.IMPOSSIBLE_TRAVEL
    assert result.risk_score > 80  # Should be very high risk
    assert "Impossible travel detected" in result.message


def test_possible_travel():
    detector = AnomalyDetector()
    
    # New York
    loc1 = Location(latitude=40.7128, longitude=-74.0060, city="New York", country="US")
    time1 = datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
    
    # London
    loc2 = Location(latitude=51.5074, longitude=-0.1278, city="London", country="GB")
    # 10 hours later - totally possible
    time2 = time1 + timedelta(hours=10)
    
    result = detector.detect_impossible_travel(
        prev_location=loc1,
        prev_time=time1,
        curr_location=loc2,
        curr_time=time2,
        prev_country="US",
        curr_country="GB"
    )
    
    assert result.detected is False
    assert result.risk_score == 0
    assert "Travel possible" in result.message


def test_new_country():
    detector = AnomalyDetector()
    
    known = ["US", "CA"]
    
    # Known country
    result1 = detector.detect_new_country("US", known)
    assert result1.detected is False
    assert result1.risk_score == 0
    
    # New country
    result2 = detector.detect_new_country("GB", known)
    assert result2.detected is True
    assert result2.type == AnomalyType.NEW_COUNTRY
    assert result2.risk_score > 0
