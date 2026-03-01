"""Unit tests for the anomaly detection engine."""

import pytest
import math
from datetime import datetime, timedelta

from src.analytics.anomalies import (
    AnomalyDetector,
    AnomalyResult,
    AnomalyType,
    Location,
)


class TestLocation:
    """Tests for Location dataclass."""
    
    def test_valid_location(self):
        """Test creating a valid location."""
        loc = Location(latitude=40.7128, longitude=-74.0060, country="US", city="New York")
        
        assert loc.latitude == 40.7128
        assert loc.longitude == -74.0060
        assert loc.country == "US"
        assert loc.city == "New York"
    
    def test_location_boundary_values(self):
        """Test location with boundary coordinate values."""
        # Valid boundaries
        Location(latitude=90, longitude=180)
        Location(latitude=-90, longitude=-180)
        Location(latitude=0, longitude=0)
    
    def test_invalid_latitude(self):
        """Test that invalid latitude raises error."""
        with pytest.raises(ValueError, match="Invalid latitude"):
            Location(latitude=91, longitude=0)
        
        with pytest.raises(ValueError, match="Invalid latitude"):
            Location(latitude=-91, longitude=0)
    
    def test_invalid_longitude(self):
        """Test that invalid longitude raises error."""
        with pytest.raises(ValueError, match="Invalid longitude"):
            Location(latitude=0, longitude=181)
        
        with pytest.raises(ValueError, match="Invalid longitude"):
            Location(latitude=0, longitude=-181)


class TestHaversineDistance:
    """Tests for haversine distance calculation."""
    
    @pytest.fixture
    def detector(self):
        """Create an AnomalyDetector instance."""
        return AnomalyDetector()
    
    def test_distance_same_point(self, detector):
        """Test distance between identical points is zero."""
        loc = Location(latitude=40.7128, longitude=-74.0060)
        distance = detector.haversine_distance(loc, loc)
        
        assert distance == 0.0
    
    def test_distance_nyc_to_london(self, detector):
        """Test distance from NYC to London (approximately 5570 km)."""
        nyc = Location(latitude=40.7128, longitude=-74.0060)
        london = Location(latitude=51.5074, longitude=-0.1278)
        
        distance = detector.haversine_distance(nyc, london)
        
        # Should be approximately 5570 km
        assert 5500 < distance < 5600
    
    def test_distance_nyc_to_la(self, detector):
        """Test distance from NYC to LA (approximately 3940 km)."""
        nyc = Location(latitude=40.7128, longitude=-74.0060)
        la = Location(latitude=34.0522, longitude=-118.2437)
        
        distance = detector.haversine_distance(nyc, la)
        
        # Should be approximately 3940 km
        assert 3900 < distance < 4000
    
    def test_distance_equator_poles(self, detector):
        """Test distance from equator to pole."""
        equator = Location(latitude=0, longitude=0)
        north_pole = Location(latitude=90, longitude=0)
        
        distance = detector.haversine_distance(equator, north_pole)
        
        # Should be approximately 10007 km (quarter circumference)
        assert 10000 < distance < 10010
    
    def test_symmetry(self, detector):
        """Test that distance is symmetric."""
        loc1 = Location(latitude=40.7128, longitude=-74.0060)
        loc2 = Location(latitude=51.5074, longitude=-0.1278)
        
        dist1 = detector.haversine_distance(loc1, loc2)
        dist2 = detector.haversine_distance(loc2, loc1)
        
        assert dist1 == dist2


