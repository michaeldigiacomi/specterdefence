"""Anomaly detection engine for login analytics."""

import logging
import math
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class AnomalyType(StrEnum):
    """Types of login anomalies."""
    IMPOSSIBLE_TRAVEL = "impossible_travel"
    NEW_COUNTRY = "new_country"
    NEW_IP = "new_ip"
    FAILED_LOGIN = "failed_login"
    MULTIPLE_FAILURES = "multiple_failures"
    SUSPICIOUS_LOCATION = "suspicious_location"


@dataclass
class AnomalyResult:
    """Result of anomaly detection."""

    type: AnomalyType
    detected: bool
    risk_score: int  # 0-100
    details: dict[str, Any]
    message: str


@dataclass
class Location:
    """Geographic location with coordinates."""

    latitude: float
    longitude: float
    country: str | None = None
    city: str | None = None

    def __post_init__(self):
        """Validate coordinates."""
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"Invalid longitude: {self.longitude}")


class AnomalyDetector:
    """Detects anomalies in login patterns."""

    # Earth's radius in kilometers
    EARTH_RADIUS_KM = 6371.0

    # Default travel speed assumption (km/h) - commercial flight average
    DEFAULT_TRAVEL_SPEED_KMH = 900

    # Minimum time between logins to consider (in minutes) for impossible travel
    MIN_TIME_DIFFERENCE_MINUTES = 5

    def __init__(self, travel_speed_kmh: float = DEFAULT_TRAVEL_SPEED_KMH):
        """
        Initialize the anomaly detector.

        Args:
            travel_speed_kmh: Assumed travel speed in km/h for impossible travel detection
        """
        self.travel_speed_kmh = travel_speed_kmh

    @staticmethod
    def haversine_distance(loc1: Location, loc2: Location) -> float:
        """
        Calculate the great circle distance between two points on Earth.

        Uses the Haversine formula for accuracy.

        Args:
            loc1: First location
            loc2: Second location

        Returns:
            Distance in kilometers
        """
        # Convert to radians
        lat1_rad = math.radians(loc1.latitude)
        lat2_rad = math.radians(loc2.latitude)
        delta_lat = math.radians(loc2.latitude - loc1.latitude)
        delta_lon = math.radians(loc2.longitude - loc1.longitude)

        # Haversine formula
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return AnomalyDetector.EARTH_RADIUS_KM * c

    def calculate_min_travel_time(self, distance_km: float) -> float:
        """
        Calculate minimum travel time between two points.

        Args:
            distance_km: Distance in kilometers

        Returns:
            Minimum travel time in minutes
        """
        if self.travel_speed_kmh <= 0:
            return float('inf')

        # time = distance / speed, convert hours to minutes
        return (distance_km / self.travel_speed_kmh) * 60

    def calculate_risk_score(self, actual_time_min: float, min_travel_time_min: float) -> int:
        """
        Calculate risk score for impossible travel.

        Risk score is inversely proportional to how much time
        the user would need to make the trip.

        Args:
            actual_time_min: Actual time between logins in minutes
            min_travel_time_min: Minimum travel time needed in minutes

        Returns:
            Risk score from 0-100
        """
        if min_travel_time_min <= 0:
            return 0

        if actual_time_min >= min_travel_time_min:
            return 0

        # Calculate ratio: how much shorter was the actual time?
        ratio = actual_time_min / min_travel_time_min

        # Risk score: 100 - (ratio * 100), but cap at 100
        risk_score = int(100 - (ratio * 100))
        return min(100, max(0, risk_score))

    def detect_impossible_travel(
        self,
        prev_location: Location,
        prev_time: datetime,
        curr_location: Location,
        curr_time: datetime,
        prev_country: str | None = None,
        curr_country: str | None = None
    ) -> AnomalyResult:
        """
        Detect if travel between two login locations is physically impossible.

        Args:
            prev_location: Previous login location
            prev_time: Previous login timestamp
            curr_location: Current login location
            curr_time: Current login timestamp
            prev_country: Previous country code (optional)
            curr_country: Current country code (optional)

        Returns:
            AnomalyResult with detection status and details
        """
        # Calculate time difference
        time_diff = curr_time - prev_time
        time_diff_minutes = abs(time_diff.total_seconds() / 60)

        # Skip if time difference is too small (same session, etc.)
        if time_diff_minutes < self.MIN_TIME_DIFFERENCE_MINUTES:
            return AnomalyResult(
                type=AnomalyType.IMPOSSIBLE_TRAVEL,
                detected=False,
                risk_score=0,
                details={
                    "time_diff_minutes": time_diff_minutes,
                    "reason": "Time difference too small to evaluate"
                },
                message="Time difference too small for travel analysis"
            )

        # Calculate distance
        distance_km = self.haversine_distance(prev_location, curr_location)

        # Calculate minimum travel time
        min_travel_time = self.calculate_min_travel_time(distance_km)

        # Check if travel is impossible
        is_impossible = time_diff_minutes < min_travel_time

        # Calculate risk score
        risk_score = self.calculate_risk_score(time_diff_minutes, min_travel_time)

        # Build location strings
        prev_location_str = f"{prev_location.city}, {prev_country or 'Unknown'}" if prev_location.city else f"{prev_country or 'Unknown'}"
        curr_location_str = f"{curr_location.city}, {curr_country or 'Unknown'}" if curr_location.city else f"{curr_country or 'Unknown'}"

        details = {
            "distance_km": round(distance_km, 2),
            "time_diff_minutes": round(time_diff_minutes, 2),
            "min_travel_time_minutes": round(min_travel_time, 2),
            "travel_speed_assumed_kmh": self.travel_speed_kmh,
            "previous_location": {
                "latitude": prev_location.latitude,
                "longitude": prev_location.longitude,
                "city": prev_location.city,
                "country": prev_country
            },
            "current_location": {
                "latitude": curr_location.latitude,
                "longitude": curr_location.longitude,
                "city": curr_location.city,
                "country": curr_country
            },
            "location_strings": [prev_location_str, curr_location_str]
        }

        if is_impossible:
            message = (
                f"Impossible travel detected: {prev_location_str} to {curr_location_str} "
                f"in {time_diff_minutes:.0f} minutes (minimum required: {min_travel_time:.0f} minutes, "
                f"distance: {distance_km:.0f} km)"
            )
        else:
            message = (
                f"Travel possible: {prev_location_str} to {curr_location_str} "
                f"in {time_diff_minutes:.0f} minutes (minimum required: {min_travel_time:.0f} minutes)"
            )

        return AnomalyResult(
            type=AnomalyType.IMPOSSIBLE_TRAVEL,
            detected=is_impossible,
            risk_score=risk_score,
            details=details,
            message=message
        )

    def detect_new_country(
        self,
        country_code: str,
        known_countries: list[str]
    ) -> AnomalyResult:
        """
        Detect if login is from a new country for the user.

        Args:
            country_code: Current country code (ISO 2-letter)
            known_countries: List of previously seen country codes

        Returns:
            AnomalyResult with detection status
        """
        country_code = country_code.upper()
        known_countries_upper = [c.upper() for c in known_countries]

        is_new = country_code not in known_countries_upper

        # Risk score: higher for first login, lower if user has traveled before
        if is_new:
            if len(known_countries) == 0:
                risk_score = 30  # First login, low risk
            elif len(known_countries) == 1:
                risk_score = 60  # Second country
            else:
                risk_score = 50  # Experienced traveler
        else:
            risk_score = 0

        details = {
            "country_code": country_code,
            "known_countries": known_countries,
            "is_first_login": len(known_countries) == 0
        }

        if is_new:
            message = f"New country detected: {country_code}. Previously seen: {', '.join(known_countries) or 'None'}"
        else:
            message = f"Known country: {country_code}"

        return AnomalyResult(
            type=AnomalyType.NEW_COUNTRY,
            detected=is_new,
            risk_score=risk_score,
            details=details,
            message=message
        )

    def detect_new_ip(
        self,
        ip_address: str,
        known_ips: list[str]
    ) -> AnomalyResult:
        """
        Detect if login is from a new IP address for the user.

        Args:
            ip_address: Current IP address
            known_ips: List of previously seen IP addresses

        Returns:
            AnomalyResult with detection status
        """
        is_new = ip_address not in known_ips

        # Risk score based on user's IP history
        risk_score = (10 if len(known_ips) == 0 else 25) if is_new else 0

        details = {
            "ip_address": ip_address,
            "known_ips_count": len(known_ips),
            "is_new": is_new
        }

        message = f"New IP address detected: {ip_address}" if is_new else f"Known IP address: {ip_address}"

        return AnomalyResult(
            type=AnomalyType.NEW_IP,
            detected=is_new,
            risk_score=risk_score,
            details=details,
            message=message
        )

    def detect_failed_login(
        self,
        is_success: bool,
        failure_reason: str | None = None,
        recent_failures: int = 0
    ) -> AnomalyResult:
        """
        Detect failed login attempts and multiple failures.

        Args:
            is_success: Whether login was successful
            failure_reason: Reason for failure if applicable
            recent_failures: Number of recent failed attempts

        Returns:
            AnomalyResult with detection status
        """
        if is_success:
            return AnomalyResult(
                type=AnomalyType.FAILED_LOGIN,
                detected=False,
                risk_score=0,
                details={"recent_failures": recent_failures},
                message="Login successful"
            )

        # Base risk score for failed login
        risk_score = 20

        # Increase risk for multiple failures
        if recent_failures >= 5:
            risk_score = 80
            detected_type = AnomalyType.MULTIPLE_FAILURES
        elif recent_failures >= 3:
            risk_score = 50
            detected_type = AnomalyType.MULTIPLE_FAILURES
        else:
            risk_score = 20
            detected_type = AnomalyType.FAILED_LOGIN

        details = {
            "failure_reason": failure_reason,
            "recent_failures": recent_failures,
            "is_multiple": recent_failures >= 3
        }

        if recent_failures >= 3:
            message = f"Multiple failed login attempts ({recent_failures} in 24h). Last reason: {failure_reason or 'Unknown'}"
        else:
            message = f"Failed login: {failure_reason or 'Unknown reason'}"

        return AnomalyResult(
            type=detected_type,
            detected=True,
            risk_score=risk_score,
            details=details,
            message=message
        )

    def analyze_login(
        self,
        current_login: dict[str, Any],
        previous_login: dict[str, Any] | None = None,
        user_history: dict[str, Any] | None = None
    ) -> list[AnomalyResult]:
        """
        Perform complete anomaly analysis on a login attempt.

        Args:
            current_login: Current login data
            previous_login: Previous login data (for travel analysis)
            user_history: User's login history

        Returns:
            List of anomaly detection results
        """
        results = []

        # Detect failed login
        is_success = current_login.get("is_success", True)
        failure_reason = current_login.get("failure_reason")
        recent_failures = user_history.get("failed_attempts_24h", 0) if user_history else 0

        failure_result = self.detect_failed_login(is_success, failure_reason, recent_failures)
        results.append(failure_result)

        # Skip location-based analysis for failed logins
        if not is_success:
            return results

        # Get current location
        curr_lat = current_login.get("latitude")
        curr_lon = current_login.get("longitude")
        curr_country = current_login.get("country_code")
        curr_ip = current_login.get("ip_address")

        if curr_lat is None or curr_lon is None:
            logger.warning("Cannot perform location analysis without coordinates")
            return results

        try:
            curr_location = Location(
                latitude=curr_lat,
                longitude=curr_lon,
                country=curr_country,
                city=current_login.get("city")
            )
        except ValueError as e:
            logger.error(f"Invalid current location: {e}")
            return results

        # Detect new country
        if user_history and curr_country:
            known_countries = user_history.get("known_countries", [])
            country_result = self.detect_new_country(curr_country, known_countries)
            results.append(country_result)

        # Detect new IP
        if user_history and curr_ip:
            known_ips = user_history.get("known_ips", [])
            ip_result = self.detect_new_ip(curr_ip, known_ips)
            results.append(ip_result)

        # Detect impossible travel
        if previous_login:
            prev_lat = previous_login.get("latitude")
            prev_lon = previous_login.get("longitude")
            prev_time = previous_login.get("login_time")
            prev_country = previous_login.get("country_code")
            curr_time = current_login.get("login_time")

            if (prev_lat is not None and prev_lon is not None and
                prev_time is not None and curr_time is not None):
                try:
                    prev_location = Location(
                        latitude=prev_lat,
                        longitude=prev_lon,
                        country=prev_country,
                        city=previous_login.get("city")
                    )

                    travel_result = self.detect_impossible_travel(
                        prev_location=prev_location,
                        prev_time=prev_time,
                        curr_location=curr_location,
                        curr_time=curr_time,
                        prev_country=prev_country,
                        curr_country=curr_country
                    )
                    results.append(travel_result)

                except ValueError as e:
                    logger.error(f"Invalid previous location: {e}")

        return results
