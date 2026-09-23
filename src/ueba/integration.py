"""
UEBA Integration Module for SpecterDefence.

This module provides integration points between the UEBA system and existing 
monitoring components in the platform.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import numpy as np
import logging

from .anomaly_detector import AnomalyDetector
from .user_risk_scoring import UserRiskScorer

logger = logging.getLogger(__name__)


class UEBAIntegration:
    """
    Integration class for connecting UEBA system with existing monitoring components.
    
    This class provides methods to integrate ML-based anomaly detection with 
    existing security monitoring infrastructure.
    """

    def __init__(self):
        """Initialize the UEBA integration."""
        self.anomaly_detector = AnomalyDetector()
        self.risk_scorer = UserRiskScorer()
        self.is_initialized = False
        
    def initialize(self) -> None:
        """Initialize the UEBA system."""
        logger.info("Initializing UEBA system")
        # In a real implementation, this might load pre-trained models
        self.is_initialized = True
        logger.info("UEBA system initialized successfully")
        
    def process_user_behavior_data(self, user_id: str, 
                                  behavior_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user behavior data and generate anomaly detection results.
        
        Args:
            user_id: User identifier
            behavior_data: Dictionary containing behavioral metrics
            
        Returns:
            Detection results including risk scores and anomaly information
        """
        if not self.is_initialized:
            raise RuntimeError("UEBA system not initialized")
            
        # Create feature vector from behavior data
        features = self._create_feature_vector(behavior_data)
        
        # Ensure user model exists
        if user_id not in self.anomaly_detector.behavior_models:
            self.anomaly_detector.add_user_model(user_id)
            
        try:
            # Detect anomalies
            detection_results = self.anomaly_detector.detect_anomalies(user_id, features)
            
            # Calculate composite risk score
            risk_score = self.risk_scorer.calculate_risk_score(
                user_id=user_id,
                anomaly_score=detection_results['risk_score'],
                activity_metrics=behavior_data
            )
            
            # Update detection results with risk score
            detection_results['composite_risk_score'] = risk_score
            
            return detection_results
            
        except Exception as e:
            logger.error("Error processing behavior data for user %s: %s", user_id, str(e))
            raise
            
    def _create_feature_vector(self, behavior_data: Dict[str, Any]) -> np.ndarray:
        """
        Convert behavior data into a feature vector suitable for ML models.
        
        Args:
            behavior_data: Dictionary containing behavioral metrics
            
        Returns:
            Feature vector as numpy array
        """
        # Extract numeric features for ML model input
        features = []
        
        # Login time features
        if 'login_times' in behavior_data and behavior_data['login_times']:
            login_hours = [t.hour for t in behavior_data['login_times']]
            features.extend([
                np.mean(login_hours),
                np.std(login_hours),
                len(login_hours)
            ])
            
        # Location features (if provided)
        if 'locations' in behavior_data and behavior_data['locations']:
            latitudes = [loc[0] for loc in behavior_data['locations'] if loc]
            longitudes = [loc[1] for loc in behavior_data['locations'] if loc]
            
            if latitudes and longitudes:
                features.extend([
                    np.mean(latitudes),
                    np.std(latitudes),
                    np.mean(longitudes),
                    np.std(longitudes)
                ])
                
        # Authentication features
        if 'failed_logins' in behavior_data:
            features.append(behavior_data['failed_logins'])
            
        # Email activity features
        if 'email_count' in behavior_data:
            features.append(behavior_data['email_count'])
            
        # Default to zero vector if no features available
        if not features:
            features = [0.0] * 10  # 10 default features
            
        return np.array(features).reshape(1, -1)
        
    def get_user_risk_score(self, user_id: str) -> float:
        """
        Get current risk score for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Risk score (0.0-1.0)
        """
        return self.risk_scorer.get_user_score(user_id)
        
    def get_all_risk_scores(self) -> Dict[str, float]:
        """
        Get risk scores for all users.
        
        Returns:
            Dictionary of user_id -> risk_score
        """
        return self.risk_scorer.get_all_scores()
        
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get current status of the UEBA system.
        
        Returns:
            Status information including model training status and user counts
        """
        return {
            "initialized": self.is_initialized,
            "active_users": len(self.anomaly_detector.behavior_models),
            "timestamp": datetime.now().isoformat(),
        }