class TestImpossibleTravelDetection:
    """Tests for impossible travel detection."""
    
    @pytest.fixture
    def detector(self):
        """Create an AnomalyDetector with default speed."""
        return AnomalyDetector(travel_speed_kmh=900)
    
    def test_possible_travel_nyc_to_boston(self, detector):
        """Test NYC to Boston in 3 hours (should be possible)."""
        nyc = Location(latitude=40.7128, longitude=-74.0060)
        boston = Location(latitude=42.3601, longitude=-71.0589)
        
        prev_time = datetime(2024, 1, 1, 12, 0, 0)
        curr_time = datetime(2024, 1, 1, 15, 0, 0)  # 3 hours later
        
        result = detector.detect_impossible_travel(
            prev_location=nyc,
            prev_time=prev_time,
            curr_location=boston,
            curr_time=curr_time,
            prev_country="US",
            curr_country="US"
        )
        
        assert result.type == AnomalyType.IMPOSSIBLE_TRAVEL
        assert result.detected is False
        assert result.risk_score == 0
    
    def test_impossible_travel_nyc_to_tokyo(self, detector):
        """Test NYC to Tokyo in 1 hour (should be impossible)."""
        nyc = Location(latitude=40.7128, longitude=-74.0060, country="US", city="New York")
        tokyo = Location(latitude=35.6762, longitude=139.6503, country="JP", city="Tokyo")
        
        prev_time = datetime(2024, 1, 1, 12, 0, 0)
        curr_time = datetime(2024, 1, 1, 13, 0, 0)  # 1 hour later
        
        result = detector.detect_impossible_travel(
            prev_location=nyc,
            prev_time=prev_time,
            curr_location=tokyo,
            curr_time=curr_time,
            prev_country="US",
            curr_country="JP"
        )
        
        assert result.type == AnomalyType.IMPOSSIBLE_TRAVEL
        assert result.detected is True
        assert result.risk_score > 90  # Very high risk
        assert "New York" in result.message or "Tokyo" in result.message or "US" in result.message
    
    def test_impossible_travel_same_country(self, detector):
        """Test impossible travel within same country."""
        la = Location(latitude=34.0522, longitude=-118.2437)
        nyc = Location(latitude=40.7128, longitude=-74.0060)
        
        prev_time = datetime(2024, 1, 1, 12, 0, 0)
        curr_time = datetime(2024, 1, 1, 13, 0, 0)  # 1 hour later
        
        result = detector.detect_impossible_travel(
            prev_location=la,
            prev_time=prev_time,
            curr_location=nyc,
            curr_time=curr_time,
            prev_country="US",
            curr_country="US"
        )
        
        assert result.detected is True
        # LA to NYC is ~3940 km, needs ~4.4 hours at 900 km/h
        assert result.risk_score > 70
    
    def test_time_too_small_to_evaluate(self, detector):
        """Test that very small time differences are skipped."""
        loc1 = Location(latitude=40.7128, longitude=-74.0060)
        loc2 = Location(latitude=42.3601, longitude=-71.0589)
        
        prev_time = datetime(2024, 1, 1, 12, 0, 0)
        curr_time = datetime(2024, 1, 1, 12, 3, 0)  # 3 minutes later
        
        result = detector.detect_impossible_travel(
            prev_location=loc1,
            prev_time=prev_time,
            curr_location=loc2,
            curr_time=curr_time
        )
        
        assert result.detected is False
        assert result.risk_score == 0
        assert "too small" in result.message
    
    def test_exact_minimum_travel_time(self, detector):
        """Test borderline case where time equals minimum."""
        # Two points ~900 km apart (1 hour at 900 km/h)
        loc1 = Location(latitude=0, longitude=0)
        # Approx 900 km north
        loc2 = Location(latitude=8.1, longitude=0)
        
        prev_time = datetime(2024, 1, 1, 12, 0, 0)
        curr_time = datetime(2024, 1, 1, 13, 0, 0)  # 1 hour later
        
        result = detector.detect_impossible_travel(
            prev_location=loc1,
            prev_time=prev_time,
            curr_location=loc2,
            curr_time=curr_time
        )
        
        # Should be possible (just barely)
        assert result.detected is False or result.risk_score < 10


class TestRiskScoreCalculation:
    """Tests for risk score calculation."""
    
    @pytest.fixture
    def detector(self):
        """Create an AnomalyDetector with default speed."""
        return AnomalyDetector(travel_speed_kmh=900)
    
    def test_risk_score_zero_when_time_sufficient(self, detector):
        """Test risk score is zero when time is sufficient."""
        score = detector.calculate_risk_score(
            actual_time_min=120,  # 2 hours
            min_travel_time_min=60  # 1 hour needed
        )
        
        assert score == 0
    
    def test_risk_score_maximum_when_no_time(self, detector):
        """Test risk score is 100 when no time elapsed."""
        score = detector.calculate_risk_score(
            actual_time_min=0,
            min_travel_time_min=60
        )
        
        assert score == 100
    
    def test_risk_score_half_when_half_time(self, detector):
        """Test risk score when actual time is half of minimum."""
        score = detector.calculate_risk_score(
            actual_time_min=30,
            min_travel_time_min=60
        )
        
        assert score == 50
    
    def test_risk_score_capped_at_100(self, detector):
        """Test risk score doesn't exceed 100."""
        score = detector.calculate_risk_score(
            actual_time_min=-10,  # Negative time (shouldn't happen but test anyway)
            min_travel_time_min=60
        )
        
        assert score == 100


