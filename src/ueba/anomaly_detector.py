"""
Anomaly Detector for SpecterDefence UEBA system.

This module handles real-time anomaly detection using machine learning models.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
import logging
from datetime import datetime, timedelta

from .behavior_model import BehaviorModel

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Main anomaly detection class for UEBA system."""

    def __init__(self):
        """Initialize the anomaly detector."""
        self.behavior_models: Dict[str, BehaviorModel] = {}
        self.risk_scores: Dict[str, float] = {}
        self.last_analysis_time: Dict[str, datetime] = {}
        
    def add_user_model(self, user_id: str, window_size: int = 30) -> None:
        """
        Add a behavior model for a specific user.
        
        Args:
            user_id: The user identifier
            window_size: Number of historical data points to consider
        """
        if user_id not in self.behavior_models:
            self.behavior_models[user_id] = BehaviorModel(window_size)
            logger.info("Created behavior model for user %s", user_id)
            
    def train_user_model(self, user_id: str, features: np.ndarray) -> None:
        """
        Train the behavior model for a specific user.
        
        Args:
            user_id: The user identifier
            features: Array of feature vectors for training
        """
        if user_id not in self.behavior_models:
            raise ValueError(f"No behavior model found for user {user_id}")
            
        self.behavior_models[user_id].fit(features)
        logger.info("Trained behavior model for user %s", user_id)
        
    def detect_anomalies(self, user_id: str, features: np.ndarray) -> Dict[str, Any]:
        """
        Detect anomalies for a specific user based on provided features.
        
        Args:
            user_id: The user identifier
            features: Array of feature vectors to analyze
            
        Returns:
            Dictionary containing anomaly detection results
        """
        if user_id not in self.behavior_models:
            raise ValueError(f"No behavior model found for user {user_id}")
            
        # Get anomaly scores and labels
        scores, labels = self.behavior_models[user_id].predict_anomaly(features)
        
        # Calculate risk score (mean of negative anomaly scores)
        risk_score = float(np.mean(-scores))
        
        # Update risk score
        self.risk_scores[user_id] = risk_score
        
        # Store analysis time
        self.last_analysis_time[user_id] = datetime.now()
        
        return {
            "user_id": user_id,
            "anomaly_scores": scores.tolist(),
            "anomaly_labels": labels.tolist(),
            "risk_score": risk_score,
            "timestamp": datetime.now().isoformat(),
            "anomalies_detected": int(np.sum(labels == -1))
        }
        
    def get_user_risk_score(self, user_id: str) -> float:
        """
        Get the current risk score for a user.
        
        Args:
            user_id: The user identifier
            
        Returns:
            Risk score (higher = more risky)
        """
        return self.risk_scores.get(user_id, 0.0)
        
    def get_all_risk_scores(self) -> Dict[str, float]:
        """
        Get risk scores for all users.
        
        Returns:
            Dictionary of user_id -> risk_score
        """
        return self.risk_scores.copy()
        
    def update_model_with_new_data(self, user_id: str, new_features: np.ndarray) -> None:
        """
        Update behavior model with new data (for continuous learning).
        
        Args:
            user_id: The user identifier
            new_features: New feature vectors to incorporate
        """
        if user_id in self.behavior_models and self.behavior_models[user_id].is_trained:
            logger.info("Updating model for user %s with new data", user_id)
            # In a production system, this would involve incremental learning or retraining
            # For now, we note that the data is available but don't actually update
            pass