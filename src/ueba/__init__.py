"""
UEBA (User and Entity Behavior Analytics) module for SpecterDefence.

This module implements machine learning-based anomaly detection for users
and entities within Microsoft 365 environments.
"""

from .anomaly_detector import AnomalyDetector
from .user_risk_scoring import UserRiskScorer
from .behavior_model import BehaviorModel

__all__ = ["AnomalyDetector", "UserRiskScorer", "BehaviorModel"]