class TestNewCountryDetection:
    """Tests for new country detection."""
    
    @pytest.fixture
    def detector(self):
        """Create an AnomalyDetector."""
        return AnomalyDetector()
    
    def test_new_country_first_login(self, detector):
        """Test first login to a country (empty known list)."""
        result = detector.detect_new_country("US", [])
        
        assert result.type == AnomalyType.NEW_COUNTRY
        assert result.detected is True
        assert result.risk_score == 30  # Lower risk for first login
        assert "US" in result.message
    
    def test_new_country_additional(self, detector):
        """Test login from new country when user has history."""
        result = detector.detect_new_country("JP", ["US", "CA"])
        
        assert result.detected is True
        assert result.risk_score == 50  # Moderate risk
        assert "JP" in result.message
        assert "US" in result.message
        assert "CA" in result.message
    
    def test_known_country(self, detector):
        """Test login from known country."""
        result = detector.detect_new_country("US", ["US", "CA"])
        
        assert result.detected is False
        assert result.risk_score == 0
    
    def test_case_insensitive_country_code(self, detector):
        """Test that country codes are case-insensitive."""
        result = detector.detect_new_country("us", ["US"])
        
        assert result.detected is False
    
    def test_second_country_detection(self, detector):
        """Test that second country has different risk score."""
        result = detector.detect_new_country("CA", ["US"])
        
        assert result.detected is True
        assert result.risk_score == 60  # Higher risk for second country


class TestNewIPDetection:
    """Tests for new IP detection."""
    
    @pytest.fixture
    def detector(self):
        """Create an AnomalyDetector."""
        return AnomalyDetector()
    
    def test_new_ip_first_login(self, detector):
        """Test first login from any IP."""
        result = detector.detect_new_ip("192.168.1.1", [])
        
        assert result.type == AnomalyType.NEW_IP
        assert result.detected is True
        assert result.risk_score == 10
    
    def test_new_ip_additional(self, detector):
        """Test new IP when user has IP history."""
        result = detector.detect_new_ip("10.0.0.1", ["192.168.1.1"])
        
        assert result.detected is True
        assert result.risk_score == 25
    
    def test_known_ip(self, detector):
        """Test login from known IP."""
        result = detector.detect_new_ip("192.168.1.1", ["192.168.1.1", "10.0.0.1"])
        
        assert result.detected is False
        assert result.risk_score == 0


class TestFailedLoginDetection:
    """Tests for failed login detection."""
    
    @pytest.fixture
    def detector(self):
        """Create an AnomalyDetector."""
        return AnomalyDetector()
    
    def test_successful_login(self, detector):
        """Test successful login has no anomaly."""
        result = detector.detect_failed_login(is_success=True)
        
        assert result.type == AnomalyType.FAILED_LOGIN
        assert result.detected is False
        assert result.risk_score == 0
    
    def test_single_failure(self, detector):
        """Test single failed login."""
        result = detector.detect_failed_login(
            is_success=False,
            failure_reason="Invalid password"
        )
        
        assert result.detected is True
        assert result.risk_score == 20
        assert "Invalid password" in result.message
    
    def test_multiple_failures_threshold(self, detector):
        """Test multiple failures at threshold."""
        result = detector.detect_failed_login(
            is_success=False,
            failure_reason="Invalid password",
            recent_failures=3
        )
        
        assert result.type == AnomalyType.MULTIPLE_FAILURES
        assert result.detected is True
        assert result.risk_score == 50
    
    def test_many_failures(self, detector):
        """Test many failures."""
        result = detector.detect_failed_login(
            is_success=False,
            failure_reason="Account locked",
            recent_failures=5
        )
        
        assert result.type == AnomalyType.MULTIPLE_FAILURES
        assert result.risk_score == 80
        assert "5" in result.message


