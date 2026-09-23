"""
User Risk Scoring for SpecterDefence UEBA system.

This module handles the calculation and management of risk scores for users
based on behavioral analytics.
"""

import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class UserRiskScorer:
    """User risk scoring system based on multiple behavioral factors."""

    def __init__(self, decay_factor: float = 0.95, max_age_hours: int = 24):
        """
        Initialize the user risk scorer.
        
        Args:
            decay_factor: Factor by which to decay old scores (0.0-1.0)
            max_age_hours: Maximum age of data before scoring is discarded
        """
        self.decay_factor = decay_factor
        self.max_age_hours = max_age_hours
        self.user_scores: Dict[str, List[Tuple[datetime, float]]] = {}
        self.current_scores: Dict[str, float] = {}
        
    def calculate_risk_score(self, 
                           user_id: str,
                           anomaly_score: float,
                           activity_metrics: Dict[str, Any],
                           time_window_hours: int = 1) -> float:
        """
        Calculate a comprehensive risk score for a user.
        
        Args:
            user_id: The user identifier
            anomaly_score: Raw anomaly detection score from UEBA model
            activity_metrics: Dictionary of activity metrics (login times, locations, etc.)
            time_window_hours: Time window for score calculation
            
        Returns:
            Composite risk score (0.0-1.0)
        """
        # Base anomaly-based score
        base_score = min(1.0, max(0.0, anomaly_score))
        
        # Get behavior-based factors
        behavior_score = self._calculate_behavior_score(activity_metrics)
        
        # Weighted combination of scores
        final_score = 0.7 * base_score + 0.3 * behavior_score
        
        # Update the score with decay
        self._update_user_score(user_id, final_score, datetime.now())
        
        return float(final_score)
        
    def _calculate_behavior_score(self, activity_metrics: Dict[str, Any]) -> float:
        """
        Calculate behavior-based component of risk score.
        
        Args:
            activity_metrics: Dictionary of user activity metrics
            
        Returns:
            Behavior score (0.0-1.0)
        """
        score = 0.0
        factors_count = 0
        
        # Login time irregularity
        if 'login_times' in activity_metrics:
            irregularity = self._calculate_time_irregularity(activity_metrics['login_times'])
            score += irregularity * 0.3
            factors_count += 0.3
            
        # Geographic anomalies (impossible travel)
        if 'locations' in activity_metrics:
            geo_anomaly = self._calculate_geo_anomaly(activity_metrics['locations'])
            score += geo_anomaly * 0.4
            factors_count += 0.4
            
        # Authentication patterns
        if 'failed_logins' in activity_metrics:
            failed_login_score = min(1.0, activity_metrics['failed_logins'] / 10.0)
            score += failed_login_score * 0.3
            factors_count += 0.3
            
        # Normalize by number of factors considered
        if factors_count > 0:
            return score / factors_count
        else:
            return 0.0
            
    def _calculate_time_irregularity(self, login_times: List[datetime]) -> float:
        """
        Calculate time irregularity score based on login times.
        
        Args:
            login_times: List of login datetime objects
            
        Returns:
            Irregularity score (0.0-1.0)
        """
        if len(login_times) < 2:
            return 0.0
            
        # Calculate time differences between logins
        time_differences = []
        for i in range(1, len(login_times)):
            diff = abs((login_times[i] - login_times[i-1]).total_seconds())
            time_differences.append(diff)
            
        if not time_differences:
            return 0.0
            
        # Calculate variance in login times
        avg_time_diff = np.mean(time_differences)
        std_time_diff = np.std(time_differences)
        
        # High variance indicates irregular activity
        if avg_time_diff > 0:
            irregularity = min(1.0, std_time_diff / avg_time_diff)  
            return irregularity
        else:
            return 0.0
            
    def _calculate_geo_anomaly(self, locations: List[Tuple[float, float]]) -> float:
        """
        Calculate geographic anomaly score based on location changes.
        
        Args:
            locations: List of (latitude, longitude) tuples
            
        Returns:
            Geo anomaly score (0.0-1.0)
        """
        if len(locations) < 2:
            return 0.0
            
        # Calculate distances between consecutive locations
        import haversine
        distances = []
        for i in range(1, len(locations)):
            try:
                dist = haversine.distance(locations[i-1], locations[i]).kilometers
                distances.append(dist)
            except Exception:
                continue
                
        if not distances:
            return 0.0
            
        # Calculate mean + standard deviation of distances
        avg_dist = np.mean(distances)
        std_dist = np.std(distances)
        
        # High standard deviation indicates irregular travel patterns
        if avg_dist > 0:
            anomaly_score = min(1.0, std_dist / avg_dist)
            return anomaly_score
        else:
            return 0.0
            
    def _update_user_score(self, user_id: str, score: float, timestamp: datetime) -> None:
        """
        Update user score with decay.
        
        Args:
            user_id: The user identifier
            score: New score value
            timestamp: When the score was calculated
        """
        if user_id not in self.user_scores:
            self.user_scores[user_id] = []
            
        # Add new score
        self.user_scores[user_id].append((timestamp, score))
        
        # Remove old scores that exceed max age
        cutoff_time = timestamp - timedelta(hours=self.max_age_hours)
        self.user_scores[user_id] = [
            (t, s) for t, s in self.user_scores[user_id] 
            if t > cutoff_time
        ]
        
        # Apply decay to all scores and calculate final score
        current_time = datetime.now()
        weighted_sum = 0.0
        weight_sum = 0.0
        
        for t, s in reversed(self.user_scores[user_id]):
            age_hours = (current_time - t).total_seconds() / 3600
            weight = self.decay_factor ** age_hours
            weighted_sum += s * weight
            weight_sum += weight
            
        if weight_sum > 0:
            self.current_scores[user_id] = weighted_sum / weight_sum
        else:
            self.current_scores[user_id] = score
            
    def get_user_score(self, user_id: str) -> float:
        """
        Get the current risk score for a user.
        
        Args:
            user_id: The user identifier
            
        Returns:
            Current risk score (0.0-1.0)
        """
        return self.current_scores.get(user_id, 0.0)
        
    def get_all_scores(self) -> Dict[str, float]:
        """
        Get all current user scores.
        
        Returns:
            Dictionary of user_id -> risk_score
        """
        return self.current_scores.copy()
        
    def reset_user_scores(self) -> None:
        """Reset all user scores."""
        self.user_scores.clear()
        self.current_scores.clear()