class TestAnalyzeLogin:
    """Tests for comprehensive login analysis."""
    
    @pytest.fixture
    def detector(self):
        """Create an AnomalyDetector."""
        return AnomalyDetector()
    
    def test_analyze_successful_login_no_anomalies(self, detector):
        """Test analysis of normal successful login."""
        current_login = {
            "user_email": "user@example.com",
            "ip_address": "192.168.1.1",
            "country_code": "US",
            "city": "New York",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "login_time": datetime(2024, 1, 1, 12, 0, 0),
            "is_success": True
        }
        
        user_history = {
            "known_countries": ["US"],
            "known_ips": ["192.168.1.1"],
            "failed_attempts_24h": 0
        }
        
        results = detector.analyze_login(current_login, user_history=user_history)
        
        # Should have results but no detected anomalies
        detected = [r for r in results if r.detected]
        assert len(detected) == 0
    
    def test_analyze_failed_login(self, detector):
        """Test analysis of failed login."""
        current_login = {
            "user_email": "user@example.com",
            "ip_address": "192.168.1.1",
            "login_time": datetime(2024, 1, 1, 12, 0, 0),
            "is_success": False,
            "failure_reason": "Invalid credentials"
        }
        
        results = detector.analyze_login(current_login)
        
        # Should detect failed login
        failed_results = [r for r in results if r.type in (AnomalyType.FAILED_LOGIN, AnomalyType.MULTIPLE_FAILURES)]
        assert len(failed_results) > 0
        assert any(r.detected for r in failed_results)
    
    def test_analyze_new_country(self, detector):
        """Test detection of new country."""
        current_login = {
            "user_email": "user@example.com",
            "ip_address": "1.1.1.1",
            "country_code": "JP",
            "city": "Tokyo",
            "latitude": 35.6762,
            "longitude": 139.6503,
            "login_time": datetime(2024, 1, 1, 12, 0, 0),
            "is_success": True
        }
        
        user_history = {
            "known_countries": ["US"],
            "known_ips": ["192.168.1.1"],
            "failed_attempts_24h": 0
        }
        
        results = detector.analyze_login(current_login, user_history=user_history)
        
        # Should detect new country
        country_results = [r for r in results if r.type == AnomalyType.NEW_COUNTRY]
        assert len(country_results) > 0
        assert country_results[0].detected is True
    
    def test_analyze_impossible_travel(self, detector):
        """Test detection of impossible travel."""
        current_login = {
            "user_email": "user@example.com",
            "ip_address": "1.1.1.1",
            "country_code": "JP",
            "city": "Tokyo",
            "latitude": 35.6762,
            "longitude": 139.6503,
            "login_time": datetime(2024, 1, 1, 13, 0, 0),  # 1 hour later
            "is_success": True
        }
        
        previous_login = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "country_code": "US",
            "city": "New York",
            "login_time": datetime(2024, 1, 1, 12, 0, 0)
        }
        
        results = detector.analyze_login(current_login, previous_login=previous_login)
        
        # Should detect impossible travel
        travel_results = [r for r in results if r.type == AnomalyType.IMPOSSIBLE_TRAVEL]
        assert len(travel_results) > 0
        assert travel_results[0].detected is True
        assert travel_results[0].risk_score > 90


class TestAnomalyDetectorConfiguration:
    """Tests for detector configuration."""
    
    def test_default_speed(self):
        """Test default travel speed."""
        detector = AnomalyDetector()
        assert detector.travel_speed_kmh == 900
    
    def test_custom_speed(self):
        """Test custom travel speed."""
        detector = AnomalyDetector(travel_speed_kmh=800)
        assert detector.travel_speed_kmh == 800
    
    def test_custom_speed_affects_calculation(self):
        """Test that custom speed affects travel time calculation."""
        fast_detector = AnomalyDetector(travel_speed_kmh=1000)
        slow_detector = AnomalyDetector(travel_speed_kmh=500)
        
        # Same distance, different speeds
        distance = 1000  # km
        
        fast_time = fast_detector.calculate_min_travel_time(distance)
        slow_time = slow_detector.calculate_min_travel_time(distance)
        
        assert fast_time < slow_time
        assert fast_time == 60  # 1000 km / 1000 km/h = 1 hour = 60 minutes
        assert slow_time == 120  # 1000 km / 500 km/h = 2 hours = 120 minutes
